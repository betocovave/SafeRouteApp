import argparse
import getpass
import json
import secrets
from sqlalchemy import select
from backend.data.database import SessionLocal
from backend.data.models import User
from backend.data.seed import seed
from backend.authentication.security import hasher
from backend.config import settings


def main():
    parser = argparse.ArgumentParser(description='SafeRouteAI maintenance')
    parser.add_argument('command', choices=['seed', 'create-admin', 'prepare-osm', 'export-openapi'])
    args = parser.parse_args()
    if args.command == 'export-openapi':
        from backend.main import app
        path = settings().osm_directory.parent.parent.parent / 'docs' / 'openapi.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2), encoding='utf-8')
    elif args.command == 'prepare-osm':
        import osmnx as ox
        from backend.external_services.geolocation.service import BOUNDS
        settings().osm_directory.mkdir(parents=True, exist_ok=True)
        ox.settings.cache_folder = str(settings().osm_directory / 'cache')
        for mode, kind in [('driving', 'drive'), ('walking', 'walk')]:
            path = settings().osm_directory / f'salamanca_{mode}.graphml'
            if not path.exists():
                graph = ox.graph_from_bbox(BOUNDS, network_type=kind)
                ox.save_graphml(graph, path)
            print(f'OSM {mode}: listo')
    else:
        with SessionLocal() as db:
            if args.command == 'seed':
                seed(db)
            else:
                email = input('Correo de administrador: ').strip().lower()
                if db.scalar(select(User.id).where(User.email == email)):
                    parser.error('La cuenta ya existe. No se cambian permisos de cuentas existentes.')
                name = input('Nombre: ').strip()
                password = getpass.getpass('Contraseña (mínimo 10 caracteres): ')
                if len(password) < 10 or '@' not in email or len(name) < 2:
                    parser.error('Datos inválidos.')
                code = secrets.token_urlsafe(32)
                db.add(User(name=name, email=email, password_hash=hasher.hash(password), recovery_hash=hasher.hash(code), role='admin'))
                db.commit()
                print('Guarda este código privado de recuperación; no volverá a mostrarse:')
                print(code)


if __name__ == '__main__':
    main()
