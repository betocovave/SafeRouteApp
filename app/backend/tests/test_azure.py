from backend.external_services.azure_maps.client import parse_routes
from backend.external_services.azure_maps.client import upstream_error
import pytest


def test_parse_current_geojson_route_contract():
    result = {'type': 'FeatureCollection', 'features': [
        {'geometry': {'type': 'MultiLineString', 'coordinates': [[[-101.2, 20.57], [-101.19, 20.58]]]}, 'properties': {'type': 'RoutePath', 'distanceInMeters': 1500, 'durationInSeconds': 200}},
        {'geometry': {'type': 'Point', 'coordinates': [-101.2, 20.57]}, 'properties': {'type': 'ManeuverPoint', 'instruction': {'text': 'Gira a la derecha'}, 'distanceInMeters': 100, 'durationInSeconds': 10}}
    ]}
    routes = parse_routes(result)
    assert routes[0]['distance_m'] == 1500
    assert routes[0]['instructions'][0]['text'] == 'Gira a la derecha'
    assert routes[0]['geometry']['type'] == 'LineString'


@pytest.mark.parametrize('status,expected,fragment', [(401, 503, 'credenciales'), (403, 503, 'permisos'), (429, 503, 'límite'), (500, 502, 'solicitud')])
def test_upstream_error_is_actionable_without_leaking_credentials(status, expected, fragment):
    error = upstream_error(status)
    assert error.status_code == expected
    assert fragment in error.detail


@pytest.mark.asyncio
async def test_azure_rejected_key_does_not_leak_request_headers(monkeypatch):
    import httpx
    from fastapi import HTTPException
    from backend.external_services.azure_maps import client
    original = httpx.AsyncClient
    async def reject(request):
        return httpx.Response(401, json={'error': {'message': 'secret-in-upstream-error'}})
    monkeypatch.setattr(client, 'credentials', lambda: {'subscription-key': 'private-key'})
    monkeypatch.setattr(client.httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(reject), **kwargs))
    with pytest.raises(HTTPException) as exc:
        await client.request('GET', '/geocode')
    assert exc.value.status_code == 503
    assert 'private-key' not in exc.value.detail
    assert 'secret-in-upstream-error' not in exc.value.detail


@pytest.mark.asyncio
async def test_search_keeps_only_places_in_the_salamanca_municipality(monkeypatch):
    from backend.external_services.azure_maps import client
    def place(name, municipality):
        return {'geometry': {'type': 'Point', 'coordinates': [-101.2, 20.57]}, 'properties': {'address': {'formattedAddress': name, 'adminDistricts': [{'shortName': 'GTO'}, {'shortName': municipality}]}}}
    async def request(*args, **kwargs):
        return {'features': [place('Valtierrilla', 'Salamanca'), place('Otro municipio dentro del recuadro', 'Irapuato')]}
    monkeypatch.setattr(client, 'request', request)
    assert [x['label'] for x in await client.search('colonia')] == ['Valtierrilla']


@pytest.mark.asyncio
async def test_reverse_returns_street_info_or_fallback(monkeypatch):
    from backend.external_services.azure_maps import client
    responses = [{'features': [{'properties': {'address': {'addressLine': 'Calle Guerrero 12', 'streetName': 'Calle Guerrero', 'neighborhood': 'Centro', 'postalCode': '36700'}}}]}, {'features': []}]
    async def request(*args, **kwargs):
        return responses.pop(0)
    monkeypatch.setattr(client, 'request', request)
    assert await client.reverse(-101.19, 20.57) == {'label': 'Calle Guerrero 12', 'street': 'Calle Guerrero', 'neighborhood': 'Centro', 'postal_code': '36700'}
    assert (await client.reverse(-101.19, 20.57))['label'] == 'Calle sin nombre'
