import React from 'react';
import { BarChart2, CheckCircle2, XCircle } from 'lucide-react';

const Metric = ({ label, value }) => (
  <div className="p-2 rounded-xl bg-slate-900/60 border border-slate-800 text-center">
    <span className="text-[10px] text-slate-400 block">{label}</span>
    <span className="font-bold text-slate-200">{value === null || value === undefined ? 'Calculating...' : value}</span>
  </div>
);

/** Renders the REAL ResearchQualityResult from GET /api/research/{id}/quality
 * (Phase 5 backend). Every number here is what the backend computed --
 * nothing is invented, and missing data shows "Calculating...", never 0. */
const ResearchQualityPanel = ({ quality, qualityScore }) => {
  return (
    <div className="w-full bg-[#1E293B]/90 border border-slate-700/80 rounded-[14px] p-5 shadow-xl flex flex-col gap-3">
      <div className="flex items-center gap-2 pb-3 border-b border-slate-700/60">
        <BarChart2 className="w-4 h-4 text-cyan-400" aria-hidden="true" />
        <h4 className="text-sm font-bold text-slate-100">Research Quality</h4>
      </div>

      {!quality ? (
        <p className="text-xs text-slate-500">Calculating...</p>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <Metric label="Sources" value={quality.source_count} />
            <Metric label="Evidence" value={quality.evidence_count} />
            <Metric label="Supported Claims" value={quality.supported_claim_count} />
            <Metric label="Unverified Claims" value={quality.unverified_claim_count} />
          </div>

          <div>
            <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1">
              <span>Quality</span>
              <span>{qualityScore === null || qualityScore === undefined ? 'Calculating...' : `${Math.round(qualityScore * 100)}%`}</span>
            </div>
            <div className="w-full bg-slate-900 rounded-full h-2 overflow-hidden border border-slate-800">
              <div
                className="bg-gradient-to-r from-blue-600 via-cyan-400 to-emerald-400 h-full rounded-full transition-all duration-500"
                style={{ width: `${qualityScore === null || qualityScore === undefined ? 0 : Math.round(qualityScore * 100)}%` }}
              />
            </div>
          </div>

          <div className="flex items-center gap-1.5 text-xs font-semibold">
            {quality.valid ? (
              <>
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" aria-hidden="true" />
                <span className="text-emerald-400">VALID</span>
              </>
            ) : (
              <>
                <XCircle className="w-3.5 h-3.5 text-amber-400" aria-hidden="true" />
                <span className="text-amber-400">NOT YET VALID</span>
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default ResearchQualityPanel;
