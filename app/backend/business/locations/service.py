from backend.data.models import Location, RouteRecord, now
from fastapi import HTTPException


def update(db, user, data):
    if data.route_id:
        route = db.get(RouteRecord, str(data.route_id))
        if not route or route.user_id != user.id:
            raise HTTPException(404, 'Ruta no encontrada.')
    location = db.get(Location, user.id) or Location(user_id=user.id)
    location.longitude = data.longitude
    location.latitude = data.latitude
    location.accuracy = data.accuracy
    location.route_id = str(data.route_id) if data.route_id else None
    location.updated_at = now()
    db.add(location)
    db.commit()
    return location
