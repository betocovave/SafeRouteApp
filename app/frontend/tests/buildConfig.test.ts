import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import test from 'node:test';

function resolveConfig(url: string, projectId: string) {
  return spawnSync(process.execPath, ['--import', 'tsx', '--eval', "const config = require('./app.config.ts').default; console.log(JSON.stringify(config));"], {
    encoding: 'utf8',
    env: { ...process.env, APP_ENV: 'production', EXPO_PUBLIC_API_URL: url, EXPO_PUBLIC_EAS_PROJECT_ID: projectId },
  });
}
const projectId = '01234567-89ab-4cde-8012-3456789abcde';

test('production build rejects a missing or insecure API URL before bundling', () => {
  for (const url of ['', 'http://api.example.com', 'https://api.example.com/api/v1']) {
    const result = resolveConfig(url, projectId);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /EXPO_PUBLIC_API_URL/);
  }
});

test('production build requires the EAS project and disables cleartext', () => {
  assert.notEqual(resolveConfig('https://api.example.com', '').status, 0);
  const result = resolveConfig('https://api.example.com', projectId);
  assert.equal(result.status, 0, result.stderr);
  const config = JSON.parse(result.stdout);
  assert.equal(config.extra.eas.projectId, projectId);
  assert.notEqual(config.android.usesCleartextTraffic, true);
  const properties = config.plugins.find((plugin: unknown) => Array.isArray(plugin) && plugin[0] === 'expo-build-properties');
  assert.equal(properties[1].android.usesCleartextTraffic, false);
});
