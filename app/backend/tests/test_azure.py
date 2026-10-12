from backend.external_services.azure_maps.client import parse_routes


def test_parse_current_geojson_route_contract():
    result = {'type': 'FeatureCollection', 'features': [
        {'geometry': {'type': 'MultiLineString', 'coordinates': [[[-101.2, 20.57], [-101.19, 20.58]]]}, 'properties': {'type': 'RoutePath', 'distanceInMeters': 1500, 'durationInSeconds': 200}},
        {'geometry': {'type': 'Point', 'coordinates': [-101.2, 20.57]}, 'properties': {'type': 'ManeuverPoint', 'instruction': {'text': 'Gira a la derecha'}, 'distanceInMeters': 100, 'durationInSeconds': 10}}
    ]}
    routes = parse_routes(result)
    assert routes[0]['distance_m'] == 1500
    assert routes[0]['instructions'][0]['text'] == 'Gira a la derecha'
    assert routes[0]['geometry']['type'] == 'LineString'
