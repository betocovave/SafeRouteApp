import asyncio
import hashlib
import json
import secrets
from collections import defaultdict, deque
from datetime import timedelta
from uuid import UUID
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile, WebSocket, WebSocketDisconnect
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from geoalchemy2.elements import WKTElement
from backend.api import schemas as S
from backend.api.realtime import hub
from backend.authentication.security import current_user, admin_user, authenticate, digest, hasher, issue, revoke_all, verify
from backend.business.administration.service import audit
from backend.business.alerts.service import generate
from backend.business.incidents.service import corroborate
from backend.business.locations.service import update as update_location
from backend.business.preferences.service import save as save_preferences
from backend.business.routes.service import calculate, output
from backend.business.users.service import profile
from backend.config import settings
from backend.data.database import get_db, SessionLocal
from backend.data.models import Alert, Category, Device, Evaluation, Incident, Location, Photo, Report, RouteRecord, Session, User, now, utc
from backend.external_services.azure_maps.client import search
from backend.external_services.geolocation.service import require_city, distance
from backend.intelligence.processing.heatmap import heatmap
from backend.intelligence.risk_algorithm.engine import evaluate
from backend.media import photos

router = APIRouter(prefix='/api/v1')
auth_attempts = defaultdict(deque)
ws_tickets = {}


def limit(request, bucket, max_count=12):
    key = (request.client.host if request.client else 'unknown', bucket)
    queue = auth_attempts[key]
    cutoff = now()-timedelta(minutes=5)
    while queue and queue[0] < cutoff:
        queue.popleft()
    if len(queue) >= max_count:
        raise HTTPException(429, 'Demasiados intentos. Espera unos minutos.')
    queue.append(now())


def incident_output(db, incident):
    category = db.get(Category, incident.category_id)
    photo = db.scalar(select(Photo).join(Report, Photo.report_id == Report.id).where(Report.incident_id == incident.id))
    return {'id': incident.id, 'category_id': category.id, 'category': category.name, 'description': incident.description, 'longitude': incident.longitude, 'latitude': incident.latitude, 'status': 'expired' if incident.status in ('pending', 'confirmed') and utc(incident.expires_at) <= now() else incident.status, 'confidence': incident.confidence, 'critical': category.critical, 'occurred_at': utc(incident.occurred_at).isoformat(), 'expires_at': utc(incident.expires_at).isoformat(), 'updated_at': utc(incident.updated_at).isoformat(), 'version': incident.version, 'photo_id': photo.id if photo else None}


@router.post('/auth/register', response_model=S.Tokens, status_code=201)
def register(data: S.Registration, request: Request, db=Depends(get_db)):
    limit(request, 'register')
    if db.scalar(select(User.id).where(User.email == data.email)):
        raise HTTPException(409, 'Este correo ya está registrado.')
    recovery = secrets.token_urlsafe(32)
    user = User(name=data.name, email=data.email, password_hash=hasher.hash(data.password), recovery_hash=hasher.hash(recovery))
    db.add(user)
    try:
        db.flush()
        return issue(db, user, recovery_code=recovery)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Este correo ya está registrado.')


@router.post('/auth/login', response_model=S.Tokens)
def login(data: S.Login, request: Request, db=Depends(get_db)):
    limit(request, 'login')
    user = db.scalar(select(User).where(User.email == data.email))
    if not user or not user.active or not verify(user.password_hash, data.password):
        raise HTTPException(401, 'Credenciales inválidas.')
    return issue(db, user)


@router.post('/auth/recover', response_model=S.Tokens)
def recover(data: S.Recovery, request: Request, db=Depends(get_db)):
    limit(request, 'recover', 5)
    user = db.scalar(select(User).where(User.email == data.email).with_for_update())
    if not user or not user.active or not verify(user.recovery_hash, data.recovery_code):
        raise HTTPException(401, 'Correo o código de recuperación inválidos.')
    recovery = secrets.token_urlsafe(32)
    user.password_hash = hasher.hash(data.password)
    user.recovery_hash = hasher.hash(recovery)
    revoke_all(db, user.id)
    audit(db, user, 'account.recovered', user.id)
    return issue(db, user, recovery_code=recovery)


@router.post('/auth/refresh', response_model=S.Tokens)
def refresh(data: S.Refresh, request: Request, db=Depends(get_db)):
    limit(request, 'refresh', 100)
    session = db.scalar(select(Session).where(Session.refresh_hash == digest(data.refresh_token)).with_for_update())
    if not session or session.revoked or utc(session.expires_at) <= now():
        raise HTTPException(401, 'Sesión expirada.')
    user = db.get(User, session.user_id)
    if not user.active:
        raise HTTPException(401, 'Cuenta suspendida.')
    return issue(db, user, existing=session)


