import test from 'node:test';
import assert from 'node:assert/strict';
import { serverUrl } from '../src/api/serverUrl';

test('LAN detects Metro computer; explicit HTTPS API works across networks', () => {
  assert.equal(serverUrl('', true, '192.168.1.105:8081'), 'http://192.168.1.105:8000');
  assert.equal(serverUrl(' https://api.example.com/ ', true, 'example.exp.direct'), 'https://api.example.com');
});
test('a Metro tunnel must not be mistaken for a backend tunnel', () => {
  assert.throws(() => serverUrl('', true, 'abc.exp.direct:80'), /modo túnel/);
  assert.throws(() => serverUrl('', false), /HTTPS/);
  assert.throws(() => serverUrl('http://api.example.com', false), /HTTPS/);
  assert.equal(serverUrl('https://api.example.com', false), 'https://api.example.com');
});
test('API URL rejects paths, credentials and unsupported protocols', () => {
  for (const value of ['https://example.com/api/v1', 'https://user:password@example.com', 'ftp://example.com']) {
    assert.throws(() => serverUrl(value, true));
  }
});
