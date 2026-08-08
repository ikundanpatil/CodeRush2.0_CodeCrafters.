import React from 'react';

export const ASSISTANT_STATE_LABELS = {
  idle: "Ready to listen",
  listening: "Listening...",
  processing: "Processing...",
  researching: "Researching...",
  analyzing: "Analyzing evidence...",
  verifying: "Verifying answer...",
  speaking: "Speaking...",
  completed: "Research complete",
  cancelled: "Research cancelled",
  error: "Something went wrong",
};

/** Visible status text + an aria-live region so screen-reader users get the
 * same information sighted users get from AssistantCore's animation --
 * state must never be conveyed by color/motion alone. */
const VoiceStatus = ({ state = 'idle', detail = '', className = '' }) => {
  const label = ASSISTANT_STATE_LABELS[state] || ASSISTANT_STATE_LABELS.idle;

  return (
    <div className={`text-center ${className}`}>
      <p className="text-sm font-semibold text-slate-900 tracking-wide uppercase">{label}</p>
      {detail && <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">{detail}</p>}
      <span className="sr-only" role="status" aria-live="polite">
        {label}
        {detail ? `. ${detail}` : ''}
      </span>
    </div>
  );
};

export default VoiceStatus;
