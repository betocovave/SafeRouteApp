import json
from pathlib import Path
from datetime import timedelta
from zoneinfo import ZoneInfo
from math import exp
import numpy as np
from shapely.geometry import LineString, Point
from sqlalchemy import select, func, cast
from geoalchemy2 import Geography
from backend.data.models import Incident, Category, now, utc

RULES = json.loads(Path(__file__).with_name('rules.json').read_text())


def line_distance_m(coordinates, point):
    latitude = point[1]
    scale = np.array([111320 * np.cos(np.radians(latitude)), 110540])
    return float(LineString(np.asarray(coordinates) * scale).distance(Point(np.asarray(point) * scale)))


def nearby(db, geometry, historical=True):
    statement = select(Incident, Category).join(Category, Category.id == Incident.category_id).where(Incident.status != 'hidden')
    if historical:
        statement = statement.where(Incident.occurred_at >= now() - timedelta(days=RULES['historical_days']))
    else:
        statement = statement.where(Incident.status.in_(['pending', 'confirmed']), Incident.expires_at > now())
    if db.bind.dialect.name == 'postgresql':
        path = cast(func.ST_SetSRID(func.ST_GeomFromGeoJSON(json.dumps(geometry)), 4326), Geography(srid=4326))
        position = cast(Incident.position, Geography(srid=4326))
        statement = statement.add_columns(func.ST_Distance(position, path)).where(func.ST_DWithin(position, path, RULES['influence_radius_m']))
        return [(incident, category, float(d)) for incident, category, d in db.execute(statement)]
    return [(i, c, d) for i, c in db.execute(statement) if (d := line_distance_m(geometry['coordinates'], [i.longitude, i.latitude])) <= RULES['influence_radius_m']]


def evaluate(db, geometry, at=None):
    at = at or now()
    local_hour = at.astimezone(ZoneInfo('America/Mexico_City')).hour
    night_start, night_end = RULES['night_hours']
    night = local_hour >= night_start or local_hour < night_end if night_start > night_end else night_start <= local_hour < night_end
    factors = []
    critical = False
    for incident, category, meters in nearby(db, geometry):
        live = incident.status in ('pending', 'confirmed') and utc(incident.expires_at) > at
        age_hours = max(0, (at - utc(incident.updated_at)).total_seconds() / 3600)
        decay = exp(-age_hours / max(1, category.ttl_hours)) if live else RULES['historical_weight'] * exp(-age_hours / (24 * RULES['historical_days']))
        light_multiplier = 1 if category.group != 'lighting' or night else 0
        contribution = category.severity * RULES['group_weights'][category.group] * incident.confidence * decay * max(0, 1 - meters / RULES['influence_radius_m']) * light_multiplier
        dangerous = bool(live and category.critical and meters <= RULES['critical_distance_m'])
        critical |= dangerous
        factors.append({'incident_id': incident.id, 'category': category.name, 'distance_m': round(meters, 1), 'contribution': round(contribution, 5), 'confidence': incident.confidence, 'critical': dangerous})
    informative = any(x['contribution'] > 0 for x in factors)
    # Un reporte de buena iluminacion o un factor no aplicable no prueba ausencia de delitos.
    risk = round(100 * (1 - exp(-sum(x['contribution'] for x in factors) / RULES['risk_scale'])), 1) if informative else None
    critical |= risk is not None and risk >= RULES['critical_index']
    return {'risk_index': risk, 'safety_index': round(100-risk, 1) if risk is not None else None, 'label': 'Información insuficiente' if risk is None else ('Crítico' if critical else 'Elevado' if risk >= RULES['medium_index'] else 'Menor exposición'), 'critical': bool(critical), 'factors': sorted(factors, key=lambda x: -x['contribution']), 'calculated_at': at.isoformat(), 'rules_version': RULES['version'], 'observed_incidents': len(factors)}
