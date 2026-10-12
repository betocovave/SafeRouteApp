from backend.data.models import Category

CATEGORIES = [
    ('theft', 'Robo o asalto', 'acute', 0.8, 6, False),
    ('confrontation', 'Enfrentamiento o disparos', 'acute', 1.0, 6, True),
    ('fire', 'Incendio', 'acute', 1.0, 6, True),
    ('accident', 'Accidente', 'acute', 0.65, 6, False),
    ('protest', 'Manifestación', 'acute', 0.4, 6, False),
    ('checkpoint', 'Retén', 'acute', 0.35, 6, False),
    ('operation', 'Operativo', 'acute', 0.4, 6, False),
    ('blocked', 'Bloqueo', 'road', 0.8, 24, False),
    ('flood', 'Inundación', 'road', 0.8, 24, False),
    ('obstacle', 'Obstáculo', 'road', 0.5, 24, False),
    ('damaged', 'Calle dañada', 'road', 0.4, 720, False),
    ('light_good', 'Iluminación adecuada', 'lighting', 0.0, 720, False),
    ('light_poor', 'Iluminación deficiente', 'lighting', 0.5, 720, False),
    ('light_none', 'Sin iluminación', 'lighting', 0.8, 720, False),
]


def seed(db):
    for ident, name, group, severity, ttl, critical in CATEGORIES:
        if not db.get(Category, ident):
            db.add(Category(id=ident, name=name, group=group, severity=severity, ttl_hours=ttl, critical=critical))
    db.commit()
