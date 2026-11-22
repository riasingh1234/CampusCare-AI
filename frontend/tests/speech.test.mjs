// Tests the speech logic with a fake Azure SDK, a fake microphone and a fake token endpoint. No Azure or microphone needed.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ApiError } from '../src/lib/api.js';
import { explainCancel, explainMicError, startVoice } from '../src/lib/speech.js';

// ---- a tiny stand-in for microsoft-cognitiveservices-speech-sdk
function makeSdk({ failStart = false } = {}) {
  const state = { recognizer: null, config: null, closed: false };
  const sdk = {
    ResultReason: { RecognizedSpeech: 3, NoMatch: 0 },
    CancellationReason: { Error: 0 },
    AudioConfig: { fromDefaultMicrophoneInput: () => ({ mic: true }) },
    SpeechConfig: { fromAuthorizationToken: (token, region) => { state.config = { token, region }; return state.config; } },
    SpeechRecognizer: class {
      constructor(config) { state.recognizer = this; this.config = config; }
      startContinuousRecognitionAsync(ok, fail) { failStart ? fail('boom') : ok(); }
      stopContinuousRecognitionAsync(ok) { ok(); }
      close() { state.closed = true; }
    },
  };
  return { sdk, state };
}

function harness(overrides = {}) {
  const { sdk, state } = makeSdk(overrides.sdkOptions);
  const log = { interim: [], final: [], errors: [], stops: [], micStopped: 0 };
  const stream = { getTracks: () => [{ stop: () => { log.micStopped += 1; } }] };
  const args = {
    getToken: async () => ({ token: 'short-lived', region: 'centralindia', expiresIn: 540 }),
    loadSdk: async () => sdk,
    getUserMedia: async () => stream,
    language: 'en-IN',
    onInterim: (t) => log.interim.push(t),
    onFinal: (t) => log.final.push(t),
    onError: (m, o) => log.errors.push({ m, o }),
    onStop: (r) => log.stops.push(r),
    ...overrides,
  };
  return { args, log, state };
}

test('speech is recognised and handed over as text; the token (not a key) configures the SDK', async () => {
  const { args, log, state } = harness();
  const ctl = await startVoice(args);
  assert.ok(ctl);
  assert.equal(state.config.token, 'short-lived');
  assert.equal(state.config.region, 'centralindia');
  assert.equal(state.recognizer.config.speechRecognitionLanguage, 'en-IN');
  state.recognizer.recognizing(null, { result: { text: 'the tap is' } });
  state.recognizer.recognized(null, { result: { reason: 3, text: 'The tap is leaking.' } });
  assert.deepEqual(log.final, ['The tap is leaking.']);
  assert.equal(log.interim[0], 'the tap is');
  ctl.stop();
  assert.deepEqual(log.stops, [{ heardSpeech: true }]);
  assert.equal(state.closed, true);
});

test('the permission probe releases the microphone straight away', async () => {
  const { args, log } = harness();
  await startVoice(args);
  assert.equal(log.micStopped, 1);
});

test('blocked microphone permission gives a clear message and never asks for a token', async () => {
  let tokenAsked = false;
  const { args, log } = harness({
    getUserMedia: async () => { throw Object.assign(new Error('x'), { name: 'NotAllowedError' }); },
    getToken: async () => { tokenAsked = true; return {}; },
  });
  assert.equal(await startVoice(args), null);
  assert.match(log.errors[0].m, /blocked/);
  assert.match(log.errors[0].m, /type your complaint/);
  assert.equal(tokenAsked, false);
});

test('no microphone / unsupported browser', async () => {
  const none = harness({ getUserMedia: undefined });
  assert.equal(await startVoice(none.args), null);
  assert.match(none.log.errors[0].m, /secure page|microphone support/);
  assert.match(explainMicError({ name: 'NotFoundError' }), /No microphone/);
  assert.match(explainMicError({ name: 'NotReadableError' }), /another app/);
  assert.match(explainMicError({ name: 'Weird' }), /could not be started/);
});

test('Azure Speech not configured on the server (SPEECH_ENABLED=false): clear message and voice is marked unavailable', async () => {
  const { args, log } = harness({
    getToken: async () => { throw new ApiError('Voice input is not switched on', { status: 503, code: 'service_unavailable', details: { reason: 'speech_disabled' } }); },
  });
  assert.equal(await startVoice(args), null);
  assert.match(log.errors[0].m, /not switched on/);
  assert.equal(log.errors[0].o.permanent, true);
});

test('server unreachable or token rejected is temporary, not permanent', async () => {
  const net = harness({ getToken: async () => { throw new ApiError('x', { code: 'network_error' }); } });
  await startVoice(net.args);
  assert.equal(net.log.errors[0].o.permanent, false);
  assert.match(net.log.errors[0].m, /Cannot reach/);
  const expired = harness({ getToken: async () => { throw new ApiError('x', { status: 401 }); } });
  await startVoice(expired.args);
  assert.match(expired.log.errors[0].m, /sign in again/);
});

test('the SDK failing to load is handled', async () => {
  const { args, log } = harness({ loadSdk: async () => { throw new Error('chunk failed'); } });
  assert.equal(await startVoice(args), null);
  assert.match(log.errors[0].m, /could not be loaded/);
});

test('Azure cancels with an error (for example expired token): message shown, session ends once', async () => {
  const { args, log, state } = harness();
  await startVoice(args);
  state.recognizer.canceled(null, { reason: 0, errorCode: 1 });
  state.recognizer.sessionStopped();
  assert.match(log.errors[0].m, /not accepted by Azure/);
  assert.equal(log.stops.length, 1);
  assert.deepEqual(log.stops[0], { heardSpeech: false });
});

test('starting recognition can fail', async () => {
  const { args, log } = harness({ sdkOptions: { failStart: true } });
  await startVoice(args);
  assert.match(log.errors[0].m, /could not start/);
  assert.equal(log.stops.length, 1);
});

test('silence is reported as nothing heard; empty or NoMatch results are not added to the text', async () => {
  const { args, log, state } = harness();
  const ctl = await startVoice(args);
  state.recognizer.recognized(null, { result: { reason: 0, text: '' } });
  state.recognizer.recognized(null, { result: { reason: 3, text: '' } });
  ctl.stop();
  assert.deepEqual(log.final, []);
  assert.deepEqual(log.stops, [{ heardSpeech: false }]);
});

test('stopping twice only reports once', async () => {
  const { args, log } = harness();
  const ctl = await startVoice(args);
  ctl.stop(); ctl.stop();
  assert.equal(log.stops.length, 1);
});

test('cancel messages cover auth, rate limit and connection problems', () => {
  assert.match(explainCancel(1), /not accepted/);
  assert.match(explainCancel(3), /busy/);
  assert.match(explainCancel(5), /connection/);
  assert.match(explainCancel(99), /failed/);
});
