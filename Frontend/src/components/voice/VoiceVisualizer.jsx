import React from 'react';

const BAR_COUNT = 5;

/** Small bar-waveform, reused by AssistantCore (LISTENING/SPEAKING) and
 * standalone inside VoiceInput. Purely decorative (aria-hidden) -- the
 * actual state is always announced separately via VoiceStatus's live
 * region, never conveyed by animation/color alone. */
const VoiceVisualizer = ({ active = false, variant = 'listening', className = '' }) => {
  const barColor = variant === 'speaking' ? 'bg-emerald-400' : 'bg-cyan-400';

  return (
    <div className={`flex items-end justify-center gap-1 h-5 ${className}`} aria-hidden="true">
      {Array.from({ length: BAR_COUNT }).map((_, i) => (
        <span
          key={i}
          className={`w-1 rounded-full ${barColor} ${active ? 'animate-voice-bar' : ''}`}
          style={{
            height: active ? undefined : '4px',
            animationDelay: `${i * 0.11}s`,
            opacity: active ? 1 : 0.35,
          }}
        />
      ))}
    </div>
  );
};

export default VoiceVisualizer;