@router.post('/auth/logout', status_code=204)
def logout(request: Request, user=Depends(current_user), db=Depends(get_db)):
    _, session = authenticate(db, request.headers['authorization'].split(' ', 1)[1])
    session.revoked = True
    db.execute(delete(Device).where(Device.user_id == user.id))
    db.execute(delete(Location).where(Location.user_id == user.id))
    db.commit()


@router.get('/users/me', response_model=S.UserOutput)
def me(user=Depends(current_user)):
    return profile(user)


@router.patch('/users/me', response_model=S.UserOutput)
def edit_profile(data: S.Profile, user=Depends(current_user), db=Depends(get_db)):
    user.name = data.name
    db.commit()
    return profile(user)


@router.put('/preferences', response_model=S.Preferences)
def preferences(data: S.Preferences, user=Depends(current_user), db=Depends(get_db)):
    return save_preferences(db, user, data)


@router.post('/locations')
async def location(data: S.LocationInput, user=Depends(current_user), db=Depends(get_db)):
    require_city(data.longitude, data.latitude)
    update_location(db, user, data)
    for incident in db.scalars(select(Incident).where(Incident.status.in_(['pending', 'confirmed']), Incident.expires_at > now())):
        for user_id, alert_id in generate(db, incident):
            await hub.send(user_id, {'type': 'alert', 'id': alert_id})
    return {'updated': True}


@router.delete('/locations', status_code=204)
def clear_location(user=Depends(current_user), db=Depends(get_db)):
    db.execute(delete(Location).where(Location.user_id == user.id))
    db.commit()


@router.get('/search')
async def destination_search(q: str = Query(min_length=2, max_length=160), user=Depends(current_user)):
    return await search(q)


@router.post('/routes', response_model=S.RouteResults)
async def routes(data: S.RouteInput, request: Request, user=Depends(current_user), db=Depends(get_db)):
    limit(request, 'routes', 60)
    require_city(data.origin.longitude, data.origin.latitude)
    require_city(data.destination.longitude, data.destination.latitude)
    return await calculate(db, user, data)


@router.post('/routes/{route_id}/evaluate', response_model=S.RiskEvaluation)
def reevaluate(route_id: UUID, user=Depends(current_user), db=Depends(get_db)):
    record = db.get(RouteRecord, str(route_id))
    if not record or record.user_id != user.id:
        raise HTTPException(404, 'Ruta no encontrada.')
    record.evaluation = evaluate(db, record.geometry)
    db.add(Evaluation(route_id=record.id, result=record.evaluation))
    db.commit()
    return record.evaluation


@router.get('/categories', response_model=list[S.CategoryOutput])
def categories(user=Depends(current_user), db=Depends(get_db)):
    return [{'id': c.id, 'name': c.name, 'group': c.group, 'severity': c.severity, 'ttl_hours': c.ttl_hours, 'critical': c.critical, 'active': c.active} for c in db.scalars(select(Category).where(Category.active.is_(True)).order_by(Category.name))]


@router.get('/incidents/heatmap')
def historical_heatmap(user=Depends(current_user), db=Depends(get_db)):
    return heatmap(db)


@router.get('/incidents', response_model=list[S.IncidentOutput])
def incidents(longitude: float = Query(ge=-180, le=180), latitude: float = Query(ge=-90, le=90), radius_m: int = Query(default=2000, ge=100, le=5000), offset: int = Query(default=0, ge=0), user=Depends(current_user), db=Depends(get_db)):
    require_city(longitude, latitude)
    point = [longitude, latitude]
    candidates = db.scalars(select(Incident).where(Incident.status.in_(['pending', 'confirmed']), Incident.expires_at > now()).order_by(Incident.updated_at.desc()))
    selected = [i for i in candidates if distance(point, [i.longitude, i.latitude]) <= radius_m]
    return [incident_output(db, i) for i in selected[offset:offset+100]]


@router.get('/incidents/{incident_id}', response_model=S.IncidentOutput)
def incident_detail(incident_id: UUID, user=Depends(current_user), db=Depends(get_db)):
    incident = db.get(Incident, str(incident_id))
    if not incident or incident.status == 'hidden':
        raise HTTPException(404, 'Incidente no encontrado.')
    return incident_output(db, incident)


