import React from 'react';
import { AlertTriangle, CheckCircle2 } from 'lucide-react';
import Badge from '../Badge';

const PRIORITY_VARIANT = { high: 'danger', medium: 'warning', low: 'neutral' };

/** Renders REAL gaps from GET /api/research/{id}/iterations (Phase 6
 * `analyze_gaps`, embedded per-iteration) -- never a fabricated warning. */
const ResearchGapPanel = ({ gaps, iterationCount }) => {
  return (
    <div className="w-full bg-white border border-slate-200 rounded-[14px] p-5 shadow-sm flex flex-col gap-3">
      <div className="flex items-center justify-between pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-sky-600" aria-hidden="true" />
          <h4 className="text-sm font-bold text-slate-900">Research Gaps</h4>
        </div>
        <span className="text-[10px] text-slate-500">
          Iterations: {iterationCount === null || iterationCount === undefined ? 'Calculating...' : iterationCount}
        </span>
      </div>

      {gaps === null || gaps === undefined ? (
        <p className="text-xs text-slate-500">Calculating...</p>
      ) : gaps.length === 0 ? (
        <div className="flex items-center gap-1.5 text-xs text-emerald-600">
          <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />
          No research gaps detected.
        </div>
      ) : (
        <>
          <ul className="space-y-1.5">
            {gaps.map((gap, idx) => (
              <li key={idx} className="flex items-start gap-2 text-xs">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-500 mt-0.5 flex-shrink-0" aria-hidden="true" />
                <span className="text-slate-600 flex-1">{gap.description}</span>
                <Badge variant={PRIORITY_VARIANT[gap.priority] || 'neutral'} size="sm">
                  {gap.priority}
                </Badge>
              </li>
            ))}
          </ul>
          <p className="text-[11px] text-slate-500 italic">Additional research recommended.</p>
        </>
      )}
    </div>
  );
};

export default ResearchGapPanel;
