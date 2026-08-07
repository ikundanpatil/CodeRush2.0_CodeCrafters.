import { useCallback, useEffect, useRef, useState } from 'react';

export const VOICE_STATES = {
  IDLE: 'idle',
  LISTENING: 'listening',
  ERROR: 'error',
};

/**
 * Thin wrapper around the browser's SpeechRecognition API. Only owns
 * mic-level concerns (support detection, permission errors, start/stop,
 * transcript). Never starts listening on its own -- the caller must invoke
 * startListening() from an explicit user action (click/keypress).
 */
export function useVoiceRecognition({ onResult, lang = 'en-US' } = {}) {
  const [state, setState] = useState(VOICE_STATES.IDLE);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [error, setError] = useState(null);
  const recognitionRef = useRef(null);
  const onResultRef = useRef(onResult);
  onResultRef.current = onResult;

  const RecognitionImpl =
    typeof window !== 'undefined' ? window.SpeechRecognition || window.webkitSpeechRecognition : undefined;
  const supported = Boolean(RecognitionImpl);

  const startListening = useCallback(() => {
    if (!supported) {
      setError('Your browser does not support speech recognition. Try Chrome or Edge.');
      setState(VOICE_STATES.ERROR);
      return;
    }
    if (state === VOICE_STATES.LISTENING) return;

    try {
      const recognition = new RecognitionImpl();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = lang;

      recognition.onstart = () => {
        setError(null);
        setInterimTranscript('');
        setState(VOICE_STATES.LISTENING);
      };

      recognition.onresult = (event) => {
        let interim = '';
        let final = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const chunk = event.results[i];
          if (chunk.isFinal) final += chunk[0].transcript;
          else interim += chunk[0].transcript;
        }
        if (interim) setInterimTranscript(interim);
        if (final) {
          setTranscript(final);
          setInterimTranscript('');
          onResultRef.current?.(final.trim());
        }
      };

      recognition.onerror = (event) => {
        const code = event?.error;
        const message =
          code === 'not-allowed' || code === 'permission-denied'
            ? 'Microphone permission is required.'
            : code === 'no-speech'
              ? "I didn't hear anything -- try again."
              : code === 'audio-capture'
                ? 'No microphone was found.'
                : 'Speech recognition failed.';
        setError(message);
        setState(VOICE_STATES.ERROR);
      };

      recognition.onend = () => {
        setState((current) => (current === VOICE_STATES.LISTENING ? VOICE_STATES.IDLE : current));
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch {
      setError('Could not start speech recognition.');
      setState(VOICE_STATES.ERROR);
    }
  }, [RecognitionImpl, lang, state, supported]);

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop();
  }, []);

  const reset = useCallback(() => {
    setState(VOICE_STATES.IDLE);
    setError(null);
    setTranscript('');
    setInterimTranscript('');
  }, []);

  useEffect(() => {
    return () => {
      recognitionRef.current?.abort?.();
    };
  }, []);

  return { supported, state, transcript, interimTranscript, error, startListening, stopListening, reset };
}