@router.post('/incidents', status_code=201, response_model=S.ReportOutput)
async def report(data: S.IncidentInput, request: Request, user=Depends(current_user), db=Depends(get_db)):
    require_city(data.longitude, data.latitude)
    payload_hash = digest(json.dumps(data.model_dump(mode='json'), sort_keys=True))
    existing = db.scalar(select(Report).where(Report.user_id == user.id, Report.client_id == str(data.client_id)))
    if existing:
        if existing.payload_hash != payload_hash:
            raise HTTPException(409, 'El identificador ya pertenece a otro reporte.')
        return {'report_id': existing.id, 'incident': incident_output(db, db.get(Incident, existing.incident_id))}
    limit(request, 'report', 20)
    if utc(data.occurred_at) > now()+timedelta(minutes=2) or utc(data.occurred_at) < now()-timedelta(days=30):
        raise HTTPException(422, 'La fecha del incidente está fuera del intervalo permitido.')
    category = db.get(Category, data.category_id)
    if not category or not category.active:
        raise HTTPException(422, 'Categoría inválida.')
    incident = Incident(category_id=category.id, description=data.description, longitude=data.longitude, latitude=data.latitude, occurred_at=utc(data.occurred_at), updated_at=utc(data.occurred_at), expires_at=utc(data.occurred_at)+timedelta(hours=category.ttl_hours))
    if incident.expires_at <= now():
        incident.status = 'expired'
    if db.bind.dialect.name == 'postgresql':
        incident.position = WKTElement(f'POINT({data.longitude} {data.latitude})', srid=4326)
    db.add(incident)
    db.flush()
    item = Report(user_id=user.id, incident_id=incident.id, client_id=str(data.client_id), payload_hash=payload_hash)
    db.add(item)
    audit(db, user, 'incident.reported', incident.id)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Reporte concurrente. Reintenta con el mismo identificador.')
    await hub.broadcast({'type': 'incidents_changed'})
    for user_id, alert_id in generate(db, incident):
        await hub.send(user_id, {'type': 'alert', 'id': alert_id})
    return {'report_id': item.id, 'incident': incident_output(db, incident)}


@router.post('/incidents/{incident_id}/corroborations', response_model=S.IncidentOutput)
async def confirmation(incident_id: UUID, data: S.CorroborationInput, user=Depends(current_user), db=Depends(get_db)):
    item = corroborate(db, user, str(incident_id), data.answer, data.version)
    await hub.broadcast({'type': 'incidents_changed'})
    return incident_output(db, item)


@router.post('/reports/{report_id}/photo')
async def attach_photo(report_id: UUID, file: UploadFile = File(), user=Depends(current_user), db=Depends(get_db)):
    item = db.get(Report, str(report_id))
    if not item or item.user_id != user.id:
        raise HTTPException(404, 'Reporte no encontrado.')
    existing = db.scalar(select(Photo).where(Photo.report_id == item.id))
    if existing:
        return {'photo_id': existing.id}
    data = await file.read(settings().max_photo_bytes+1)
    clean = await asyncio.to_thread(photos.sanitize, data)
    blob = await asyncio.to_thread(photos.upload, clean)
    photo = Photo(report_id=item.id, blob_name=blob)
    db.add(photo)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Un intento simultaneo no puede sustituir la evidencia ya registrada.
        existing = db.scalar(select(Photo).where(Photo.report_id == item.id))
        return {'photo_id': existing.id}
    await hub.broadcast({'type': 'incidents_changed'})
    return {'photo_id': photo.id}


@router.get('/photos/{photo_id}')
async def photo(photo_id: UUID, user=Depends(current_user), db=Depends(get_db)):
    item = db.get(Photo, str(photo_id))
    if not item:
        raise HTTPException(404, 'Foto no encontrada.')
    report_item = db.get(Report, item.report_id)
    incident = db.get(Incident, report_item.incident_id)
    if incident.status == 'hidden' and user.role != 'admin' and report_item.user_id != user.id:
        raise HTTPException(404, 'Foto no encontrada.')
    return Response(await asyncio.to_thread(photos.download, item.blob_name), media_type='image/jpeg', headers={'Cache-Control': 'private, no-store'})


@router.get('/alerts', response_model=list[S.AlertOutput])
def alerts(offset: int = Query(default=0, ge=0), user=Depends(current_user), db=Depends(get_db)):
    return [{'id': a.id, 'incident_id': a.incident_id, 'kind': a.kind, 'message': a.message, 'priority': a.priority, 'read': a.read, 'created_at': utc(a.created_at).isoformat()} for a in db.scalars(select(Alert).where(Alert.user_id == user.id).order_by(Alert.created_at.desc()).offset(offset).limit(50))]


@router.patch('/alerts/{alert_id}/read', status_code=204)
def read_alert(alert_id: UUID, user=Depends(current_user), db=Depends(get_db)):
    item = db.get(Alert, str(alert_id))
    if not item or item.user_id != user.id:
        raise HTTPException(404, 'Alerta no encontrada.')
    item.read = True
    db.commit()


@router.post('/devices', status_code=204)
def device(data: S.DeviceInput, user=Depends(current_user), db=Depends(get_db)):
    item = db.get(Device, data.token) or Device(token=data.token, user_id=user.id)
    item.user_id = user.id
    db.add(item)
    db.commit()


