import React, { useState } from 'react';
import {
  Share2,
  CheckCircle2,
  ShieldCheck,
  BookOpen,
  Table as TableIcon,
  Sparkles,
  Download,
} from 'lucide-react';
import Button from './Button';
import Badge from './Badge';
import { reportAPI } from '../services/api';

const ReportCard = ({ report }) => {
  const [exported, setExported] = useState(false);
  const [pdfError, setPdfError] = useState(null);
  const [downloading, setDownloading] = useState(false);

  // Part O: previously this downloaded a JSON blob under a "Download PDF"
  // label. It now calls the ONE authoritative PDF path -- the real
  // reportlab-generated PDF from GET /api/research/{run_id}/report/pdf.
  const handleDownloadPDF = async () => {
    const runId = report?.run_id;
    if (!runId) {
      setPdfError('This report has no research run associated with it yet.');
      return;
    }
    setDownloading(true);
    setPdfError(null);
    try {
      await reportAPI.downloadRunPDF(runId);
    } catch {
      setPdfError('Report service unavailable -- the PDF could not be generated.');
    } finally {
      setDownloading(false);
    }
  };

  const handleExport = async () => {
    const runId = report?.run_id;
    if (!runId) {
      setPdfError('This report has no research run associated with it yet.');
      return;
    }
    try {
      await reportAPI.exportRunJSON(runId);
      setExported(true);
      setTimeout(() => setExported(false), 2500);
    } catch {
      setPdfError('Export failed -- research service unavailable.');
    }
  };

  return (
    <div className="w-full bg-white border border-slate-200 rounded-[14px] p-6 md:p-8 shadow-md space-y-8">
      {/* Report Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-200">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <Badge variant="cyan" glow icon={Sparkles}>
              Verified Deep Research
            </Badge>
            <span className="text-xs text-slate-500 font-mono">{report.date}</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-slate-900 tracking-tight leading-snug">
            {report.title}
          </h1>
          <p className="text-sm text-slate-500">{report.subtitle}</p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col items-end gap-2">
          <div className="flex items-center gap-3">
            <Button variant="secondary" size="sm" icon={Share2} onClick={handleExport}>
              {exported ? 'Exported!' : 'Export JSON'}
            </Button>
            <Button variant="primary" size="sm" icon={Download} isLoading={downloading} onClick={handleDownloadPDF}>
              Download PDF
            </Button>
          </div>
          {pdfError && (
            <p className="text-xs text-red-500" role="alert">
              {pdfError}
            </p>
          )}
        </div>
      </div>

      {/* Metrics & Confidence Gauge */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 rounded-[14px] bg-slate-50 border border-slate-200">
        <div className="flex flex-col gap-1">
          <span className="text-xs text-slate-500 font-medium">Confidence Score</span>
          <span className="text-xl font-bold text-emerald-600 flex items-center gap-1.5">
            <ShieldCheck className="w-5 h-5 text-emerald-600" />
            {report.confidenceScore}%
          </span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-xs text-slate-500 font-medium">Verified Sources</span>
          <span className="text-xl font-bold text-sky-600">{report.citationCount} Papers & Repos</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-xs text-slate-500 font-medium">Reading Time</span>
          <span className="text-xl font-bold text-slate-800">{report.readingTime}</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-xs text-slate-500 font-medium">Research Depth</span>
          <span className="text-xl font-bold text-indigo-500">{report.depth}</span>
        </div>
      </div>

      {/* 1. Executive Summary */}
      <section className="space-y-3">
        <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2 border-b border-slate-200 pb-2">
          <BookOpen className="w-5 h-5 text-sky-600" />
          Executive Summary
        </h3>
        <p className="text-slate-600 text-sm leading-relaxed whitespace-pre-line bg-slate-50 p-4 rounded-xl border border-slate-200">
          {report.executiveSummary}
        </p>
      </section>

      {/* 2. Key Findings */}
      <section className="space-y-4">
        <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2 border-b border-slate-200 pb-2">
          <Sparkles className="w-5 h-5 text-sky-600" />
          Key Research Findings
        </h3>
        <div className="grid gap-4">
          {report.findings.map((item, idx) => (
            <div key={idx} className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
              <h4 className="text-sm font-semibold text-slate-800">{item.heading}</h4>
              <p className="text-xs text-slate-500 leading-relaxed">{item.content}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 3. Comparison Table */}
      {report.comparisonTable && report.comparisonTable.length > 0 && (
        <section className="space-y-4">
          <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2 border-b border-slate-200 pb-2">
            <TableIcon className="w-5 h-5 text-sky-600" />
            Framework Performance Comparison Matrix
          </h3>
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200 uppercase">
                  <th className="py-3 px-4">Framework</th>
                  <th className="py-3 px-4">Reasoning Engine</th>
                  <th className="py-3 px-4">Latency</th>
                  <th className="py-3 px-4">Accuracy</th>
                  <th className="py-3 px-4">Cost / Task</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-600">
                {report.comparisonTable.map((row, rIdx) => (
                  <tr key={rIdx} className={rIdx === 0 ? 'bg-sky-50 font-medium text-sky-700' : 'hover:bg-slate-50'}>
                    <td className="py-3 px-4 font-bold">{row.framework}</td>
                    <td className="py-3 px-4">{row.reasoning}</td>
                    <td className="py-3 px-4 font-mono">{row.speed}</td>
                    <td className="py-3 px-4 font-semibold text-emerald-600">{row.accuracy}</td>
                    <td className="py-3 px-4 font-mono text-slate-500">{row.cost}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* 4. Strategic Recommendations */}
      <section className="space-y-3">
        <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2 border-b border-slate-200 pb-2">
          <CheckCircle2 className="w-5 h-5 text-emerald-600" />
          Strategic Recommendations
        </h3>
        <ul className="space-y-2 text-xs text-slate-600">
          {report.recommendations.map((rec, idx) => (
            <li key={idx} className="flex items-start gap-2.5 p-3 rounded-xl bg-slate-50 border border-slate-200">
              <span className="w-5 h-5 rounded-full bg-sky-100 text-sky-600 font-bold text-[11px] flex items-center justify-center flex-shrink-0 mt-0.5">
                {idx + 1}
              </span>
              <span className="leading-snug">{rec}</span>
            </li>
          ))}
        </ul>
      </section>

      {/* 5. References & Sources */}
      <section className="space-y-3">
        <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2 border-b border-slate-200 pb-2">
          <BookOpen className="w-5 h-5 text-indigo-500" />
          Cited Primary Sources & Whitepapers
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {report.references.map((ref, idx) => (
            <a
              key={idx}
              href={ref.link}
              target="_blank"
              rel="noreferrer"
              className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 hover:border-sky-300 transition-all flex items-start justify-between gap-3 group"
            >
              <div className="space-y-1">
                <p className="text-xs font-semibold text-slate-800 group-hover:text-sky-600 transition-colors leading-snug">
                  {ref.title}
                </p>
                <p className="text-[11px] text-slate-500 font-mono">{ref.source}</p>
              </div>
              <Badge variant="cyan" size="sm">
                {ref.rating}
              </Badge>
            </a>
          ))}
        </div>
      </section>
    </div>
  );
};

export default ReportCard;
