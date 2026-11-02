from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from backend.config import Settings
from backend.data.database import connection_options

PRODUCTION = dict(environment='production', public_api_url='https://api.example.com', database_url='postgresql+psycopg://app:s3cret@db/app', cors_origins='https://app.example.com')


def test_production_accepts_real_configuration():
    Settings(**PRODUCTION)


@pytest.mark.parametrize('override', [{'public_api_url': 'http://api.example.com'}, {'database_url': 'postgresql+psycopg://saferoute:saferoute@db/app'}, {'cors_origins': 'http://localhost:8081'}, {'environment': 'prod'}])
def test_production_rejects_development_defaults(override):
    with pytest.raises(ValidationError):
        Settings(**{**PRODUCTION, **override})


def test_development_postgres_uses_compose_ipv4_and_bounded_connection():
    url, options = connection_options(SimpleNamespace(database_url='postgresql+psycopg://user:password@localhost:5432/db', environment='development'))
    assert url.host == '127.0.0.1'
    assert url.password == 'password'
    assert options['connect_args']['connect_timeout'] == 5


def test_production_and_sqlite_keep_their_host_and_supported_options():
    url, _ = connection_options(SimpleNamespace(database_url='postgresql+psycopg://user:password@db:5432/db', environment='production'))
    assert url.host == 'db'
    url, options = connection_options(SimpleNamespace(database_url='sqlite://', environment='development'))
    assert 'connect_args' not in options
    assert 'pool_timeout' not in options
