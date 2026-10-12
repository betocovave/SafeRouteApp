import test from 'node:test';
import assert from 'node:assert/strict';
import { flushReports } from '../src/storage/queueCore';
import { progress } from '../src/geolocation/navigation';
import type { PendingReport, Route } from '../src/api/types';

test('a failed photo preserves its server report id and retries without duplicating the report', async () => {
  let calls = 0;
  const item = { client_id: 'id', local_photo: 'photo.jpg' } as PendingReport;
  let state: PendingReport[] = [];
  const send = async () => { calls++; return { report_id: 'server-id' } as never; };
  const first = await flushReports([item], send, async () => { throw new Error('offline'); }, async value => { state = JSON.parse(JSON.stringify(value)); });
  assert.equal(first.length, 1); assert.equal(state[0].report_id, 'server-id');
  const second = await flushReports(state, send, async () => {}, async () => {});
  assert.equal(calls, 1); assert.equal(second.length, 0);
});

test('navigation retains forward progress and detects arrival', () => {
  const route = { geometry: { coordinates: [[-101.2, 20.57], [-101.199, 20.57], [-101.198, 20.57]] }, instructions: [], duration_s: 90 } as unknown as Route;
  const middle = progress(route, { longitude: -101.199, latitude: 20.57 });
  const end = progress(route, { longitude: -101.198, latitude: 20.57 }, middle.nearestIndex);
  assert.ok(end.arrived); assert.equal(end.remaining_m, 0);
  assert.ok(progress(route, { longitude: -101.2, latitude: 20.58 }, middle.nearestIndex).offRoute);
});
