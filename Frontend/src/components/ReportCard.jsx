import React, { useState } from 'react';
import {
  FileDown,
  Share2,
  CheckCircle2,
  ShieldCheck,
  BookOpen,
  ExternalLink,
  Table as TableIcon,
  Sparkles,
  Download,
  Copy,
} from 'lucide-react';
import Button from './Button';
import Badge from './Badge';

const ReportCard = ({ report }) => {
  const [exported, setExported] = useState(false);

  const handleDownloadPDF = () => {
    const element = document.createElement('a');
    const file = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    element.href = URL.createObjectURL(file);
    element.download = `${report.topic.toLowerCase().replace(/\s+/g, '_')}_report.json`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const handleExport = () => {
    setExported(true);
    setTimeout(() => setExported(false), 2500);
  };

  return (
    <div className="w-full bg-[#1E293B] border border-slate-700/80 rounded-[14px] p-6 md:p-8 shadow-2xl space-y-8">
      {/* Report Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-700/80">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <Badge variant="cyan" glow icon={Sparkles}>
              Verified Deep Research
            </Badge>
            <span className="text-xs text-slate-400 font-mono">{report.date}</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-slate-100 tracking-tight leading-snug">
            {report.title}
          </h1>
          <p className="text-sm text-slate-400">{report.subtitle}</p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-3">
          <Button variant="secondary" size="sm" icon={Share2} onClick={handleExport}>
            {exported ? 'Link Copied!' : 'Share'}
          </Button>
          <Button variant="primary" size="sm" icon={Download} onClick={handleDownloadPDF}>
            Download PDF
          </Button>
        </div>
      </div>

      {/* Metrics & Confidence Gauge */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 rounded-[14px] bg-[#111827]/60 border border-slate-700/60">
        <div className="flex flex-col gap-1">
          <span className="text-xs text-slate-400 font-medium">Confidence Score</span>
          <span className="text-xl font-bold text-emerald-400 flex items-center gap-1.5">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            {report.confidenceScore}%
          </span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-xs text-slate-400 font-medium">Verified Sources</span>
          <span className="text-xl font-bold text-cyan-400">{report.citationCount} Papers & Repos</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-xs text-slate-400 font-medium">Reading Time</span>
          <span className="text-xl font-bold text-slate-200">{report.readingTime}</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-xs text-slate-400 font-medium">Research Depth</span>
          <span className="text-xl font-bold text-blue-400">{report.depth}</span>
        </div>
      </div>

      {/* 1. Executive Summary */}
      <section className="space-y-3">
        <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2 border-b border-slate-700/50 pb-2">
          <BookOpen className="w-5 h-5 text-cyan-400" />
          Executive Summary
        </h3>
        <p className="text-slate-300 text-sm leading-relaxed whitespace-pre-line bg-slate-900/40 p-4 rounded-xl border border-slate-800">
          {report.executiveSummary}
        </p>
      </section>

      {/* 2. Key Findings */}
      <section className="space-y-4">
        <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2 border-b border-slate-700/50 pb-2">
          <Sparkles className="w-5 h-5 text-cyan-400" />
          Key Research Findings
        </h3>
        <div className="grid gap-4">
          {report.findings.map((item, idx) => (
            <div key={idx} className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 space-y-1.5">
              <h4 className="text-sm font-semibold text-slate-200">{item.heading}</h4>
              <p className="text-xs text-slate-400 leading-relaxed">{item.content}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 3. Comparison Table */}
      {report.comparisonTable && report.comparisonTable.length > 0 && (
        <section className="space-y-4">
          <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2 border-b border-slate-700/50 pb-2">
            <TableIcon className="w-5 h-5 text-cyan-400" />
            Framework Performance Comparison Matrix
          </h3>
          <div className="overflow-x-auto rounded-xl border border-slate-700/60 bg-slate-900/60">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-[#111827] text-slate-400 font-semibold border-b border-slate-700/60 uppercase">
                  <th className="py-3 px-4">Framework</th>
                  <th className="py-3 px-4">Reasoning Engine</th>
                  <th className="py-3 px-4">Latency</th>
                  <th className="py-3 px-4">Accuracy</th>
                  <th className="py-3 px-4">Cost / Task</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-slate-300">
                {report.comparisonTable.map((row, rIdx) => (
                  <tr key={rIdx} className={rIdx === 0 ? 'bg-cyan-500/10 font-medium text-cyan-300' : 'hover:bg-slate-800/40'}>
                    <td className="py-3 px-4 font-bold">{row.framework}</td>
                    <td className="py-3 px-4">{row.reasoning}</td>
                    <td className="py-3 px-4 font-mono">{row.speed}</td>
                    <td className="py-3 px-4 font-semibold text-emerald-400">{row.accuracy}</td>
                    <td className="py-3 px-4 font-mono text-slate-400">{row.cost}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* 4. Strategic Recommendations */}
      <section className="space-y-3">
        <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2 border-b border-slate-700/50 pb-2">
          <CheckCircle2 className="w-5 h-5 text-emerald-400" />
          Strategic Recommendations
        </h3>
        <ul className="space-y-2 text-xs text-slate-300">
          {report.recommendations.map((rec, idx) => (
            <li key={idx} className="flex items-start gap-2.5 p-3 rounded-xl bg-slate-900/40 border border-slate-800">
              <span className="w-5 h-5 rounded-full bg-cyan-500/20 text-cyan-400 font-bold text-[11px] flex items-center justify-center flex-shrink-0 mt-0.5">
                {idx + 1}
              </span>
              <span className="leading-snug">{rec}</span>
            </li>
          ))}
        </ul>
      </section>

      {/* 5. References & Sources */}
      <section className="space-y-3">
        <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2 border-b border-slate-700/50 pb-2">
          <BookOpen className="w-5 h-5 text-blue-400" />
          Cited Primary Sources & Whitepapers
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {report.references.map((ref, idx) => (
            <a
              key={idx}
              href={ref.link}
              target="_blank"
              rel="noreferrer"
              className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-cyan-500/50 transition-all flex items-start justify-between gap-3 group"
            >
              <div className="space-y-1">
                <p className="text-xs font-semibold text-slate-200 group-hover:text-cyan-300 transition-colors leading-snug">
                  {ref.title}
                </p>
                <p className="text-[11px] text-slate-400 font-mono">{ref.source}</p>
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
