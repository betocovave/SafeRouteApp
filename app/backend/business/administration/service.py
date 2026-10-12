from backend.data.models import Audit


def audit(db, actor, action, target, details=None):
    db.add(Audit(actor_id=actor.id, action=action, target=target, details=details or {}))
