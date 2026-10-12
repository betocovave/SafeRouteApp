from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geometry
from backend.data.database import Base


def now():
    return datetime.now(timezone.utc)


def uid():
    return str(uuid4())


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    recovery_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default='user')
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    preferences: Mapped[dict] = mapped_column(JSON, default=lambda: {'transport': 'driving', 'risk_tolerance': 'low', 'alerts': True, 'quiet_start': None, 'quiet_end': None, 'theme': 'system'})
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Session(Base):
    __tablename__ = 'sessions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    refresh_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class Category(Base):
    __tablename__ = 'categories'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    group: Mapped[str] = mapped_column(String(30))
    severity: Mapped[float] = mapped_column(Float)
    ttl_hours: Mapped[int] = mapped_column(Integer)
    critical: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Incident(Base):
    __tablename__ = 'incidents'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    category_id: Mapped[str] = mapped_column(ForeignKey('categories.id'), index=True)
    description: Mapped[str] = mapped_column(String(1000))
    longitude: Mapped[float] = mapped_column(Float)
    latitude: Mapped[float] = mapped_column(Float)
    position: Mapped[object | None] = mapped_column(JSON().with_variant(Geometry('POINT', srid=4326), 'postgresql'), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default='pending', index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)


class Report(Base):
    __tablename__ = 'reports'
    __table_args__ = (UniqueConstraint('user_id', 'client_id'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey('incidents.id'), index=True)
    client_id: Mapped[str] = mapped_column(String(36))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    payload_hash: Mapped[str] = mapped_column(String(64))


class Corroboration(Base):
    __tablename__ = 'corroborations'
    __table_args__ = (UniqueConstraint('user_id', 'incident_id', 'version'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    incident_id: Mapped[str] = mapped_column(ForeignKey('incidents.id'), index=True)
    version: Mapped[int] = mapped_column(Integer)
    answer: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Location(Base):
    __tablename__ = 'locations'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), primary_key=True)
    longitude: Mapped[float] = mapped_column(Float)
    latitude: Mapped[float] = mapped_column(Float)
    accuracy: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    route_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class RouteRecord(Base):
    __tablename__ = 'routes'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    transport: Mapped[str] = mapped_column(String(20))
    geometry: Mapped[dict] = mapped_column(JSON)
    path: Mapped[object | None] = mapped_column(JSON().with_variant(Geometry('LINESTRING', srid=4326), 'postgresql'), nullable=True)
    distance_m: Mapped[float] = mapped_column(Float)
    duration_s: Mapped[float] = mapped_column(Float)
    instructions: Mapped[list] = mapped_column(JSON)
    evaluation: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Evaluation(Base):
    __tablename__ = 'evaluations'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    route_id: Mapped[str] = mapped_column(ForeignKey('routes.id'), index=True)
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Photo(Base):
    __tablename__ = 'photos'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    report_id: Mapped[str] = mapped_column(ForeignKey('reports.id'), unique=True)
    blob_name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Alert(Base):
    __tablename__ = 'alerts'
    __table_args__ = (UniqueConstraint('user_id', 'incident_id', 'version', 'kind'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey('incidents.id'))
    version: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(30))
    message: Mapped[str] = mapped_column(String(500))
    priority: Mapped[str] = mapped_column(String(20))
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Device(Base):
    __tablename__ = 'devices'
    token: Mapped[str] = mapped_column(String(200), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)


class Delivery(Base):
    __tablename__ = 'deliveries'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    alert_id: Mapped[str] = mapped_column(ForeignKey('alerts.id'), unique=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default='pending')
    ticket_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Audit(Base):
    __tablename__ = 'audit'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    target: Mapped[str] = mapped_column(String(80))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
