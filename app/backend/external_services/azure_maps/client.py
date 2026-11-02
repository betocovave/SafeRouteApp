import httpx
import logging
from fastapi import HTTPException
from backend.config import settings
from backend.external_services.geolocation.service import within_city


def credentials():
    config = settings()
    if config.azure_maps_auth_mode == 'sas' and config.azure_maps_sas_token:
        return {'Authorization': 'jwt-sas ' + config.azure_maps_sas_token}
    if config.azure_maps_auth_mode == 'key' and config.azure_maps_api_key:
        return {'subscription-key': config.azure_maps_api_key}
    raise HTTPException(503, 'El servicio de mapas no está configurado. Inténtalo más tarde.')


def upstream_error(status):
    # Registrar únicamente el código, nunca encabezados, URLs ni la respuesta de Azure.
    logging.getLogger('saferoute.azure').warning('Azure Maps HTTP %s', status)
    if status in (401, 403):
        return HTTPException(503, 'Azure Maps rechazó las credenciales o permisos del servidor. Revisa la configuración de Azure y reinicia el backend.')
    if status == 429:
        return HTTPException(503, 'Azure Maps alcanzó su límite de solicitudes. Espera un momento y vuelve a intentar.')
    return HTTPException(502, 'Azure Maps no pudo completar la solicitud. Inténtalo nuevamente.')


async def request(method, path, params=None, body=None):
    headers = {**credentials(), 'Accept-Language': 'es-MX'}
    if body:
        headers['Content-Type'] = 'application/geo+json'
    try:
        async with httpx.AsyncClient(timeout=settings().request_timeout) as client:
            response = await client.request(method, 'https://atlas.microsoft.com' + path, headers=headers, params=params, json=body)
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        raise HTTPException(504, 'Azure Maps tardó demasiado. Inténtalo nuevamente.')
    except httpx.HTTPStatusError as exc:
        raise upstream_error(exc.response.status_code) from None
    except (httpx.HTTPError, ValueError):
        # No exponer respuestas ni URLs que puedan contener credenciales.
        raise HTTPException(502, 'Azure Maps no está disponible o rechazó la configuración.')


def in_municipality(feature):
    # El recuadro es rectangular y puede incluir otros municipios; Azure reporta el municipio en adminDistricts.
    return any(d.get('shortName') == 'Salamanca' for d in feature.get('properties', {}).get('address', {}).get('adminDistricts', []))


async def search(query):
    result = await request('GET', '/geocode', {'api-version': '2025-01-01', 'query': query + ', Salamanca, Guanajuato, México', 'top': 8, 'bbox': '-101.30,20.48,-101.08,20.68'})
    return [{'label': x.get('properties', {}).get('address', {}).get('formattedAddress', query), 'longitude': x['geometry']['coordinates'][0], 'latitude': x['geometry']['coordinates'][1]} for x in result.get('features', []) if x.get('geometry', {}).get('type') == 'Point' and within_city(*x['geometry']['coordinates'][:2]) and in_municipality(x)]


async def reverse(longitude, latitude):
    result = await request('GET', '/reverseGeocode', {'api-version': '2025-01-01', 'coordinates': f'{longitude},{latitude}', 'resultTypes': 'Address'})
    address = next(iter(result.get('features', [])), {}).get('properties', {}).get('address', {})
    return {'label': address.get('addressLine') or address.get('formattedAddress') or 'Calle sin nombre', 'street': address.get('streetName'), 'neighborhood': address.get('neighborhood'), 'postal_code': address.get('postalCode')}


def parse_routes(result):
    routes = []
    for collection in [result, *result.get('alternativeRoutes', [])]:
        features = collection.get('features', [])
        paths = [f for f in features if f.get('properties', {}).get('type') == 'RoutePath']
        if not paths:
            continue
        path = paths[0]
        geo = path['geometry']
        points = geo['coordinates'] if geo['type'] == 'LineString' else [p for segment in geo['coordinates'] for p in segment]
        points = [p[:2] for i, p in enumerate(points) if i == 0 or p != points[i-1]]
        if len(points) < 2:
            continue
        props = path['properties']
        instructions = []
        for f in features:
            p = f.get('properties', {})
            instruction = p.get('instruction', {})
            if f.get('geometry', {}).get('type') == 'Point' and instruction.get('text'):
                instructions.append({'text': instruction['text'], 'coordinates': f['geometry']['coordinates'][:2], 'distance_m': p.get('distanceInMeters', 0), 'duration_s': p.get('durationInSeconds', 0)})
        routes.append({'geometry': {'type': 'LineString', 'coordinates': points}, 'distance_m': props['distanceInMeters'], 'duration_s': props.get('durationTrafficInSeconds', props['durationInSeconds']), 'instructions': instructions})
    return routes


async def directions(origin, destination, transport, via=None):
    points = [origin, *(via or []), destination]
    body = {'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': point}, 'properties': {'pointIndex': i, 'pointType': 'waypoint' if i in (0, len(points)-1) else 'viaWaypoint'}} for i, point in enumerate(points)], 'travelMode': transport, 'routeOutputOptions': ['routePath', 'itinerary'], 'optimizeRoute': 'fastestWithTraffic' if transport == 'driving' else 'shortest'}
    if transport == 'driving':
        body['maxRouteCount'] = 3
    return parse_routes(await request('POST', '/route/directions', {'api-version': '2025-01-01'}, body))
