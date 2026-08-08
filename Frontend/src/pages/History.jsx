import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { History as HistoryIcon, Eye, PlusCircle, FileDown, AlertTriangle, ShieldCheck } from 'lucide-react';
import { researchAPI, reportAPI } from '../services/api';
import Table from '../components/Table';
import Button from '../components/Button';
import Badge from '../components/Badge';

// Part G: real research history from GET /api/research/history. No mock
// fallback -- if the backend is unreachable the page says so rather than
// showing fabricated research runs.
const History = () => {
  const navigate = useNavigate();
  const [rows, setRows] = useState(null);
  const [error, setError] = useState(null);
  const [downloadingId, setDownloadingId] = useState(null);

  useEffect(() => {
    let cancelled = false;
    researchAPI
      .getResearchHistory()
      .then((data) => {
        if (!cancelled) setRows(data);
      })
      .catch(() => {
        if (!cancelled) setError('Research service unavailable -- history could not be loaded.');
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleDownloadPDF = async (runId) => {
    setDownloadingId(runId);
    try {
      await reportAPI.downloadRunPDF(runId);
    } catch {
      setError('Report service unavailable -- the PDF could not be generated.');
    } finally {
      setDownloadingId(null);
    }
  };

  const columns = [
    {
      header: 'Research Question',
      accessor: 'question',
      sortable: true,
      render: (row) => (
        <div className="space-y-1">
          <p className="font-semibold text-slate-800 line-clamp-1">{row.question}</p>
          <div className="flex items-center gap-2 text-[11px] text-slate-500 font-mono">
            <span>{row.source_count} sources</span>
            <span>&bull;</span>
            <span>{row.claim_count} claims</span>
            <span>&bull;</span>
            <span>{row.iteration_count} iterations</span>
          </div>
        </div>
      ),
    },
    {
      header: 'Date',
      accessor: 'created_at',
      sortable: true,
      className: 'w-36',
      render: (row) => (
        <span className="font-mono text-xs text-slate-500">
          {new Date(row.created_at).toLocaleString()}
        </span>
      ),
    },
    {
      header: 'Status',
      accessor: 'status',
      className: 'w-28',
      render: (row) => (
        <Badge
          variant={
            row.status === 'completed' ? 'success'
              : row.status === 'failed' ? 'danger'
                : row.status === 'cancelled' ? 'neutral' : 'cyan'
          }
          glow={!['completed', 'failed', 'cancelled'].includes(row.status)}
        >
          {row.status}
        </Badge>
      ),
    },
    {
      header: 'Verified',
      accessor: 'verification_valid',
      className: 'w-28',
      render: (row) =>
        row.verification_valid === null || row.verification_valid === undefined ? (
          <span className="text-xs text-slate-500">&mdash;</span>
        ) : (
          <span
            className={`flex items-center gap-1 text-xs ${row.verification_valid ? 'text-emerald-600' : 'text-amber-600'}`}
          >
            <ShieldCheck className="w-3 h-3" aria-hidden="true" />
            {row.verification_valid ? 'Verified' : 'Issues'}
          </span>
        ),
    },
    {
      header: 'Actions',
      accessor: 'actions',
      className: 'w-32 text-right',
      render: (row) => (
        <div className="flex items-center justify-end gap-2" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={() => navigate(`/command-center?run=${row.run_id}`)}
            className="p-1.5 rounded-lg bg-slate-100 hover:bg-sky-50 text-sky-600 hover:text-sky-700 transition-colors cursor-pointer"
            title="Open research session"
            aria-label={`Open research session for ${row.question}`}
          >
            <Eye className="w-4 h-4" />
          </button>
          <button
            onClick={() => handleDownloadPDF(row.run_id)}
            disabled={!row.report_available || downloadingId === row.run_id}
            className="p-1.5 rounded-lg bg-slate-100 hover:bg-emerald-50 text-slate-500 hover:text-emerald-600 transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
            title={row.report_available ? 'Download PDF report' : 'Report not available yet'}
            aria-label={`Download PDF report for ${row.question}`}
          >
            <FileDown className="w-4 h-4" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="w-full space-y-6 pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Badge variant="cyan" glow icon={HistoryIcon}>
              Audit Trail & Execution Logs
            </Badge>
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900">Autonomous Research History</h1>
          <p className="text-xs text-slate-500">Past research runs, with verification status and downloadable reports.</p>
        </div>

        <Button variant="primary" size="md" icon={PlusCircle} onClick={() => navigate('/command-center')}>
          New Research
        </Button>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2" role="alert">
          <AlertTriangle className="w-4 h-4" aria-hidden="true" />
          {error}
        </div>
      )}

      {rows === null && !error ? (
        <p className="text-sm text-slate-500">Loading research history...</p>
      ) : rows && rows.length === 0 ? (
        <p className="text-sm text-slate-500">No research runs yet. Start one from the Command Center.</p>
      ) : rows ? (
        <Table columns={columns} data={rows} searchKey="question" />
      ) : null}
    </div>
  );
};

export default History;
