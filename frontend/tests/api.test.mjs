// Run with:  npm test      (uses Node's built-in test runner, no extra packages)
import assert from 'node:assert/strict';
import { beforeEach, test } from 'node:test';
import { ApiError, api, clearToken, configureApi, describeError, getToken, setToken, setUnauthorizedHandler } from '../src/lib/api.js';

let calls;
const reply = (status, body) => ({ ok: status < 400, status, text: async () => (body === undefined ? '' : JSON.stringify(body)) });
const mockFetch = (fn) => { globalThis.fetch = async (url, init) => { calls.push({ url, init }); return fn(url, init); }; };

beforeEach(() => { calls = []; clearToken(); setUnauthorizedHandler(null); configureApi({ baseUrl: 'http://api.test/api/' }); });

test('GET sends the bearer token and uses the configured base URL', async () => {
  setToken('abc');
  mockFetch(() => reply(200, { ok: true }));
  assert.deepEqual(await api.get('/workspace'), { ok: true });
  assert.equal(calls[0].url, 'http://api.test/api/workspace');
  assert.equal(calls[0].init.headers.Authorization, 'Bearer abc');
});

test('no token means no Authorization header', async () => {
  mockFetch(() => reply(200, {}));
  await api.get('/health');
  assert.equal(calls[0].init.headers.Authorization, undefined);
});

test('POST sends JSON', async () => {
  mockFetch(() => reply(201, { id: 'CC-2026-0001' }));
  await api.post('/complaints', { title: 'x' });
  assert.equal(calls[0].init.headers['Content-Type'], 'application/json');
  assert.equal(calls[0].init.body, '{"title":"x"}');
});

test('server errors become ApiError with message, code and field details', async () => {
  mockFetch(() => reply(400, { error: { code: 'validation_failed', message: 'Please fix the highlighted fields.', details: { title: 'Title is required.' } } }));
  await assert.rejects(api.post('/complaints', {}), (e) => {
    assert.ok(e instanceof ApiError);
    assert.equal(e.status, 400);
    assert.equal(e.code, 'validation_failed');
    assert.equal(describeError(e), 'Title is required.');
    return true;
  });
});

test('network failure gives a friendly message, not a raw error', async () => {
  mockFetch(() => { throw new TypeError('Failed to fetch'); });
  await assert.rejects(api.get('/workspace'), (e) => e.code === 'network_error' && /Cannot reach/.test(e.message));
});

test('a 401 on a normal call clears the token and tells the app to sign out', async () => {
  setToken('old');
  let signedOut = 0;
  setUnauthorizedHandler(() => { signedOut += 1; });
  mockFetch(() => reply(401, { error: { code: 'unauthenticated', message: 'Sign in to continue.' } }));
  await assert.rejects(api.get('/workspace'));
  assert.equal(getToken(), null);
  assert.equal(signedOut, 1);
});

test('a failed login (401) does not trigger the signed-out handler', async () => {
  setToken('keep');
  let signedOut = 0;
  setUnauthorizedHandler(() => { signedOut += 1; });
  mockFetch(() => reply(401, { error: { code: 'unauthenticated', message: 'Email or password is incorrect.' } }));
  await assert.rejects(api.post('/auth/login', { email: 'a', password: 'b' }), /incorrect/);
  assert.equal(signedOut, 0);
});

test('upload sends the file as the body with its type and name', async () => {
  setToken('t');
  mockFetch(() => reply(201, { id: 1 }));
  const file = new Blob(['hello'], { type: 'image/png' });
  file.name = 'leak photo.png';
  await api.upload('/complaints/CC-2026-0001/attachments', file);
  assert.equal(calls[0].url, 'http://api.test/api/complaints/CC-2026-0001/attachments?name=leak%20photo.png');
  assert.equal(calls[0].init.body, file);
  assert.equal(calls[0].init.headers['Content-Type'], 'image/png');
  assert.equal(calls[0].init.headers.Authorization, 'Bearer t');
});

test('an empty 200 body and a non-JSON error body are handled', async () => {
  mockFetch(() => reply(200));
  assert.equal(await api.get('/x'), null);
  mockFetch(() => ({ ok: false, status: 502, text: async () => '<html>Bad gateway</html>' }));
  await assert.rejects(api.get('/x'), (e) => e.status === 502 && /error \(502\)/.test(e.message));
});
