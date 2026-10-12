from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Point(Strict):
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)


class Login(Strict):
    email: str = Field(min_length=5, max_length=254, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    password: str = Field(min_length=10, max_length=128)

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value):
        return value.lower()


class Registration(Login):
    name: str = Field(min_length=2, max_length=80)


class Recovery(Login):
    recovery_code: str = Field(min_length=20, max_length=100)


class Refresh(Strict):
    refresh_token: str = Field(min_length=20, max_length=200)


class Tokens(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int = 900
    recovery_code: str | None = None


class Profile(Strict):
    name: str = Field(min_length=2, max_length=80)


class Preferences(Strict):
    transport: Literal['driving', 'walking'] = 'driving'
    risk_tolerance: Literal['low', 'medium', 'high'] = 'low'
    alerts: bool = True
    quiet_start: int | None = Field(default=None, ge=0, le=23)
    quiet_end: int | None = Field(default=None, ge=0, le=23)
    theme: Literal['system', 'light', 'dark'] = 'system'


class LocationInput(Point):
    accuracy: float = Field(ge=0, le=10000)
    route_id: UUID | None = None


class IncidentInput(Point):
    category_id: str = Field(min_length=1, max_length=40)
    description: str = Field(min_length=5, max_length=1000)
    client_id: UUID
    occurred_at: datetime

    @field_validator('occurred_at')
    @classmethod
    def require_timezone(cls, value):
        if value.tzinfo is None:
            raise ValueError('La fecha debe incluir zona horaria.')
        return value


class CorroborationInput(Strict):
    answer: Literal['present', 'ended', 'unknown']
    version: int = Field(ge=1)


class RouteInput(Strict):
    origin: Point
    destination: Point
    transport: Literal['driving', 'walking']


class Instruction(BaseModel):
    text: str
    coordinates: list[float]
    distance_m: float = 0
    duration_s: float = 0


class Factor(BaseModel):
    incident_id: str
    category: str
    distance_m: float
    contribution: float
    confidence: float
    critical: bool


class RiskEvaluation(BaseModel):
    risk_index: float | None
    safety_index: float | None
    label: str
    critical: bool
    factors: list[Factor]
    calculated_at: str
    rules_version: str
    observed_incidents: int


class LineGeometry(BaseModel):
    type: Literal['LineString'] = 'LineString'
    coordinates: list[list[float]]


class RouteOutput(BaseModel):
    id: str
    transport: str
    geometry: LineGeometry
    distance_m: float
    duration_s: float
    instructions: list[Instruction]
    evaluation: RiskEvaluation


class RouteResults(BaseModel):
    routes: list[RouteOutput]
    recommended_id: str | None
    warning: str | None


class DeviceInput(Strict):
    token: str = Field(max_length=200, pattern=r'^(ExponentPushToken|ExpoPushToken)\[[A-Za-z0-9_-]+\]$')


class AdminUser(Strict):
    active: bool


class AdminIncident(Strict):
    status: Literal['confirmed', 'resolved', 'hidden']
    reason: str = Field(min_length=5, max_length=300)


class CategoryInput(Strict):
    name: str = Field(min_length=2, max_length=80)
    group: Literal['acute', 'road', 'lighting']
    severity: float = Field(ge=0, le=1)
    ttl_hours: int = Field(ge=1, le=720)
    critical: bool
    active: bool


class UserOutput(BaseModel):
    id: str
    name: str
    email: str
    role: str
    preferences: Preferences
    created_at: datetime


class CategoryOutput(CategoryInput):
    id: str


class IncidentOutput(Point):
    id: str
    category_id: str
    category: str
    description: str
    status: str
    confidence: float
    critical: bool
    occurred_at: str
    expires_at: str
    updated_at: str
    version: int
    photo_id: str | None


class ReportOutput(BaseModel):
    report_id: str
    incident: IncidentOutput


class AlertOutput(BaseModel):
    id: str
    incident_id: str
    kind: str
    message: str
    priority: str
    read: bool
    created_at: str


class HistoryOutput(BaseModel):
    routes: list[RouteOutput]
    reports: list[ReportOutput]
