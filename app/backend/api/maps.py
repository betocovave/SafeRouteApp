import asyncio
import hashlib
import json
from urllib.parse import urlsplit, parse_qsl, urlencode
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import Field
from backend.api.schemas import Point
from backend.authentication.security import current_user
from backend.config import settings
from backend.external_services.azure_maps.client import credentials
from backend.external_services.geolocation.service import require_city
from backend.business.routes.corridors import graph_for
from backend.data.models import now

router = APIRouter(prefix='/api/v1')


class PackageInput(Point):
    radius_m: int = Field(default=2000, ge=100, le=2000)


@router.get('/maps/proxy')
async def map_proxy(url: str = Query(max_length=3000), user=Depends(current_user)):
    target = urlsplit(url)
    if target.scheme != 'https' or target.hostname != 'atlas.microsoft.com' or not target.path.startswith('/map/') or target.username or target.port not in (None, 443):
        raise HTTPException(422, 'Recurso cartográfico no permitido.')
    query = [(key, value) for key, value in parse_qsl(target.query) if key.lower() not in ('subscription-key', 'token', 'authorization', 'clientid', 'x-ms-client-id')]
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=False) as client:
            result = await client.get('https://atlas.microsoft.com' + target.path + '?' + urlencode(query), headers=credentials())
        if result.status_code != 200:
            raise HTTPException(502, 'No se pudo cargar este recurso de Azure Maps.')
        return Response(result.content, media_type=result.headers.get('content-type', 'application/octet-stream'), headers={'Cache-Control': 'private, no-store'})
    except httpx.HTTPError:
        raise HTTPException(502, 'Azure Maps no está disponible.')


def make_package(data):
    from shapely.geometry import LineString, Point as GeoPoint, mapping
    from shapely.ops import transform
    from math import cos, radians
    sx, sy = 111320*cos(radians(data.latitude)), 110540
    project = lambda x, y, z=None: ((x-data.longitude)*sx, (y-data.latitude)*sy)
    unproject = lambda x, y, z=None: (x/sx+data.longitude, y/sy+data.latitude)
    area = GeoPoint(0, 0).buffer(data.radius_m)
    features, signatures = [], set()
    for mode in ['driving', 'walking']:
        graph = graph_for(mode)
        for u, v, edge in graph.edges(data=True):
            line = edge.get('geometry')
            if line is None:
                line = LineString([(graph.nodes[u]['x'], graph.nodes[u]['y']), (graph.nodes[v]['x'], graph.nodes[v]['y'])])
            clipped = transform(project, line).intersection(area)
            if clipped.is_empty or clipped.geom_type not in ('LineString', 'MultiLineString'):
                continue
            geo = mapping(transform(unproject, clipped))
            signature = json.dumps(geo, sort_keys=True)
            if signature in signatures:
                continue
            signatures.add(signature)
            name = edge.get('name', '')
            features.append({'type': 'Feature', 'geometry': geo, 'properties': {'name': ', '.join(name) if isinstance(name, list) else str(name)}})
    package = {'type': 'FeatureCollection', 'features': features, 'metadata': {'center': [data.longitude, data.latitude], 'radius_m': data.radius_m, 'created_at': now().isoformat(), 'attribution': '© OpenStreetMap contributors - ODbL', 'source': 'OpenStreetMap, cartografía vectorial generada por SafeRouteAI'}}
    content = json.dumps(package, ensure_ascii=False, separators=(',', ':')).encode()
    if len(content) > 50*1024*1024:
        raise HTTPException(413, 'El sector supera 50 MB. Reduce su tamaño.')
    return content


@router.post('/offline-packages')
async def offline_package(data: PackageInput, user=Depends(current_user)):
    require_city(data.longitude, data.latitude)
    content = await asyncio.to_thread(make_package, data)
    return Response(content, media_type='application/geo+json', headers={'X-Package-SHA256': hashlib.sha256(content).hexdigest(), 'X-Package-Bytes': str(len(content)), 'Cache-Control': 'private, no-store'})
