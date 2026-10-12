import asyncio
import json
from fastapi import HTTPException
from sqlalchemy import select
from geoalchemy2.elements import WKTElement
from backend.data.models import Incident, Category, RouteRecord, Evaluation, now
from backend.external_services.azure_maps import client
from backend.business.routes.corridors import safe_corridor
from backend.business.recommendations.service import recommendation
from backend.intelligence.risk_algorithm.engine import evaluate


def output(record):
    return {k: getattr(record, k) for k in ['id', 'transport', 'geometry', 'distance_m', 'duration_s', 'instructions', 'evaluation']}


async def calculate(db, user, data):
    origin = [data.origin.longitude, data.origin.latitude]
    destination = [data.destination.longitude, data.destination.latitude]
    if origin == destination:
        raise HTTPException(422, 'Elige un destino distinto al origen.')
    hazards = list(db.execute(select(Incident, Category).join(Category, Category.id == Incident.category_id).where(Incident.status.in_(['pending', 'confirmed']), Incident.expires_at > now(), Category.severity > 0)))

    async def corridor_routes():
        via = await asyncio.to_thread(safe_corridor, origin, destination, data.transport, hazards)
        return await client.directions(origin, destination, data.transport, via) if via else []

    base, extra = await asyncio.gather(client.directions(origin, destination, data.transport), corridor_routes(), return_exceptions=True)
    if isinstance(base, Exception):
        raise base
    if isinstance(extra, Exception):
        # Se exige una red instalada; no prometer evitacion sin el motor de corredores.
        raise extra
    records = []
    signatures = set()
    for route in [*base, *extra]:
        signature = json.dumps([[round(x, 5), round(y, 5)] for x, y in route['geometry']['coordinates']])
        if signature in signatures:
            continue
        signatures.add(signature)
        result = evaluate(db, route['geometry'])
        record = RouteRecord(user_id=user.id, transport=data.transport, **route, evaluation=result)
        if db.bind.dialect.name == 'postgresql':
            coordinates = ','.join(f'{x} {y}' for x, y in route['geometry']['coordinates'])
            record.path = WKTElement(f'LINESTRING({coordinates})', srid=4326)
        db.add(record)
        db.flush()
        db.add(Evaluation(route_id=record.id, result=result))
        records.append(output(record))
    selected, warning = recommendation(records, user.preferences.get('risk_tolerance', 'low'))
    db.commit()
    return {'routes': records, 'recommended_id': selected, 'warning': warning}
