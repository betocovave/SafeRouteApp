import asyncio
import logging
import json
from datetime import timedelta
import httpx
from sqlalchemy import select, delete
from backend.config import settings
from backend.data.database import SessionLocal
from backend.data.models import Alert, Delivery, Device, Location, now
from backend.business.incidents.service import expire

log = logging.getLogger('saferoute.jobs')


async def deliver(db):
    pending = list(db.scalars(select(Delivery).where(Delivery.status == 'pending', Delivery.retry_at <= now()).limit(50)))
    headers = {'Authorization': 'Bearer ' + settings().expo_access_token} if settings().expo_access_token else {}
    async with httpx.AsyncClient(timeout=5) as client:
        for task in pending:
            alert = db.get(Alert, task.alert_id)
            devices = list(db.scalars(select(Device).where(Device.user_id == alert.user_id)))
            if not devices:
                task.status = 'no_device'
                continue
            task.attempts += 1
            try:
                response = await client.post('https://exp.host/--/api/v2/push/send', headers=headers, json=[{'to': d.token, 'title': 'SafeRouteAI', 'body': alert.message, 'data': {'incident_id': alert.incident_id}, 'sound': 'default'} for d in devices])
                response.raise_for_status()
                results = response.json().get('data', [])
                if len(results) != len(devices):
                    raise ValueError('invalid receipt')
                for device, result in zip(devices, results):
                    if result.get('details', {}).get('error') == 'DeviceNotRegistered':
                        db.delete(device)
                if any(r.get('status') != 'ok' for r in results):
                    raise ValueError('push rejected')
                task.ticket_id = json.dumps([{'id': r['id'], 'token': d.token} for r, d in zip(results, devices)])
                task.status = 'accepted'
                task.retry_at = now() + timedelta(seconds=60)
            except (httpx.HTTPError, ValueError, KeyError):
                task.status = 'failed' if task.attempts >= 5 else 'pending'
                task.retry_at = now() + timedelta(seconds=min(300, 2**task.attempts * 10))
        db.commit()

        # Un ticket aceptado no prueba entrega: consultar recibos del proveedor.
        accepted = list(db.scalars(select(Delivery).where(Delivery.status == 'accepted', Delivery.retry_at <= now()).limit(50)))
        for task in accepted:
            tickets = json.loads(task.ticket_id or '[]')
            try:
                response = await client.post('https://exp.host/--/api/v2/push/getReceipts', headers=headers, json={'ids': [t['id'] for t in tickets]})
                response.raise_for_status()
                receipts = response.json().get('data', {})
                if any(t['id'] not in receipts for t in tickets):
                    raise ValueError('receipts pending')
                for ticket in tickets:
                    receipt = receipts[ticket['id']]
                    if receipt.get('details', {}).get('error') == 'DeviceNotRegistered':
                        device = db.get(Device, ticket['token'])
                        if device:
                            db.delete(device)
                task.status = 'provider_delivered' if all(receipts[t['id']].get('status') == 'ok' for t in tickets) else 'failed'
            except (httpx.HTTPError, ValueError, KeyError):
                task.attempts += 1
                task.status = 'failed' if task.attempts >= 15 else 'accepted'
                task.retry_at = now() + timedelta(seconds=60)
        db.commit()


async def run(hub):
    while True:
        try:
            with SessionLocal() as db:
                changed = expire(db)
                db.execute(delete(Location).where(Location.updated_at < now()-timedelta(minutes=settings().location_retention_minutes)))
                db.commit()
                if changed:
                    await hub.broadcast({'type': 'incidents_changed'})
                await deliver(db)
        except Exception:
            log.error('Background job failed; retrying', exc_info=False)
        await asyncio.sleep(15)
