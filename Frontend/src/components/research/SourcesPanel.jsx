import React from 'react';
import { Link2, ExternalLink } from 'lucide-react';

const domainOf = (url) => {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return '';
  }
};

/** Renders REAL sources from GET /api/research/{id}/result -- never
 * invents a source. Links open safely (new tab, no opener/referrer leak). */
const SourcesPanel = ({ sources }) => {
  return (
    <div className="w-full bg-[#1E293B]/90 border border-slate-700/80 rounded-[14px] p-5 shadow-xl flex flex-col gap-3">
      <div className="flex items-center gap-2 pb-3 border-b border-slate-700/60">
        <Link2 className="w-4 h-4 text-cyan-400" aria-hidden="true" />
        <h4 className="text-sm font-bold text-slate-100">Sources</h4>
      </div>

      {sources === null || sources === undefined ? (
        <p className="text-xs text-slate-500">Waiting for data...</p>
      ) : sources.length === 0 ? (
        <p className="text-xs text-slate-500">No sources found yet.</p>
      ) : (
        <ul className="space-y-2 max-h-72 overflow-y-auto pr-1">
          {sources.map((source) => (
            <li key={source.id} className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
              <a
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-start justify-between gap-2 text-xs font-semibold text-slate-200 hover:text-cyan-300 transition-colors"
              >
                <span className="line-clamp-2">{source.title}</span>
                <ExternalLink className="w-3.5 h-3.5 flex-shrink-0 text-slate-500" aria-hidden="true" />
              </a>
              <div className="flex items-center justify-between mt-1 text-[10px] text-slate-500">
                <span>
                  {source.publisher || 'Unknown Publisher'} &middot; {domainOf(source.url)}
                </span>
                <span>{source.evidence?.length ?? 0} evidence</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default SourcesPanel;
