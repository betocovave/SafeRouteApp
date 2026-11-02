import test from 'node:test';
import assert from 'node:assert/strict';
import { inCoverage } from '../src/geolocation/defaultOrigin';

test('Salamanca is covered; a GPS fix in Querétaro is not', () => {
  assert.equal(inCoverage({ longitude: -101.195, latitude: 20.57 }), true);
  assert.equal(inCoverage({ longitude: -100.39, latitude: 20.59 }), false);
});
