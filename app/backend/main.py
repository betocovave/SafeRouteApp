import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from backend.api.endpoints import router
from backend.api.maps import router as maps_router
from backend.api.realtime import hub
from backend.config import settings
from backend.data.database import SessionLocal
from backend.jobs.worker import run


@asynccontextmanager
async def lifespan(app):
    job = asyncio.create_task(run(hub)) if settings().enable_jobs else None
    yield
    if job:
        job.cancel()
        with suppress(asyncio.CancelledError):
            await job


app = FastAPI(title='SafeRouteAI', version='1.0.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings().cors_origins.split(','), allow_credentials=False, allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'], allow_headers=['Authorization', 'Content-Type'], expose_headers=['X-Package-SHA256', 'X-Package-Bytes'])
app.include_router(router)
app.include_router(maps_router)


@app.middleware('http')
async def response_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.exception_handler(Exception)
async def unexpected(request: Request, exc: Exception):
    logging.getLogger('saferoute').error('Unhandled request failure: %s', type(exc).__name__)
    return JSONResponse(status_code=500, content={'detail': 'No se pudo completar la operación. Inténtalo nuevamente.'})


@app.get('/health')
def health():
    return {'status': 'ok', 'service': 'SafeRouteAI'}


@app.get('/ready')
def ready():
    try:
        with SessionLocal() as db:
            db.execute(text('SELECT 1'))
        return {'database': 'ready'}
    except Exception:
        return JSONResponse(status_code=503, content={'database': 'unavailable'})
