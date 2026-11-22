import { useEffect, useRef, useState } from 'react';
import { Mic, Square } from 'lucide-react';
import { api } from '../../lib/api';
import { SPEECH_LANGUAGES, startVoice } from '../../lib/speech';
import { Button } from '../ui/primitives';

// Microphone button for the complaint form. Recognised sentences are handed to onText(text); the parent adds them to
// the description box, where the student can edit them. Typing always keeps working (this component is optional).
export default function VoiceInput({ onText }) {
  const [state, setState] = useState('idle'); // idle | starting | listening
  const [language, setLanguage] = useState(SPEECH_LANGUAGES[0].code);
  const [interim, setInterim] = useState('');
  const [message, setMessage] = useState('');
  const [unavailable, setUnavailable] = useState(false); // true when the server says voice is switched off
  const controller = useRef(null);

  useEffect(() => () => controller.current?.stop(), []); // stop listening if the student leaves the page

  const start = async () => {
    setMessage('');
    setState('starting');
    const ctl = await startVoice({
      getToken: () => api.get('/speech/token'),
      loadSdk: () => import('microsoft-cognitiveservices-speech-sdk'),
      getUserMedia: navigator.mediaDevices?.getUserMedia?.bind(navigator.mediaDevices),
      language,
      onInterim: setInterim,
      onFinal: onText,
      onError: (text, opts) => { setMessage(text); if (opts?.permanent) setUnavailable(true); },
      onStop: ({ heardSpeech }) => {
        controller.current = null;
        setState('idle');
        if (!heardSpeech) setMessage((m) => m || 'We did not hear any speech. Try again closer to the microphone, or type your complaint.');
      },
    });
    controller.current = ctl;
    setState(ctl ? 'listening' : 'idle');
  };

  const listening = state === 'listening';
  return (
    <div className="mt-2 rounded-lg bg-navy-50/70 p-3">
      <div className="flex flex-wrap items-center gap-2">
        {listening ? (
          <Button type="button" variant="danger" size="sm" icon={Square} onClick={() => controller.current?.stop()}>Stop</Button>
        ) : (
          <Button type="button" variant="secondary" size="sm" icon={Mic} loading={state === 'starting'} disabled={unavailable} onClick={start}>Speak your complaint</Button>
        )}
        <select aria-label="Speech language" value={language} disabled={state !== 'idle'} onChange={(e) => setLanguage(e.target.value)}
          className="rounded-md border border-navy-200 bg-white px-2 py-1.5 text-[13px] text-navy-700">
          {SPEECH_LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
        </select>
        {listening && <span className="flex items-center gap-1.5 text-[13px] font-semibold text-red-600"><span className="h-2 w-2 animate-pulse rounded-full bg-red-500" />Listening, speak now</span>}
      </div>
      {listening && interim && <p className="mt-2 text-[13px] italic text-navy-500" aria-live="polite">{interim}</p>}
      {message && <p className="mt-2 text-[13px] font-medium text-amber-700" role="alert">{message}</p>}
      <p className="mt-2 text-xs text-navy-400">
        {unavailable ? 'Voice input is off. Please type your complaint.' : 'Your voice is sent to Azure for transcription and is not saved. You can edit the text before submitting.'}
      </p>
    </div>
  );
}
