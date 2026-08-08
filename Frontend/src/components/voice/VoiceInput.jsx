import React, { useEffect } from 'react';
import { Mic, AlertCircle } from 'lucide-react';
import { useVoiceRecognition, VOICE_STATES } from '../../hooks/useVoiceRecognition';
import VoiceVisualizer from './VoiceVisualizer';

/** The mic button. Explicit activation only -- listening never starts on
 * its own, only from a real click or Enter/Space on this button (a native
 * <button>, so keyboard activation is free). */
const VoiceInput = ({ onTranscript, onStateChange, onBeforeListen, disabled = false, className = '' }) => {
  const { supported, state, transcript, interimTranscript, error, startListening, stopListening } =
    useVoiceRecognition({ onResult: onTranscript });

  const listening = state === VOICE_STATES.LISTENING;
  const hasError = state === VOICE_STATES.ERROR;

  useEffect(() => {
    onStateChange?.({ listening, error: hasError ? error : null });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listening, hasError, error]);

  const handleClick = async () => {
    if (disabled) return;
    if (listening) {
      stopListening();
      return;
    }
    // Let the caller speak a greeting (e.g. only on the first activation)
    // BEFORE recognition starts, so the assistant's own voice is never
    // picked up as a spoken command.
    if (onBeforeListen) await onBeforeListen();
    startListening();
  };

  return (
    <div className={`flex flex-col items-center gap-3 ${className}`}>
      <button
        type="button"
        onClick={handleClick}
        disabled={disabled || !supported}
        aria-pressed={listening}
        aria-label={listening ? 'Stop listening' : 'Speak to Evo'}
        title={
          supported
            ? listening
              ? 'Stop listening'
              : 'Speak to Evo'
            : 'Speech recognition is not supported in this browser'
        }
        className={`relative w-16 h-16 rounded-full flex items-center justify-center border transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-2 focus-visible:ring-offset-white disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer ${
          listening
            ? 'bg-sky-50 border-sky-400 shadow-[0_0_20px_-6px_rgba(14,165,233,0.45)]'
            : hasError
              ? 'bg-red-50 border-red-300'
              : 'bg-slate-100 border-slate-200 hover:border-sky-400'
        }`}
      >
        {hasError ? (
          <AlertCircle className="w-6 h-6 text-red-500" aria-hidden="true" />
        ) : (
          <Mic className={`w-6 h-6 ${listening ? 'text-sky-600' : 'text-slate-500'}`} aria-hidden="true" />
        )}
      </button>

      {listening && <VoiceVisualizer active variant="listening" />}

      <div className="min-h-[1.25rem] text-center">
        {hasError && error && (
          <p className="text-xs text-red-600" role="alert">
            {error}
          </p>
        )}
        {!hasError && (interimTranscript || transcript) && (
          <p className="text-xs text-slate-500 italic max-w-xs">&quot;{interimTranscript || transcript}&quot;</p>
        )}
        {!supported && !hasError && (
          <p className="text-xs text-amber-600">Voice input isn&apos;t supported in this browser. Try Chrome or Edge.</p>
        )}
      </div>
    </div>
  );
};

export default VoiceInput;
