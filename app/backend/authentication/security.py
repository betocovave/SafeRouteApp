import hashlib
import secrets
from datetime import timedelta
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from backend.config import settings
from backend.data.database import get_db
from backend.data.models import Session, User, now, utc

hasher = PasswordHasher()
bearer = HTTPBearer(auto_error=False)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def verify(encoded, value):
    try:
        return hasher.verify(encoded, value)
    except (VerificationError, InvalidHashError):
        return False


def issue(db, user, existing=None, recovery_code=None):
    refresh = secrets.token_urlsafe(48)
    session = existing or Session(user_id=user.id)
    session.refresh_hash = digest(refresh)
    session.expires_at = now() + timedelta(days=30)
    db.add(session)
    db.flush()
    token = jwt.encode({'sub': user.id, 'sid': session.id, 'iat': now(), 'exp': now() + timedelta(minutes=15), 'iss': 'saferoute', 'aud': 'saferoute-mobile'}, settings().jwt_secret, algorithm='HS256')
    db.commit()
    return {'access_token': token, 'refresh_token': refresh, 'expires_in': 900, 'recovery_code': recovery_code}


def authenticate(db, token):
    try:
        payload = jwt.decode(token, settings().jwt_secret, algorithms=['HS256'], issuer='saferoute', audience='saferoute-mobile', options={'require': ['exp', 'sub', 'sid', 'iat']})
        user = db.get(User, payload['sub'])
        session = db.get(Session, payload['sid'])
        if not user or not user.active or not session or session.user_id != user.id or session.revoked or utc(session.expires_at) <= now():
            raise ValueError()
        return user, session
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(401, 'Sesión expirada. Inicia sesión nuevamente.')


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db=Depends(get_db)):
    if not credentials:
        raise HTTPException(401, 'Inicia sesión para continuar.')
    return authenticate(db, credentials.credentials)[0]


def admin_user(user=Depends(current_user)):
    if user.role != 'admin':
        raise HTTPException(403, 'Permiso de administrador requerido.')
    return user


def revoke_all(db, user_id):
    for session in db.scalars(select(Session).where(Session.user_id == user_id)):
        session.revoked = True
