import React from 'react';
import { Activity, Search, Globe, ShieldCheck, GitBranch, AlertTriangle, ShieldAlert } from 'lucide-react';

const iconForEventType = (type = '') => {
  if (type.includes('search')) return Search;
  if (type.includes('browser') || type.includes('browse')) return Globe;
  if (type.includes('policy')) return ShieldCheck;
  if (type.includes('gap')) return AlertTriangle;
  if (type.includes('security') || type.includes('injection')) return ShieldAlert;
  if (type.includes('evidence') || type.includes('claim') || type.includes('graph')) return GitBranch;
  return Activity;
};

const formatTime = (timestamp) => {
  try {
    return new Date(timestamp).toLocaleTimeString();
  } catch {
    return '';
  }
};

/** Renders REAL backend AgentEvents (GET /api/research/{id}/trace) --
 * never a fabricated activity list. Newest first. */
const ResearchActivityPanel = ({ trace }) => {
  return (
    <div className="w-full bg-[#1E293B]/90 border border-slate-700/80 rounded-[14px] p-5 shadow-xl flex flex-col gap-3">
      <div className="flex items-center gap-2 pb-3 border-b border-slate-700/60">
        <Activity className="w-4 h-4 text-cyan-400" aria-hidden="true" />
        <h4 className="text-sm font-bold text-slate-100">Research Activity</h4>
      </div>

      {trace === null || trace === undefined ? (
        <p className="text-xs text-slate-500">Waiting for data...</p>
      ) : trace.length === 0 ? (
        <p className="text-xs text-slate-500">No activity yet.</p>
      ) : (
        <ul className="space-y-2 max-h-72 overflow-y-auto pr-1">
          {[...trace].reverse().map((event) => {
            const Icon = iconForEventType(event.type);
            return (
              <li key={event.event_id} className="flex items-start gap-2.5 text-xs">
                <Icon className="w-3.5 h-3.5 text-cyan-400 mt-0.5 flex-shrink-0" aria-hidden="true" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-slate-200 truncate">{event.title}</span>
                    <span className="text-[10px] text-slate-500 font-mono flex-shrink-0">
                      {formatTime(event.timestamp)}
                    </span>
                  </div>
                  <p className="text-slate-400 leading-snug">{event.message}</p>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
};

export default ResearchActivityPanel;
