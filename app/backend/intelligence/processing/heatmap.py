import pandas as pd
from datetime import timedelta
from sqlalchemy import select
from backend.data.models import Incident, Category, now


def heatmap(db):
    rows = db.execute(select(Incident.longitude, Incident.latitude, Category.severity).join(Category, Category.id == Incident.category_id).where(Incident.status != 'hidden', Category.severity > 0, Incident.occurred_at >= now() - timedelta(days=90))).all()
    if not rows:
        return {'type': 'FeatureCollection', 'features': []}
    frame = pd.DataFrame(rows, columns=['longitude', 'latitude', 'severity'])
    frame[['longitude', 'latitude']] = frame[['longitude', 'latitude']].round(3)
    groups = frame.groupby(['longitude', 'latitude'], as_index=False).agg(count=('severity', 'size'), weight=('severity', 'sum'))
    return {'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [float(row.longitude), float(row.latitude)]}, 'properties': {'count': int(row.count), 'weight': float(row.weight)}} for row in groups.itertuples(index=False)]}
