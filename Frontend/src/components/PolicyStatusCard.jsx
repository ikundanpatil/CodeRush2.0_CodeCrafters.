import React, { useEffect, useState } from 'react';
import { ShieldCheck, ShieldAlert, ShieldQuestion } from 'lucide-react';
import { policyAPI } from '../services/api';
import Badge from './Badge';

const decisionBadge = {
  ALLOW: { label: 'ALLOWED', variant: 'success' },
  DENY: { label: 'BLOCKED', variant: 'danger' },
  REQUIRE_REVIEW: { label: 'REVIEW', variant: 'warning' },
};

const PolicyStatusCard = () => {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    policyAPI
      .getStatus()
      .then((data) => {
        if (!cancelled) setStatus(data);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="w-full bg-[#1E293B]/90 border border-slate-700/80 rounded-[14px] p-5 shadow-xl flex flex-col gap-3">
      <div className="flex items-center justify-between pb-3 border-b border-slate-700/60">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-slate-100">Safety / Policy Engine</h4>
            <p className="text-[11px] text-slate-400">Deterministic action guardrails</p>
          </div>
        </div>

        {error ? (
          <Badge variant="neutral">UNAVAILABLE</Badge>
        ) : status ? (
          <Badge variant={status.enabled ? 'success' : 'warning'} glow>
            {status.enabled ? 'ACTIVE' : 'DISABLED'}
          </Badge>
        ) : (
          <Badge variant="neutral">LOADING</Badge>
        )}
      </div>

      {error && (
        <div className="flex items-center gap-2 text-[11px] text-slate-400 py-2">
          <ShieldQuestion className="w-4 h-4 text-slate-500" />
          Policy status unavailable -- backend unreachable.
        </div>
      )}

      {status && (
        <>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
              Recent decisions
            </p>
            {status.recent_decisions.length === 0 ? (
              <p className="text-[11px] text-slate-500">No policy decisions recorded yet.</p>
            ) : (
              <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                {status.recent_decisions.map((d, idx) => {
                  const badge = decisionBadge[d.decision] || { label: d.decision, variant: 'neutral' };
                  return (
                    <div
                      key={idx}
                      className="flex items-center justify-between gap-2 text-xs bg-slate-900/60 border border-slate-800 rounded-lg px-2.5 py-1.5"
                    >
                      <span className="font-mono text-slate-300 truncate">{d.action}</span>
                      <Badge variant={badge.variant} size="sm">
                        {badge.label}
                      </Badge>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="pt-2 border-t border-slate-700/60 flex items-center gap-2 text-[10px] text-slate-500">
            <ShieldAlert className="w-3.5 h-3.5" />
            Max iterations: {status.limits.max_allowed_research_iterations} &middot; Max sources/iteration:{' '}
            {status.limits.max_allowed_sources_per_iteration}
          </div>
        </>
      )}
    </div>
  );
};

export default PolicyStatusCard;
