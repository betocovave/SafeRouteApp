"""Se ejecuta con infrastructure/test-postgis.ps1; recrea el esquema de una base *_test desechable."""
import os
import subprocess
import sys
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from backend.api.endpoints import auth_attempts
from backend.business.routes import service
from backend.data.database import get_db
from backend.data.models import Incident
from backend.data.seed import seed
from backend.intelligence.risk_algorithm.engine import line_distance_m, nearby
from backend.main import app

needs_pg = pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Ejecuta infrastructure/test-postgis.ps1 (requiere Docker)')


def fresh_test_schema(url):
    """Recrea el esquema con las migraciones reales; solo en bases cuyo nombre termina en _test."""
    assert make_url(url).database.endswith('_test'), 'TEST_DATABASE_URL debe apuntar a una base *_test desechable.'
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text('DROP SCHEMA public CASCADE'))
        connection.execute(text('CREATE SCHEMA public'))
    # Subproceso: conftest fija DATABASE_URL=sqlite:// y alembic toma el engine de settings().
    subprocess.run([sys.executable, '-m', 'alembic', '-c', 'backend/alembic.ini', 'upgrade', 'head'], env={**os.environ, 'DATABASE_URL': url}, check=True)
    with Session(engine) as db:
        seed(db)
    return engine


@pytest.fixture(scope='module')
def pg():
    engine = fresh_test_schema(os.environ['TEST_DATABASE_URL'])
    yield engine
    engine.dispose()


@needs_pg
def test_postgis_geography_distance_and_index():
    engine = create_engine(os.environ['TEST_DATABASE_URL'])
    with engine.begin() as connection:
        connection.execute(text('CREATE EXTENSION IF NOT EXISTS postgis'))
        connection.execute(text('CREATE TEMP TABLE test_incidents (position geometry(Point,4326))'))
        connection.execute(text('CREATE INDEX ON test_incidents USING gist ((position::geography))'))
        connection.execute(text("INSERT INTO test_incidents VALUES (ST_GeomFromText('POINT(-101.195 20.57)',4326))"))
        count = connection.scalar(text("SELECT count(*) FROM test_incidents WHERE ST_DWithin(position::geography, ST_GeomFromText('LINESTRING(-101.196 20.57,-101.194 20.57)',4326)::geography,300)"))
        assert count == 1
    engine.dispose()


def test_schema_helper_refuses_non_test_database():
    with pytest.raises(AssertionError):
        fresh_test_schema('postgresql+psycopg://saferoute:x@127.0.0.1:5432/saferoute')


@needs_pg
def test_migration_creates_users_sessions_and_spatial_column(pg):
    with pg.connect() as connection:
        tables = set(connection.scalars(text("SELECT tablename FROM pg_tables WHERE schemaname='public'")))
        assert {'users', 'sessions', 'incidents'} <= tables
        assert connection.scalar(text("SELECT udt_name FROM information_schema.columns WHERE table_name='incidents' AND column_name='position'")) == 'geometry'


@pytest.fixture
def pg_client(pg):
    with Session(pg, expire_on_commit=False) as db:
        app.dependency_overrides[get_db] = lambda: db
        auth_attempts.clear()
        with TestClient(app) as client:
            yield client, db
        app.dependency_overrides.clear()


def register(client, email):
    response = client.post('/api/v1/auth/register', json={'name': 'Persona', 'email': email, 'password': 'securepassword12'})
    assert response.status_code == 201, response.text
    return {'Authorization': 'Bearer ' + response.json()['access_token']}


@needs_pg
def test_users_register_login_and_duplicate_email_on_postgres(pg_client):
    client, db = pg_client
    headers = register(client, 'usuario@example.com')
    assert client.post('/api/v1/auth/register', json={'name': 'Persona', 'email': 'usuario@example.com', 'password': 'securepassword12'}).status_code == 409
    assert client.post('/api/v1/auth/login', json={'email': 'usuario@example.com', 'password': 'securepassword12'}).status_code == 200
    assert client.get('/api/v1/users/me', headers=headers).json()['preferences']['theme'] == 'system'
    assert db.scalar(text("SELECT count(*) FROM users WHERE email='usuario@example.com'")) == 1


@needs_pg
def test_reported_incident_stores_position_and_risk_uses_postgis_distance(pg_client):
    client, db = pg_client
    headers = register(client, 'reporta@example.com')
    response = client.post('/api/v1/incidents', headers=headers, json={'category_id': 'accident', 'description': 'Choque en la esquina', 'client_id': '6f1c1b0e-0000-4000-8000-000000000001', 'occurred_at': datetime.now(timezone.utc).isoformat(), 'latitude': 20.5703, 'longitude': -101.195})
    assert response.status_code == 201, response.text
    incident_id = response.json()['incident']['id']
    assert db.scalar(text('SELECT position IS NOT NULL FROM incidents WHERE id=:id'), {'id': incident_id}) is True
    near = [[-101.196, 20.57], [-101.194, 20.57]]
    found = nearby(db, {'type': 'LineString', 'coordinates': near})
    assert [i.id for i, _, _ in found] == [incident_id]
    assert abs(found[0][2] - line_distance_m(near, [-101.195, 20.5703])) < 2  # misma distancia que la ruta SQLite
    assert nearby(db, {'type': 'LineString', 'coordinates': [[-101.196, 20.58], [-101.194, 20.58]]}) == []


@needs_pg
def test_calculated_route_is_stored_as_linestring(pg_client, monkeypatch):
    client, db = pg_client
    headers = register(client, 'ruta@example.com')
    geometry = {'type': 'LineString', 'coordinates': [[-101.196, 20.57], [-101.194, 20.57]]}
    async def directions(*args, **kwargs):
        return [{'geometry': geometry, 'distance_m': 200, 'duration_s': 100, 'instructions': []}]
    monkeypatch.setattr(service.client, 'directions', directions)
    monkeypatch.setattr(service, 'safe_corridor', lambda *args: [])
    response = client.post('/api/v1/routes', headers=headers, json={'origin': {'longitude': -101.196, 'latitude': 20.57}, 'destination': {'longitude': -101.194, 'latitude': 20.57}, 'transport': 'walking'})
    assert response.status_code == 200, response.text
    route_id = response.json()['routes'][0]['id']
    assert db.execute(text('SELECT ST_GeometryType(path), ST_SRID(path) FROM routes WHERE id=:id'), {'id': route_id}).one() == ('ST_LineString', 4326)
    assert 'risk_index' in response.json()['routes'][0]['evaluation']
