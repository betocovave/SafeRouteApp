from datetime import timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import select
from backend.data.models import Alert, Category, Delivery, Incident, Location, Report, RouteRecord, User, now, utc
from backend.external_services.geolocation.service import distance
from backend.intelligence.risk_algorithm.engine import RULES, line_distance_m


def quiet(preferences):
    start, end = preferences.get('quiet_start'), preferences.get('quiet_end')
    hour = now().astimezone(ZoneInfo('America/Mexico_City')).hour
    return start is not None and end is not None and (start <= hour < end if start < end else hour >= start or hour < end)


def generate(db, incident):
    category = db.get(Category, incident.category_id)
    if incident.status not in ('pending', 'confirmed') or utc(incident.expires_at) <= now():
        return []
    notifications = []
    locations = db.scalars(select(Location).where(Location.updated_at >= now()-timedelta(seconds=RULES['location_max_age_s'])))
    for location in locations:
        user = db.get(User, location.user_id)
        if not user.active or not user.preferences.get('alerts', True) or location.accuracy > RULES['location_max_accuracy_m']:
            continue
        own = db.scalar(select(Report.id).where(Report.user_id == user.id, Report.incident_id == incident.id))
        if own:
            continue
        point = [incident.longitude, incident.latitude]
        near = distance([location.longitude, location.latitude], point) <= RULES['corroboration_radius_m']
        route = db.get(RouteRecord, location.route_id) if location.route_id else None
        on_route = route and line_distance_m(route.geometry['coordinates'], point) <= RULES['influence_radius_m']
        if not near and not on_route:
            continue
        kind = 'risk' if category.critical or on_route else 'corroboration'
        message = ('Riesgo crítico: evita continuar hacia la zona afectada.' if category.critical else 'Nuevo incidente en tu recorrido.' if on_route else 'Incidente cercano: corrobora solo si puedes hacerlo con seguridad.')
        if db.scalar(select(Alert.id).where(Alert.user_id == user.id, Alert.incident_id == incident.id, Alert.version == incident.version, Alert.kind == kind)):
            continue
        alert = Alert(user_id=user.id, incident_id=incident.id, version=incident.version, kind=kind, message=message, priority='critical' if category.critical else 'normal')
        db.add(alert)
        db.flush()
        if not quiet(user.preferences) or category.critical:
            db.add(Delivery(alert_id=alert.id))
        notifications.append((user.id, alert.id))
    db.commit()
    return notifications
