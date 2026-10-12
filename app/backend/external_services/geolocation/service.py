from math import cos, radians, sin, atan2, sqrt
from fastapi import HTTPException

# Limite inicial operativo de Salamanca; ampliable por configuracion de ciudad.
BOUNDS = (-101.30, 20.48, -101.08, 20.68)


def within_city(lon, lat):
    return BOUNDS[0] <= lon <= BOUNDS[2] and BOUNDS[1] <= lat <= BOUNDS[3]


def require_city(lon, lat):
    if not within_city(lon, lat):
        raise HTTPException(422, 'La cobertura inicial está limitada a Salamanca, Guanajuato.')


def distance(a, b):
    lon1, lat1, lon2, lat2 = map(radians, [*a, *b])
    d = sin((lat2-lat1)/2)**2 + cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2
    return 6371000 * 2 * atan2(sqrt(d), sqrt(max(0, 1-d)))
