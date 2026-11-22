// Speech-to-text with Azure AI Speech. This file holds the logic; components/complaints/VoiceInput.jsx holds the buttons.
//
// How it stays secure: the browser never sees the Speech key. It asks OUR backend for a short-lived token
// (GET /speech/token), gives that token to the Azure Speech SDK, and the SDK streams the microphone to Azure.
// Nothing is recorded or stored by us.
//
// Everything the logic needs is passed in (getToken, loadSdk, getUserMedia), so it can be tested without a microphone.

export const SPEECH_LANGUAGES = [
  { code: 'en-IN', label: 'English (India)' },
  { code: 'hi-IN', label: 'Hindi' },
];
export const MAX_LISTEN_MS = 60000; // stops by itself after one minute

export function explainMicError(err) {
  const name = err?.name;
  if (name === 'NotAllowedError' || name === 'PermissionDeniedError' || name === 'SecurityError') {
    return 'Microphone access is blocked. Allow the microphone for this site (lock icon near the address bar), or type your complaint instead.';
  }
  if (name === 'NotFoundError' || name === 'OverconstrainedError') return 'No microphone was found on this device. You can type your complaint instead.';
  if (name === 'NotReadableError' || name === 'AbortError') return 'The microphone is being used by another app. Close it and try again, or type your complaint.';
  return 'The microphone could not be started. You can type your complaint instead.';
}

export function explainTokenError(err) {
  if (err?.details?.reason === 'speech_disabled') return { message: 'Voice input is not switched on for this server. You can type your complaint instead.', permanent: true };
  if (err?.code === 'network_error') return { message: 'Cannot reach the server for voice input. Check your connection, or type your complaint.', permanent: false };
  if (err?.status === 401) return { message: 'Please sign in again to use voice input.', permanent: false };
  return { message: err?.message || 'Voice input is not available right now. You can type your complaint instead.', permanent: false };
}

// Azure Speech cancellation error codes (CancellationErrorCode): 1 auth, 3 too many requests, 4 forbidden, 5 connection, 6 timeout, 7+ service.
export function explainCancel(errorCode) {
  if (errorCode === 1 || errorCode === 4) return 'Voice input was not accepted by Azure (the access token may have expired). Try again, or type your complaint.';
  if (errorCode === 3) return 'Voice input is busy right now. Wait a moment and try again, or type your complaint.';
  if (errorCode === 5 || errorCode === 6) return 'The connection to the speech service was lost. Check your internet and try again, or type your complaint.';
  return 'Speech recognition failed. Please try again, or type your complaint.';
}

// Starts listening. Returns { stop() } or null if it could not start (onError already told the user why).
export async function startVoice({ getToken, loadSdk, getUserMedia, language, onInterim, onFinal, onError, onStop }) {
  // 1. Ask for the microphone first, so a refused permission gives a clear message. Close it right away.
  if (!getUserMedia) {
    onError('Voice input needs a secure page (https or localhost) and a browser with microphone support. You can type instead.');
    return null;
  }
  try {
    const probe = await getUserMedia({ audio: true });
    probe.getTracks().forEach((t) => t.stop());
  } catch (err) {
    onError(explainMicError(err));
    return null;
  }

  // 2. Short-lived token from our backend (the key stays on the server).
  let session;
  try {
    session = await getToken();
  } catch (err) {
    const { message, permanent } = explainTokenError(err);
    onError(message, { permanent });
    return null;
  }

  // 3. Azure Speech SDK (loaded only now, so the app starts fast).
  let sdk;
  try {
    sdk = await loadSdk();
  } catch {
    onError('Voice input could not be loaded. You can type your complaint instead.');
    return null;
  }

  let recognizer;
  let finished = false;
  let heard = false;
  let timer = null;

  const finish = () => {
    if (finished) return;
    finished = true;
    clearTimeout(timer);
    try { recognizer?.close(); } catch { /* already closed */ }
    onInterim('');
    onStop({ heardSpeech: heard });
  };
  const stop = () => {
    if (finished) return;
    if (!recognizer) return finish();
    recognizer.stopContinuousRecognitionAsync(finish, finish);
  };

  try {
    const config = sdk.SpeechConfig.fromAuthorizationToken(session.token, session.region);
    config.speechRecognitionLanguage = language;
    recognizer = new sdk.SpeechRecognizer(config, sdk.AudioConfig.fromDefaultMicrophoneInput());
    recognizer.recognizing = (_s, e) => onInterim(e.result.text || '');
    recognizer.recognized = (_s, e) => {
      if (e.result.reason === sdk.ResultReason.RecognizedSpeech && e.result.text) {
        heard = true;
        onInterim('');
        onFinal(e.result.text);
      }
    };
    recognizer.canceled = (_s, e) => {
      if (e.reason === sdk.CancellationReason.Error) onError(explainCancel(e.errorCode));
      stop();
    };
    recognizer.sessionStopped = () => finish();
    recognizer.startContinuousRecognitionAsync(
      () => { timer = setTimeout(stop, MAX_LISTEN_MS); },
      () => { onError('Voice input could not start. Please try again, or type your complaint.'); finish(); },
    );
  } catch {
    onError('Voice input could not start. Please try again, or type your complaint.');
    finish();
    return null;
  }
  return { stop };
}
