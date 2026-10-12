"""Run only against a dedicated disposable PostGIS TEST_DATABASE_URL."""
import os
import pytest
from sqlalchemy import create_engine, text


@pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Requires an isolated PostGIS database')
def test_postgis_geography_distance_and_index():
    engine = create_engine(os.environ['TEST_DATABASE_URL'])
    with engine.begin() as connection:
        connection.execute(text('CREATE EXTENSION IF NOT EXISTS postgis'))
        connection.execute(text('CREATE TEMP TABLE test_incidents (position geometry(Point,4326))'))
        connection.execute(text('CREATE INDEX ON test_incidents USING gist ((position::geography))'))
        connection.execute(text("INSERT INTO test_incidents VALUES (ST_GeomFromText('POINT(-101.195 20.57)',4326))"))
        count = connection.scalar(text("SELECT count(*) FROM test_incidents WHERE ST_DWithin(position::geography, ST_GeomFromText('LINESTRING(-101.196 20.57,-101.194 20.57)',4326)::geography,300)"))
        assert count == 1
    engine.dispose()
