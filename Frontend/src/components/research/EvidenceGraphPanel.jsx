import React from 'react';
import { GitBranch } from 'lucide-react';

/** Renders the REAL evidence graph from GET /api/evidence/graph/{id}
 * (Phase 4 backend, read-only here -- the frontend never writes evidence).
 * A grouped Claim -> Evidence -> Source list rather than a force-directed
 * graph library, to avoid a new dependency while staying honest about the
 * real node/edge data. */
const EvidenceGraphPanel = ({ graph }) => {
  if (graph === null || graph === undefined) {
    return (
      <Panel>
        <p className="text-xs text-slate-500">Waiting for data...</p>
      </Panel>
    );
  }

  const nodes = graph.nodes || [];
  const edges = graph.edges || [];
  const claims = nodes.filter((n) => n.type === 'claim');

  if (nodes.length === 0) {
    return (
      <Panel>
        <p className="text-xs text-slate-500">No evidence graph yet.</p>
      </Panel>
    );
  }

  const nodeById = Object.fromEntries(nodes.map((n) => [n.id, n]));
  const edgesFrom = (id) => edges.filter((e) => e.from === id);

  return (
    <Panel>
      <ul className="space-y-3">
        {claims.map((claim) => {
          const evidenceEdges = edgesFrom(claim.id);
          return (
            <li key={claim.id} className="text-xs">
              <p className="font-semibold text-slate-200">{claim.label}</p>
              <ul className="mt-1.5 ml-3 pl-3 border-l border-slate-700/60 space-y-1.5">
                {evidenceEdges.map((edge) => {
                  const evidenceNode = nodeById[edge.to];
                  if (!evidenceNode) return null;
                  const sourceEdge = edgesFrom(evidenceNode.id).find((e) => e.relationship === 'DERIVED_FROM');
                  const sourceNode = sourceEdge ? nodeById[sourceEdge.to] : null;
                  return (
                    <li key={evidenceNode.id} className="text-slate-400">
                      <span className="text-slate-500">{edge.relationship}</span> {evidenceNode.label}
                      {sourceNode && <span className="text-slate-600"> -- from {sourceNode.label}</span>}
                    </li>
                  );
                })}
                {evidenceEdges.length === 0 && <li className="text-slate-600">No linked evidence.</li>}
              </ul>
            </li>
          );
        })}
        {claims.length === 0 && <p className="text-slate-500">No claims extracted yet.</p>}
      </ul>
    </Panel>
  );
};

const Panel = ({ children }) => (
  <div className="w-full bg-[#1E293B]/90 border border-slate-700/80 rounded-[14px] p-5 shadow-xl flex flex-col gap-3">
    <div className="flex items-center gap-2 pb-3 border-b border-slate-700/60">
      <GitBranch className="w-4 h-4 text-cyan-400" aria-hidden="true" />
      <h4 className="text-sm font-bold text-slate-100">Evidence Graph</h4>
    </div>
    <div className="max-h-72 overflow-y-auto pr-1">{children}</div>
  </div>
);

export default EvidenceGraphPanel;
