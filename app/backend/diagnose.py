"""Run from app: .venv/Scripts/python.exe -m backend.diagnose. Never prints secrets."""
import asyncio
import sys
import httpx
from fastapi import HTTPException
from backend.config import settings
from backend.external_services.azure_maps.client import credentials, directions, search, upstream_error


async def main():
    failures = []
    async def check(name, operation):
        try:
            await operation()
            print(f'[OK] {name}', flush=True)
        except HTTPException as exc:
            failures.append(name)
            print(f'[ERROR] {name}: {exc.detail}', flush=True)
        except Exception as exc:
            failures.append(name)
            print(f'[ERROR] {name}: {type(exc).__name__}. Revisa que el servicio este iniciado.', flush=True)

    async def backend():
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get('http://127.0.0.1:8000/ready')
            if response.status_code != 200 or response.json().get('database') != 'ready':
                raise HTTPException(503, 'La API responde, pero PostgreSQL no esta listo. Revisa Docker.')

    async def tiles():
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get('https://atlas.microsoft.com/map/tile', headers=credentials(), params={
                'api-version': '2.1', 'tilesetId': 'microsoft.base.road', 'zoom': 14, 'x': 3586, 'y': 7235})
            if response.status_code != 200:
                raise upstream_error(response.status_code)

    async def routes():
        for mode in ('driving', 'walking'):
            if not await directions([-101.195, 20.57], [-101.19, 20.575], mode):
                raise HTTPException(502, f'Azure no devolvio rutas para {mode}.')

    async def graphs():
        for mode in ('driving', 'walking'):
            if not (settings().osm_directory / f'salamanca_{mode}.graphml').is_file():
                raise HTTPException(503, 'Faltan redes OSM. Ejecuta python -m backend.cli prepare-osm.')

    await check('API y PostgreSQL', backend)
    await check('Cartografia Azure Maps', tiles)
    await check('Busqueda Azure Maps', lambda: search('Centro'))
    await check('Rutas Azure auto y caminata', routes)
    await check('Redes locales OSM', graphs)
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
