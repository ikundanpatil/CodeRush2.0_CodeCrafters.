import React from 'react';
import { ShieldCheck, ShieldAlert, AlertTriangle } from 'lucide-react';
import Badge from '../Badge';

/** Renders the REAL final-answer VerificationResult from
 * GET /api/research/{id}/result (`verification`). Distinct from the Phase 5
 * quality panel: this is the post-generation check of the answer text
 * itself. Never fabricates a score or a verdict. */
const VerificationPanel = ({ verification }) => {
  const hasData = verification && Object.keys(verification).length > 0;

  return (
    <div className="w-full bg-[#1E293B]/90 border border-slate-700/80 rounded-[14px] p-5 shadow-xl flex flex-col gap-3">
      <div className="flex items-center justify-between pb-3 border-b border-slate-700/60">
        <div className="flex items-center gap-2">
          {hasData && verification.valid ? (
            <ShieldCheck className="w-4 h-4 text-emerald-400" aria-hidden="true" />
          ) : (
            <ShieldAlert className="w-4 h-4 text-cyan-400" aria-hidden="true" />
          )}
          <h4 className="text-sm font-bold text-slate-100">Answer Verification</h4>
        </div>
        {hasData && (
          <Badge variant={verification.valid ? 'success' : 'warning'}>
            {verification.valid ? 'VERIFIED' : 'ISSUES FOUND'}
          </Badge>
        )}
      </div>

      {!hasData ? (
        <p className="text-xs text-slate-500">Waiting for data...</p>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div className="p-2 rounded-xl bg-slate-900/60 border border-slate-800 text-center">
              <span className="text-[10px] text-slate-400 block">Verified</span>
              <span className="font-bold text-emerald-400">{verification.verified_claims?.length ?? 0}</span>
            </div>
            <div className="p-2 rounded-xl bg-slate-900/60 border border-slate-800 text-center">
              <span className="text-[10px] text-slate-400 block">Unsupported</span>
              <span className="font-bold text-amber-400">{verification.unsupported_claims?.length ?? 0}</span>
            </div>
            <div className="p-2 rounded-xl bg-slate-900/60 border border-slate-800 text-center">
              <span className="text-[10px] text-slate-400 block">Contradicted</span>
              <span className="font-bold text-red-400">{verification.contradicted_claims?.length ?? 0}</span>
            </div>
          </div>

          <div className="text-[11px] text-slate-400">
            Verification score:{' '}
            <span className="font-semibold text-slate-200">
              {typeof verification.score === 'number' ? `${Math.round(verification.score * 100)}%` : 'Calculating...'}
            </span>
          </div>

          {verification.unsupported_claims?.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-amber-400 mb-1">
                Unsupported claims (flagged, not hidden)
              </p>
              <ul className="space-y-1">
                {verification.unsupported_claims.map((c, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-[11px] text-slate-400">
                    <AlertTriangle className="w-3 h-3 text-amber-400 mt-0.5 flex-shrink-0" aria-hidden="true" />
                    {c.claim_text}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {verification.citation_errors?.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-red-400 mb-1">Citation issues</p>
              <ul className="space-y-1">
                {verification.citation_errors.map((e, i) => (
                  <li key={i} className="text-[11px] text-slate-400 break-all">
                    {e}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default VerificationPanel;
