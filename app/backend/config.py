from functools import lru_cache
from pathlib import Path
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore')
    database_url: str = 'postgresql+psycopg://saferoute:saferoute@localhost:5432/saferoute'
    jwt_secret: str = Field(min_length=32)
    environment: str = 'development'
    azure_maps_api_key: str = ''
    azure_maps_sas_token: str = ''
    azure_maps_auth_mode: str = 'key'
    azure_blob_connection_string: str = ''
    azure_blob_container: str = 'incident-photos'
    cors_origins: str = 'http://localhost:8081'
    public_api_url: str = 'http://localhost:8000'
    enable_jobs: bool = True
    expo_access_token: str = ''
    request_timeout: float = 4.0
    max_photo_bytes: int = 8 * 1024 * 1024
    location_retention_minutes: int = 10
    osm_directory: Path = ROOT / 'data' / 'osm'

    @model_validator(mode='after')
    def validate_security(self):
        if 'REEMPLAZAR' in self.jwt_secret:
            raise ValueError('Genera JWT_SECRET antes de iniciar el servidor.')
        if self.environment == 'production' and (not self.public_api_url.startswith('https://') or not self.database_url.startswith('postgresql')):
            raise ValueError('Producción requiere HTTPS y PostgreSQL/PostGIS.')
        return self


@lru_cache
def settings():
    return Settings()
