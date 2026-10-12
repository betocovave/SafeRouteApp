from datetime import timedelta
from io import BytesIO
from PIL import Image
from backend.data.models import Incident, now
from backend.intelligence.risk_algorithm.engine import evaluate
from backend.media.photos import sanitize

PATH = {'type': 'LineString', 'coordinates': [[-101.196, 20.57], [-101.194, 20.57]]}


def test_no_data_is_insufficient(db):
    result = evaluate(db, PATH)
    assert result['risk_index'] is None
    assert result['safety_index'] is None


def test_critical_incident_explains_route(db):
    incident = Incident(category_id='confrontation', longitude=-101.195, latitude=20.57, description='Prueba', occurred_at=now(), updated_at=now(), expires_at=now()+timedelta(hours=6))
    db.add(incident)
    db.commit()
    result = evaluate(db, PATH)
    assert result['critical']
    assert 0 <= result['risk_index'] <= 100
    assert result['factors'][0]['incident_id'] == incident.id


def test_resolved_incident_remains_historical_not_critical(db):
    db.add(Incident(category_id='confrontation', longitude=-101.195, latitude=20.57, description='Prueba', status='resolved', occurred_at=now()-timedelta(days=1), updated_at=now(), expires_at=now()+timedelta(hours=6)))
    db.commit()
    assert not evaluate(db, PATH)['critical']


def test_photo_exif_is_removed():
    image = Image.new('RGB', (30, 30), 'blue')
    exif = Image.Exif()
    exif[270] = 'private metadata'
    original = BytesIO()
    image.save(original, format='JPEG', exif=exif)
    clean = Image.open(BytesIO(sanitize(original.getvalue())))
    assert len(clean.getexif()) == 0


def test_reject_non_image():
    import pytest
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        sanitize(b'not-an-image')
