import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { History as HistoryIcon, Eye, Trash2, PlusCircle, Sparkles, Clock, AlertTriangle } from 'lucide-react';
import { useResearch } from '../context/ResearchContext';
import Table from '../components/Table';
import Button from '../components/Button';
import Badge from '../components/Badge';
import Modal from '../components/Modal';

const History = () => {
  const navigate = useNavigate();
  const { historyList, deleteHistoryItem, setCurrentReport } = useResearch();
  const [selectedToDelete, setSelectedToDelete] = useState(null);

  const columns = [
    {
      header: 'Research Topic',
      accessor: 'topic',
      sortable: true,
      render: (row) => (
        <div className="space-y-1">
          <p className="font-semibold text-slate-200 hover:text-cyan-300 transition-colors line-clamp-1">
            {row.topic}
          </p>
          <div className="flex items-center gap-2 text-[11px] text-slate-400 font-mono">
            <span>{row.sourcesCount} Sources</span>
            <span>•</span>
            <span className="text-cyan-400">{row.depth}</span>
          </div>
        </div>
      ),
    },
    {
      header: 'Date',
      accessor: 'date',
      sortable: true,
      className: 'w-32',
      render: (row) => <span className="font-mono text-xs text-slate-400">{row.date}</span>,
    },
    {
      header: 'Status',
      accessor: 'status',
      className: 'w-32',
      render: (row) => (
        <Badge
          variant={row.status === 'Completed' ? 'success' : row.status === 'In Progress' ? 'cyan' : 'warning'}
          glow={row.status === 'In Progress'}
        >
          {row.status}
        </Badge>
      ),
    },
    {
      header: 'Duration',
      accessor: 'duration',
      className: 'w-28',
      render: (row) => (
        <span className="flex items-center gap-1 text-xs text-slate-400 font-mono">
          <Clock className="w-3 h-3" />
          {row.duration}
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
            onClick={() => {
              navigate('/report');
            }}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-cyan-500/20 text-cyan-400 hover:text-cyan-300 transition-colors cursor-pointer"
            title="Open Report"
          >
            <Eye className="w-4 h-4" />
          </button>
          <button
            onClick={() => setSelectedToDelete(row)}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-red-500/20 text-slate-400 hover:text-red-400 transition-colors cursor-pointer"
            title="Delete Record"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="w-full space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Badge variant="cyan" glow icon={HistoryIcon}>
              Audit Trail & Execution Logs
            </Badge>
          </div>
          <h1 className="text-2xl font-extrabold text-slate-100">Autonomous Research History</h1>
          <p className="text-xs text-slate-400">Search and review past agent execution runs and exported whitepapers.</p>
        </div>

        <Button variant="primary" size="md" icon={PlusCircle} onClick={() => navigate('/new-research')}>
          New Research
        </Button>
      </div>

      {/* Table Component */}
      <Table columns={columns} data={historyList} searchKey="topic" />

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={Boolean(selectedToDelete)}
        onClose={() => setSelectedToDelete(null)}
        title="Delete Research Record"
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setSelectedToDelete(null)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={() => {
                deleteHistoryItem(selectedToDelete.id);
                setSelectedToDelete(null);
              }}
            >
              Delete Record
            </Button>
          </>
        }
      >
        <div className="flex items-start gap-3 py-2">
          <div className="p-2 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-200">
              Are you sure you want to delete this research record?
            </p>
            <p className="text-xs text-slate-400 mt-1">
              "{selectedToDelete?.topic}". This action will permanently purge stored embeddings and generated report caches.
            </p>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default History;
