import React from 'react';
import { Sparkles, Search, Volume2, CheckCircle2, AlertTriangle, Loader2, ShieldCheck, Ban } from 'lucide-react';
import VoiceVisualizer from './VoiceVisualizer';

const STATE_META = {
  idle: { icon: Sparkles, ring: 'border-slate-700', glow: '', iconColor: 'text-slate-400' },
  listening: {
    icon: Sparkles, ring: 'border-cyan-400',
    glow: 'shadow-[0_0_40px_-8px_rgba(6,182,212,0.55)]', iconColor: 'text-cyan-300',
  },
  processing: {
    icon: Loader2, ring: 'border-blue-400',
    glow: 'shadow-[0_0_35px_-8px_rgba(59,130,246,0.5)]', iconColor: 'text-blue-300',
  },
  researching: {
    icon: Search, ring: 'border-cyan-500',
    glow: 'shadow-[0_0_35px_-8px_rgba(6,182,212,0.5)]', iconColor: 'text-cyan-300',
  },
  analyzing: {
    icon: Search, ring: 'border-blue-400',
    glow: 'shadow-[0_0_35px_-8px_rgba(59,130,246,0.5)]', iconColor: 'text-blue-300',
  },
  verifying: {
    icon: ShieldCheck, ring: 'border-amber-400',
    glow: 'shadow-[0_0_35px_-8px_rgba(251,191,36,0.45)]', iconColor: 'text-amber-300',
  },
  cancelled: {
    icon: Ban, ring: 'border-slate-500', glow: '', iconColor: 'text-slate-400',
  },
  speaking: {
    icon: Volume2, ring: 'border-emerald-400',
    glow: 'shadow-[0_0_35px_-8px_rgba(52,211,153,0.5)]', iconColor: 'text-emerald-300',
  },
  completed: {
    icon: CheckCircle2, ring: 'border-emerald-500',
    glow: 'shadow-[0_0_25px_-8px_rgba(16,185,129,0.4)]', iconColor: 'text-emerald-400',
  },
  error: {
    icon: AlertTriangle, ring: 'border-red-500',
    glow: 'shadow-[0_0_30px_-8px_rgba(239,68,68,0.5)]', iconColor: 'text-red-400',
  },
};

/** The visual centerpiece. Pure CSS/SVG-free (no canvas, no external
 * assets) -- every state is a restrained border/glow/icon/animation
 * combination, never a copy of any third-party visualizer. */
const AssistantCore = ({ state = 'idle', size = 176 }) => {
  const meta = STATE_META[state] || STATE_META.idle;
  const Icon = meta.icon;

  return (
    <div
      className={`relative rounded-full flex items-center justify-center border-2 bg-gradient-to-b from-slate-900 to-slate-950 transition-all duration-500 ${meta.ring} ${meta.glow} ${
        state === 'idle' ? 'animate-pulse-glow' : ''
      } ${state === 'error' ? 'animate-pulse' : ''}`}
      style={{ width: size, height: size }}
      role="img"
      aria-label={`Assistant state: ${state}`}
    >
      {state === 'processing' && (
        <div
          className="absolute inset-1 rounded-full animate-assistant-spin"
          style={{
            background: 'conic-gradient(from 0deg, transparent 0%, rgba(59,130,246,0.55) 15%, transparent 30%)',
          }}
          aria-hidden="true"
        />
      )}

      {state === 'researching' && (
        <div className="absolute inset-0 rounded-full overflow-hidden" aria-hidden="true">
          <div className="absolute left-0 right-0 h-1/3 bg-gradient-to-b from-transparent via-cyan-400/25 to-transparent animate-assistant-scan" />
        </div>
      )}

      <div className="relative z-10 flex flex-col items-center gap-2">
        <Icon
          className={`w-10 h-10 ${meta.iconColor} ${state === 'processing' ? 'animate-spin' : ''}`}
          aria-hidden="true"
        />
        {(state === 'listening' || state === 'speaking') && (
          <VoiceVisualizer active variant={state === 'speaking' ? 'speaking' : 'listening'} />
        )}
      </div>
    </div>
  );
};

export default AssistantCore;
