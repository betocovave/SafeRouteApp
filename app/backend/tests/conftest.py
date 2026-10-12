import os
os.environ['JWT_SECRET'] = 'test-only-secret-at-least-thirty-two-characters'
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['ENABLE_JOBS'] = 'false'

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from backend.data.database import Base, get_db
from backend.data.seed import seed
from backend.main import app
from backend.api.endpoints import auth_attempts


@pytest.fixture
def db():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with sessionmaker(engine, expire_on_commit=False)() as session:
        seed(session)
        yield session
    engine.dispose()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    auth_attempts.clear()
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def account(client):
    response = client.post('/api/v1/auth/register', json={'name': 'Persona', 'email': 'persona@example.com', 'password': 'securepassword12'})
    assert response.status_code == 201, response.text
    tokens = response.json()
    return tokens, {'Authorization': 'Bearer ' + tokens['access_token']}
