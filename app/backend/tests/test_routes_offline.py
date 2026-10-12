import json
from datetime import timedelta
import networkx as nx
import pytest
from backend.api.schemas import RouteInput
from backend.api.maps import PackageInput, make_package
from backend.data.models import Category, Incident, RouteRecord, User, now
from backend.business.routes import service, corridors
from backend.business.recommendations.service import recommendation


def fake_graph():
    graph = nx.MultiDiGraph(crs='epsg:4326')
    for n, coords in {1: (-101.196, 20.57), 2: (-101.195, 20.57), 3: (-101.194, 20.57), 4: (-101.195, 20.575)}.items():
        graph.add_node(n, x=coords[0], y=coords[1])
    for a, b in [(1, 2), (2, 3), (1, 4), (4, 3)]:
        graph.add_edge(a, b, length=100 if b == 2 or a == 2 else 700, name='Calle real de prueba')
    return graph


def test_critical_corridor_respects_direction(monkeypatch, db):
    monkeypatch.setattr(corridors, 'graph_for', lambda mode: fake_graph())
    hazard = Incident(longitude=-101.195, latitude=20.57, confidence=1)
    category = Category(critical=True, severity=1)
    via = corridors.safe_corridor([-101.196, 20.57], [-101.194, 20.57], 'driving', [(hazard, category)])
    # Zona critica cubre las aristas cortas; el desvio conserva sentidos.
    assert [-101.195, 20.575] in via
    assert corridors.safe_corridor([-101.194, 20.57], [-101.196, 20.57], 'driving', []) == []


def test_offline_package_local_generation_is_bounded(monkeypatch):
    import backend.api.maps as maps
    monkeypatch.setattr(maps, 'graph_for', lambda mode: fake_graph())
    content = make_package(PackageInput(longitude=-101.195, latitude=20.57, radius_m=100))
    package = json.loads(content)
    assert package['features']
    assert package['metadata']['radius_m'] == 100
    assert 'OpenStreetMap' in package['metadata']['attribution']
    assert len(content) < 50*1024*1024


def test_recommendation_rejects_critical_routes():
    routes = [{'id': 'unsafe', 'duration_s': 100, 'evaluation': {'critical': True, 'risk_index': 90}}]
    selected, warning = recommendation(routes, 'low')
    assert selected is None
    assert 'detente' in warning


@pytest.mark.asyncio
async def test_routes_deduplicate_and_persist_evaluations(db, monkeypatch):
    user = User(name='Usuario', email='routes@example.com', password_hash='hash', recovery_hash='hash')
    db.add(user); db.commit()
    geometry = {'type': 'LineString', 'coordinates': [[-101.196, 20.57], [-101.194, 20.57]]}
    async def directions(*args, **kwargs):
        return [{'geometry': geometry, 'distance_m': 200, 'duration_s': 100, 'instructions': []}]
    monkeypatch.setattr(service.client, 'directions', directions)
    monkeypatch.setattr(service, 'safe_corridor', lambda *args: [[-101.195, 20.57]])
    result = await service.calculate(db, user, RouteInput(origin={'longitude': -101.196, 'latitude': 20.57}, destination={'longitude': -101.194, 'latitude': 20.57}, transport='walking'))
    assert len(result['routes']) == 1
    assert result['routes'][0]['evaluation']['risk_index'] is None
    assert db.get(RouteRecord, result['routes'][0]['id']).transport == 'walking'


def test_expiration_removes_live_risk_and_keeps_history(db):
    from backend.business.incidents.service import expire
    item = Incident(category_id='theft', description='Prueba', longitude=-101.195, latitude=20.57, occurred_at=now()-timedelta(hours=7), expires_at=now()-timedelta(hours=1))
    db.add(item); db.commit()
    assert expire(db) == [item.id]
    assert item.status == 'expired'
