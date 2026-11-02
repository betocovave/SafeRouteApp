import type { Point } from '../api/types';

// Planning origin only. Never submit this point as a measured GPS position.
export const DEFAULT_ORIGIN: Point = { longitude: -101.195, latitude: 20.57 };

// shortcut: copia BOUNDS de backend/external_services/geolocation/service.py; si la cobertura cambia, actualizar ambos.
export const inCoverage = (p: Point) => p.longitude >= -101.30 && p.longitude <= -101.08 && p.latitude >= 20.48 && p.latitude <= 20.68;