@router.get('/history', response_model=S.HistoryOutput)
def history(offset: int = Query(default=0, ge=0), user=Depends(current_user), db=Depends(get_db)):
    return {'routes': [output(r) for r in db.scalars(select(RouteRecord).where(RouteRecord.user_id == user.id).order_by(RouteRecord.created_at.desc()).offset(offset).limit(20))], 'reports': [{'report_id': r.id, 'incident': incident_output(db, db.get(Incident, r.incident_id))} for r in db.scalars(select(Report).where(Report.user_id == user.id).order_by(Report.received_at.desc()).offset(offset).limit(20))]}


@router.post('/realtime/ticket')
def ticket(request: Request, user=Depends(current_user), db=Depends(get_db)):
    limit(request, 'ticket', 100)
    _, session = authenticate(db, request.headers['authorization'].split(' ', 1)[1])
    token = secrets.token_urlsafe(32)
    for key in list(ws_tickets):
        if ws_tickets[key][1] < now():
            del ws_tickets[key]
    ws_tickets[token] = (user.id, now()+timedelta(seconds=30), session.id)
    return {'ticket': token}


@router.websocket('/realtime')
async def realtime(socket: WebSocket):
    await socket.accept()
    try:
        message = await asyncio.wait_for(socket.receive_json(), timeout=5)
        credential = ws_tickets.pop(message.get('ticket', ''), None)
        if not credential or credential[1] <= now():
            await socket.close(code=4401)
            return
        user_id = credential[0]
        hub.clients.setdefault(user_id, set()).add(socket)
        while True:
            # Autorizar periodicamente; una cuenta suspendida pierde el canal.
            with SessionLocal() as db:
                user = db.get(User, user_id)
                session = db.get(Session, credential[2])
                if not user or not user.active or not session or session.revoked or utc(session.expires_at) <= now():
                    await socket.close(code=4401)
                    return
            try:
                await asyncio.wait_for(socket.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                await socket.send_json({'type': 'heartbeat'})
    except (WebSocketDisconnect, asyncio.TimeoutError, ValueError):
        pass
    finally:
        if 'user_id' in locals():
            hub.clients.get(user_id, set()).discard(socket)


@router.get('/admin/users')
def admin_users(offset: int = Query(default=0, ge=0), admin=Depends(admin_user), db=Depends(get_db)):
    return [{**profile(u), 'active': u.active} for u in db.scalars(select(User).order_by(User.created_at.desc()).offset(offset).limit(50))]


@router.patch('/admin/users/{user_id}', status_code=204)
def suspend(user_id: UUID, data: S.AdminUser, admin=Depends(admin_user), db=Depends(get_db)):
    item = db.get(User, str(user_id))
    if not item:
        raise HTTPException(404, 'Usuario no encontrado.')
    if item.role == 'admin':
        raise HTTPException(409, 'No se permite suspender administradores desde la app.')
    item.active = data.active
    if not data.active:
        revoke_all(db, item.id)
        db.execute(delete(Device).where(Device.user_id == item.id))
        db.execute(delete(Location).where(Location.user_id == item.id))
    audit(db, admin, 'user.active_changed', item.id, {'active': data.active})
    db.commit()


@router.get('/admin/incidents')
def admin_incidents(offset: int = Query(default=0, ge=0), admin=Depends(admin_user), db=Depends(get_db)):
    return [incident_output(db, i) for i in db.scalars(select(Incident).order_by(Incident.updated_at.desc()).offset(offset).limit(50))]


@router.patch('/admin/incidents/{incident_id}')
async def moderate(incident_id: UUID, data: S.AdminIncident, admin=Depends(admin_user), db=Depends(get_db)):
    item = db.get(Incident, str(incident_id))
    if not item:
        raise HTTPException(404, 'Incidente no encontrado.')
    item.status = data.status
    item.updated_at = now()
    item.version += 1
    if data.status == 'confirmed':
        item.confidence = 1
        item.expires_at = now()+timedelta(hours=db.get(Category, item.category_id).ttl_hours)
    audit(db, admin, 'incident.moderated', item.id, data.model_dump())
    db.commit()
    await hub.broadcast({'type': 'incidents_changed'})
    return incident_output(db, item)


@router.get('/admin/categories')
def admin_categories(admin=Depends(admin_user), db=Depends(get_db)):
    return [{'id': c.id, 'name': c.name, 'group': c.group, 'severity': c.severity, 'ttl_hours': c.ttl_hours, 'critical': c.critical, 'active': c.active} for c in db.scalars(select(Category).order_by(Category.name))]


@router.put('/admin/categories/{category_id}')
def edit_category(category_id: str, data: S.CategoryInput, admin=Depends(admin_user), db=Depends(get_db)):
    item = db.get(Category, category_id)
    if not item:
        raise HTTPException(404, 'Categoría no encontrada.')
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    audit(db, admin, 'category.edited', item.id, data.model_dump())
    db.commit()
    return {'id': item.id, **data.model_dump()}
