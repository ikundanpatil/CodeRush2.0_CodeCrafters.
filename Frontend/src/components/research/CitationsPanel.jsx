import React from 'react';
import { Quote, ExternalLink } from 'lucide-react';

/** Renders REAL citations from GET /api/research/{id}/result (`citations`),
 * each built by the backend citation engine from an actual Source object.
 * Never invents a citation number, title, publisher, or URL. */
const CitationsPanel = ({ citations }) => {
  return (
    <div className="w-full bg-white border border-slate-200 rounded-[14px] p-5 shadow-sm flex flex-col gap-3">
      <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
        <Quote className="w-4 h-4 text-sky-600" aria-hidden="true" />
        <h4 className="text-sm font-bold text-slate-900">Citations</h4>
      </div>

      {citations === null || citations === undefined ? (
        <p className="text-xs text-slate-500">Waiting for data...</p>
      ) : citations.length === 0 ? (
        <p className="text-xs text-slate-500">No citations yet.</p>
      ) : (
        <ol className="space-y-2 max-h-72 overflow-y-auto pr-1">
          {citations.map((c) => (
            <li key={c.citation_id} className="text-xs">
              <div className="flex items-start gap-2">
                <span className="font-mono text-sky-600 flex-shrink-0">[{c.citation_id}]</span>
                <div className="flex-1 min-w-0">
                  <a
                    href={c.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-semibold text-slate-800 hover:text-sky-700 inline-flex items-start gap-1 transition-colors"
                  >
                    <span className="line-clamp-2">{c.title}</span>
                    <ExternalLink className="w-3 h-3 flex-shrink-0 mt-0.5 text-slate-500" aria-hidden="true" />
                  </a>
                  <p className="text-[10px] text-slate-500">{c.publisher}</p>
                </div>
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
};

export default CitationsPanel;
