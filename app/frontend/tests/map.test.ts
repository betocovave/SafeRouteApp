import test from 'node:test';
import assert from 'node:assert/strict';
import { Script } from 'node:vm';
import { mapHTML } from '../src/maps/html';

for (const dark of [false, true]) {
  test(`offline map has self-contained scripts and valid JS (${dark ? 'dark' : 'light'})`, () => {
    const html = mapHTML(true, dark);
    assert.ok(!html.includes('<script src='));
    for (const match of html.matchAll(/<script>([\s\S]*?)<\/script>/g)) new Script(match[1]);
    assert.ok(html.includes('OpenStreetMap contributors'));
  });
}
test('online map proxies map resources and never includes an Azure credential', () => {
  const html = mapHTML(false, false);
  assert.ok(html.includes('/api/v1/maps/proxy'));
  assert.ok(!html.includes('subscriptionKey:'));
  for (const match of html.matchAll(/<script>([\s\S]*?)<\/script>/g)) new Script(match[1]);
});
