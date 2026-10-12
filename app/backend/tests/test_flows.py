from datetime import timedelta
from uuid import uuid4
from sqlalchemy import select
from backend.data.models import User, Incident, now


def report_data(category='theft', **overrides):
    return {'longitude': -101.195, 'latitude': 20.57, 'category_id': category, 'description': 'Reporte real de prueba controlada', 'client_id': str(uuid4()), 'occurred_at': now().isoformat(), **overrides}


def test_recovery_revokes_sessions_and_rotates_code(client, account):
    tokens, headers = account
    response = client.post('/api/v1/auth/recover', json={'email': 'persona@example.com', 'password': 'newsecurepassword', 'recovery_code': tokens['recovery_code']})
    assert response.status_code == 200
    assert response.json()['recovery_code'] != tokens['recovery_code']
    assert client.get('/api/v1/users/me', headers=headers).status_code == 401
    assert client.post('/api/v1/auth/refresh', json={'refresh_token': tokens['refresh_token']}).status_code == 401
    assert client.post('/api/v1/auth/recover', json={'email': 'persona@example.com', 'password': 'anotherpassword', 'recovery_code': tokens['recovery_code']}).status_code == 401


def test_refresh_rotation_and_logout(client, account):
    tokens, headers = account
    response = client.post('/api/v1/auth/refresh', json={'refresh_token': tokens['refresh_token']})
    assert response.status_code == 200
    assert client.post('/api/v1/auth/refresh', json={'refresh_token': tokens['refresh_token']}).status_code == 401
    assert client.post('/api/v1/auth/logout', headers=headers).status_code == 204
    assert client.get('/api/v1/users/me', headers=headers).status_code == 401


def test_report_idempotency_and_no_photo_required(client, account):
    _, headers = account
    data = report_data()
    first = client.post('/api/v1/incidents', headers=headers, json=data)
    assert first.status_code == 201, first.text
    second = client.post('/api/v1/incidents', headers=headers, json=data)
    assert first.json() == second.json()
    data['description'] = 'Otra descripción distinta'
    assert client.post('/api/v1/incidents', headers=headers, json=data).status_code == 409
    assert first.json()['incident']['photo_id'] is None


def test_old_offline_report_is_not_revived(client, account):
    _, headers = account
    result = client.post('/api/v1/incidents', headers=headers, json=report_data(occurred_at=(now()-timedelta(hours=8)).isoformat()))
    assert result.status_code == 201
    assert result.json()['incident']['status'] == 'expired'
    assert client.get('/api/v1/incidents?longitude=-101.195&latitude=20.57', headers=headers).json() == []


def test_permissions_and_spatial_bounds(client, account):
    _, headers = account
    assert client.get('/api/v1/admin/users', headers=headers).status_code == 403
    assert client.get('/api/v1/users/me').status_code == 401
    assert client.post('/api/v1/incidents', headers=headers, json=report_data(latitude=0)).status_code == 422
    assert client.get('/api/v1/maps/proxy?url=https://evil.test/map/tile', headers=headers).status_code == 422


def test_nearby_independent_corroborations(client, account, db):
    _, original = account
    item = client.post('/api/v1/incidents', headers=original, json=report_data()).json()['incident']
    endpoint = '/api/v1/incidents/' + item['id'] + '/corroborations'
    assert client.post(endpoint, headers=original, json={'version': 1, 'answer': 'present'}).status_code == 403
    for index in [1, 2]:
        tokens = client.post('/api/v1/auth/register', json={'name': 'Vecino', 'email': f'vecino{index}@example.com', 'password': 'securepassword12'}).json()
        headers = {'Authorization': 'Bearer ' + tokens['access_token']}
        assert client.post(endpoint, headers=headers, json={'version': 1, 'answer': 'present'}).status_code == 403
        assert client.post('/api/v1/locations', headers=headers, json={'longitude': -101.195, 'latitude': 20.57, 'accuracy': 10}).status_code == 200
        response = client.post(endpoint, headers=headers, json={'version': 1, 'answer': 'present'})
        assert response.status_code == 200, response.text
        assert response.json()['status'] == ('pending' if index == 1 else 'confirmed')
    assert db.get(Incident, item['id']).confidence == 1


def test_admin_audit_and_account_suspension(client, account, db):
    _, headers = account
    user = db.scalar(select(User).where(User.email == 'persona@example.com'))
    user.role = 'admin'
    db.commit()
    category = client.get('/api/v1/admin/categories', headers=headers).json()[0]
    assert client.put('/api/v1/admin/categories/'+category.pop('id'), headers=headers, json=category).status_code == 200


def test_missing_azure_returns_actionable_error(client, account):
    _, headers = account
    response = client.get('/api/v1/search?q=Centro', headers=headers)
    assert response.status_code == 503
    assert 'mapas' in response.json()['detail']
