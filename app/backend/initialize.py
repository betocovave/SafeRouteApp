"""Run in the Azure init container, before any HTTP traffic is served."""
import subprocess
import sys
from sqlalchemy import text
from backend.data.database import engine

# Session lock survives the commits made by Alembic and the seed subprocess.
LOCK_ID = 73616665726


def initialize():
    if engine.dialect.name != 'postgresql':
        raise RuntimeError('La inicialización de producción requiere PostgreSQL/PostGIS.')
    with engine.connect().execution_options(isolation_level='AUTOCOMMIT') as connection:
        connection.execute(text('SELECT pg_advisory_lock(:key)'), {'key': LOCK_ID})
        try:
            subprocess.run([sys.executable, '-m', 'alembic', '-c', 'backend/alembic.ini', 'upgrade', 'head'], check=True)
            connection.execute(text('CREATE TABLE IF NOT EXISTS deployment_state (name text PRIMARY KEY)'))
            seeded = connection.scalar(text("SELECT 1 FROM deployment_state WHERE name = 'initial_seed'"))
            if not seeded:
                subprocess.run([sys.executable, '-m', 'backend.cli', 'seed'], check=True)
                # Only mark success after seed committed. Its inserts are idempotent
                # if the process is interrupted between the commit and this marker.
                connection.execute(text("INSERT INTO deployment_state (name) VALUES ('initial_seed')"))
        finally:
            connection.execute(text('SELECT pg_advisory_unlock(:key)'), {'key': LOCK_ID})


if __name__ == '__main__':
    initialize()
