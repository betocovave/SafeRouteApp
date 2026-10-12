from datetime import datetime, timedelta, timezone
from backend.data.models import Incident, now
from backend.intelligence.risk_algorithm.engine import evaluate

PATH = {'type': 'LineString', 'coordinates': [[-101.196, 20.57], [-101.194, 20.57]]}


def test_good_lighting_does_not_imply_complete_safety(db):
    db.add(Incident(category_id='light_good', description='Prueba', longitude=-101.195, latitude=20.57, occurred_at=now(), expires_at=now()+timedelta(days=30)))
    db.commit()
    assert evaluate(db, PATH)['risk_index'] is None


def test_lighting_contributes_only_at_night(db):
    midday = datetime(2026, 10, 11, 18, tzinfo=timezone.utc)
    db.add(Incident(category_id='light_none', description='Prueba', longitude=-101.195, latitude=20.57, occurred_at=midday, updated_at=midday, expires_at=midday+timedelta(days=30)))
    db.commit()
    assert evaluate(db, PATH, midday)['risk_index'] is None
    assert evaluate(db, PATH, midday+timedelta(hours=10))['risk_index'] > 0
