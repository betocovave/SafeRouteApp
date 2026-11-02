"""Production bootstrap against a disposable PostgreSQL database only."""
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

pytestmark = pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Requiere PostGIS y TEST_DATABASE_URL con sufijo _test')


@pytest.fixture
def bootstrap_db():
    url = os.environ['TEST_DATABASE_URL']
    assert make_url(url).database.endswith('_test')
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text('DROP SCHEMA public CASCADE'))
        connection.execute(text('CREATE SCHEMA public'))
    yield engine, {**os.environ, 'DATABASE_URL': url}
    engine.dispose()


def run_init(env):
    return subprocess.run([sys.executable, '-m', 'backend.initialize'], env=env, capture_output=True, text=True, timeout=60)


def test_parallel_initialization_and_seed_only_once(bootstrap_db):
    engine, env = bootstrap_db
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run_init, [env, env]))
    assert all(result.returncode == 0 for result in results), [r.stderr for r in results]
    with engine.begin() as connection:
        assert connection.scalar(text('SELECT count(*) FROM categories')) == 14
        assert connection.scalar(text('SELECT count(*) FROM deployment_state')) == 1
        assert connection.scalar(text('SELECT version_num FROM alembic_version')) == '0001'
        connection.execute(text("DELETE FROM categories WHERE id = 'theft'"))
    result = run_init(env)
    assert result.returncode == 0, result.stderr
    with engine.connect() as connection:
        # A restart must not reinsert a category removed by an administrator.
        assert connection.scalar(text('SELECT count(*) FROM categories')) == 13


def test_failed_migration_does_not_mark_seed_or_keep_lock(bootstrap_db):
    engine, env = bootstrap_db
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE alembic_version (version_num varchar(32) PRIMARY KEY)'))
        connection.execute(text("INSERT INTO alembic_version VALUES ('missing_revision')"))
    result = run_init(env)
    assert result.returncode != 0
    with engine.begin() as connection:
        assert connection.scalar(text("SELECT to_regclass('public.deployment_state')")) is None
        connection.execute(text('DROP TABLE alembic_version'))
    # A failed init released its session lock, and a corrected deployment can start.
    result = run_init(env)
    assert result.returncode == 0, result.stderr
