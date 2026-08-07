import { useCallback, useEffect, useRef, useState } from 'react';

/** Thin wrapper around window.speechSynthesis. Speaks short, explicit text
 * only when asked to -- callers decide what/when, this hook never reads
 * anything automatically. */
export function useSpeechSynthesis() {
  const [speaking, setSpeaking] = useState(false);
  const [error, setError] = useState(null);
  const supported = typeof window !== 'undefined' && 'speechSynthesis' in window;
  const mountedRef = useRef(true);

  const speak = useCallback(
    (text, { onEnd } = {}) => {
      if (!supported) {
        setError('Text-to-speech is not supported in this browser.');
        onEnd?.();
        return;
      }
      if (!text || !text.trim()) {
        onEnd?.();
        return;
      }
      try {
        window.speechSynthesis.cancel(); // never overlap utterances
        const utterance = new window.SpeechSynthesisUtterance(text);
        utterance.onstart = () => {
          if (!mountedRef.current) return;
          setError(null);
          setSpeaking(true);
        };
        utterance.onend = () => {
          if (mountedRef.current) setSpeaking(false);
          onEnd?.();
        };
        utterance.onerror = () => {
          if (mountedRef.current) {
            setSpeaking(false);
            setError('Speech playback failed.');
          }
          onEnd?.();
        };
        window.speechSynthesis.speak(utterance);
      } catch {
        setSpeaking(false);
        setError('Speech playback failed.');
        onEnd?.();
      }
    },
    [supported],
  );

  const cancel = useCallback(() => {
    if (supported) window.speechSynthesis.cancel();
    setSpeaking(false);
  }, [supported]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (supported) window.speechSynthesis.cancel();
    };
  }, [supported]);

  return { supported, speaking, error, speak, cancel };
}
