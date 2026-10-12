from datetime import timedelta
from sqlalchemy import select
from fastapi import HTTPException
from backend.data.models import Incident, Report, Category, Corroboration, Location, Audit, now, utc
from backend.intelligence.risk_algorithm.engine import RULES
from backend.external_services.geolocation.service import distance


def expire(db):
    changed = []
    for item in db.scalars(select(Incident).where(Incident.status.in_(['pending', 'confirmed']), Incident.expires_at <= now()).with_for_update()):
        item.status = 'expired'
        item.version += 1
        item.updated_at = now()
        db.add(Audit(action='incident.expired', target=item.id))
        changed.append(item.id)
    db.commit()
    return changed


def corroborate(db, user, incident_id, answer, version):
    incident = db.scalar(select(Incident).where(Incident.id == incident_id).with_for_update())
    if not incident or incident.status not in ('pending', 'confirmed') or utc(incident.expires_at) <= now():
        raise HTTPException(409, 'El incidente ya no está vigente.')
    if version != incident.version:
        raise HTTPException(409, 'El incidente cambió. Actualiza antes de corroborar.')
    original = db.scalar(select(Report).where(Report.incident_id == incident_id, Report.user_id == user.id))
    if original:
        raise HTTPException(403, 'No puedes corroborar tu propio reporte.')
    category = db.get(Category, incident.category_id)
    if category.critical:
        raise HTTPException(403, 'No se solicita corroboración de incidentes críticos.')
    location = db.get(Location, user.id)
    if not location or (now()-utc(location.updated_at)).total_seconds() > RULES['location_max_age_s'] or location.accuracy > RULES['location_max_accuracy_m'] or distance([location.longitude, location.latitude], [incident.longitude, incident.latitude]) > RULES['corroboration_radius_m']:
        raise HTTPException(403, 'Se requiere ubicación reciente y cercana para corroborar.')
    existing = db.scalar(select(Corroboration).where(Corroboration.user_id == user.id, Corroboration.incident_id == incident.id, Corroboration.version == version))
    if existing:
        raise HTTPException(409, 'Ya corroboraste esta actualización.')
    db.add(Corroboration(user_id=user.id, incident_id=incident.id, version=version, answer=answer))
    db.flush()
    responses = list(db.scalars(select(Corroboration.answer).where(Corroboration.incident_id == incident.id, Corroboration.version == version)))
    if responses.count(answer) >= RULES['corroborations_required'] and answer != 'unknown':
        incident.status = 'confirmed' if answer == 'present' else 'resolved'
        incident.confidence = RULES['confirmed_confidence']
        incident.updated_at = now()
        if answer == 'present':
            incident.expires_at = now() + timedelta(hours=category.ttl_hours)
        incident.version += 1
    db.add(Audit(actor_id=user.id, action='incident.corroborated', target=incident.id, details={'answer': answer}))
    db.commit()
    return incident
