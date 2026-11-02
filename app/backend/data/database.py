from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from backend.config import settings


class Base(DeclarativeBase):
    pass


def connection_options(config):
    url = make_url(config.database_url)
    options = {'pool_pre_ping': True}
    if url.get_backend_name() == 'postgresql':
        # Compose publishes IPv4 loopback only. Avoid Windows trying ::1 first.
        if config.environment == 'development' and url.host == 'localhost':
            url = url.set(host='127.0.0.1')
        options.update(connect_args={'connect_timeout': 5}, pool_timeout=5)
    return url, options


database_url, engine_options = connection_options(settings())
engine = create_engine(database_url, **engine_options)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as db:
        yield db
