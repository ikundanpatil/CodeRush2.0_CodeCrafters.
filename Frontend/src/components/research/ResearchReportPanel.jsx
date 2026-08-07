import React, { useState } from 'react';
import { FileText, Volume2, Copy, Download, Check, FileDown } from 'lucide-react';
import Button from '../Button';

/** Renders the REAL final report (`answer`) from GET /api/research/{id}/result
 * -- the exact text the backend's orchestrator generated. Never regenerates
 * or rewrites it on the frontend. Export reuses the same local-blob-download
 * pattern already used by ReportCard.jsx, no new backend endpoint needed. */
const ResearchReportPanel = ({ finalReport, query, onReadAloud, speaking, onGeneratePDF, canGeneratePDF = false }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!finalReport) return;
    try {
      await navigator.clipboard.writeText(finalReport);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard API can be unavailable/denied -- fail silently, no crash.
    }
  };

  const handleExport = () => {
    if (!finalReport) return;
    const blob = new Blob([finalReport], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `evoresearch-report-${Date.now()}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="w-full bg-[#1E293B]/90 border border-slate-700/80 rounded-[14px] p-5 shadow-xl flex flex-col gap-3">
      <div className="flex items-center justify-between pb-3 border-b border-slate-700/60">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-cyan-400" aria-hidden="true" />
          <h4 className="text-sm font-bold text-slate-100">Final Report</h4>
        </div>
        {query && <span className="text-[11px] text-slate-500 truncate max-w-xs">{query}</span>}
      </div>

      {!finalReport ? (
        <p className="text-xs text-slate-500">Waiting for data...</p>
      ) : (
        <>
          <div className="max-h-96 overflow-y-auto pr-1 text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
            {finalReport}
          </div>
          <div className="flex flex-wrap gap-2 pt-2 border-t border-slate-700/60">
            <Button size="sm" variant="secondary" icon={Volume2} onClick={onReadAloud} disabled={speaking}>
              Read Aloud
            </Button>
            <Button size="sm" variant="secondary" icon={copied ? Check : Copy} onClick={handleCopy}>
              {copied ? 'Copied' : 'Copy'}
            </Button>
            <Button size="sm" variant="secondary" icon={Download} onClick={handleExport}>
              Export
            </Button>
            {canGeneratePDF && onGeneratePDF && (
              <Button size="sm" variant="primary" icon={FileDown} onClick={onGeneratePDF}>
                Generate PDF
              </Button>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default ResearchReportPanel;
