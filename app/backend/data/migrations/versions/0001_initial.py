"""Initial transactional and spatial schema."""
from alembic import op
from backend.data.database import Base
from backend.data import models

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    if connection.dialect.name == 'postgresql':
        op.execute('CREATE EXTENSION IF NOT EXISTS postgis')
    Base.metadata.create_all(connection)
    if connection.dialect.name == 'postgresql':
        op.execute('CREATE INDEX IF NOT EXISTS ix_incidents_geography ON incidents USING gist ((position::geography))')


def downgrade():
    Base.metadata.drop_all(op.get_bind())
