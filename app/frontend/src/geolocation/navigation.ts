import type { Point, Route } from '../api/types';
export function meters(a: number[], b: number[]) {
  const rad = Math.PI / 180;
  const h = Math.sin((b[1]-a[1])*rad/2)**2 + Math.cos(a[1]*rad)*Math.cos(b[1]*rad)*Math.sin((b[0]-a[0])*rad/2)**2;
  return 12742000*Math.asin(Math.min(1, Math.sqrt(h)));
}
export function progress(route: Route, point: Point, previousIndex = 0) {
  const coords = route.geometry.coordinates;
  let nearest = previousIndex;
  let nearestDistance = Infinity;
  for (let i = previousIndex; i < coords.length; i++) {
    const value = meters(coords[i], [point.longitude, point.latitude]);
    if (value < nearestDistance) { nearest = i; nearestDistance = value; }
  }
  let remaining = 0, total = 0;
  for (let i = 1; i < coords.length; i++) { const length = meters(coords[i-1], coords[i]); total += length; if (i > nearest) remaining += length; }
  const instruction = route.instructions.find(step => {
    let target = 0, closest = Infinity;
    coords.forEach((coord, index) => { const d = meters(coord, step.coordinates); if (d < closest) { closest = d; target = index; } });
    return target > nearest;
  });
  return { nearestIndex: nearest, offRoute: nearestDistance > 70, remaining_m: remaining, remaining_s: route.duration_s * (total ? remaining/total : 0), instruction: instruction?.text || 'Continúa hacia el destino', arrived: nearest === coords.length-1 && nearestDistance < 30 };
}
