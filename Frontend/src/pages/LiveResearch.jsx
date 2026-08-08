import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Activity,
  Database,
  Terminal,
  FileText,
  Square,
  PlusCircle,
} from 'lucide-react';
import { useResearch } from '../context/ResearchContext';
import { researchAPI } from '../services/api';
import Button from '../components/Button';
import Badge from '../components/Badge';
import Loader from '../components/Loader';

const TERMINAL_STATUSES = new Set(['completed', 'failed', 'cancelled']);

const STATUS_LABELS = {
  queued: 'Queued',
  planning: 'Planning',
  searching: 'Searching',
  analyzing: 'Analyzing',
  generating: 'Generating Report',
  completed: 'Completed',
  failed: 'Failed',
  cancelled: 'Cancelled',
};

function eventTone(type = '') {
  if (type.includes('error') || type.includes('failed') || type.includes('contradiction')) return 'text-red-400';
  if (type.includes('search') || type.includes('browser')) return 'text-sky-300';
  if (type.includes('verification') || type.includes('quality')) return 'text-emerald-400';
  if (type.includes('planning')) return 'text-cyan-300';
  return 'text-slate-300';
}

const LiveResearch = () => {
  const navigate = useNavigate();
  const { activeResearch, activeRunId, runStatus, runError, liveSteps, liveTrace, runSourceCount } = useResearch();
  const [cancelling, setCancelling] = useState(false);

  const isActive = Boolean(activeRunId) && !TERMINAL_STATUSES.has(runStatus);
  const isCompleted = runStatus === 'completed';
  const completedSteps = liveSteps.filter((s) => s.status === 'completed').length;
  const progressPercent = Math.round((completedSteps / liveSteps.length) * 100);
  const activeStep = liveSteps.find((s) => s.status === 'active');

  const handleCancel = async () => {
    if (!activeRunId || cancelling) return;
    setCancelling(true);
    try {
      await researchAPI.cancelResearch(activeRunId);
    } catch {
      // Surfaced via runError on the next poll tick if it actually failed server-side.
    } finally {
      setCancelling(false);
    }
  };

  if (!activeRunId) {
    return (
      <div className="w-full flex flex-col items-center justify-center text-center gap-4 py-24 bg-white border border-slate-200 rounded-[20px] shadow-sm">
        <div className="p-3 rounded-2xl bg-slate-50 border border-slate-200">
          <Activity className="w-8 h-8 text-slate-400" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-slate-900">No research is currently running</h2>
          <p className="text-sm text-slate-500 mt-1">Start a new autonomous research task to see it live here.</p>
        </div>
        <Button variant="primary" icon={PlusCircle} onClick={() => navigate('/new-research')}>
          Start New Research
        </Button>
      </div>
    );
  }

  return (
    <div className="w-full space-y-6 pb-12">
      {/* Header Banner */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 p-6 rounded-[20px] bg-white border border-slate-200 shadow-sm">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <Badge variant={isCompleted ? 'success' : runStatus === 'failed' ? 'danger' : 'cyan'} glow icon={Activity}>
              {STATUS_LABELS[runStatus] || 'Autonomous Agent Live Console'}
            </Badge>
            <span className="text-xs text-slate-500 font-mono">Run ID: {activeRunId.slice(0, 8)}</span>
          </div>
          <h1 className="text-xl md:text-2xl font-bold text-slate-900">{activeResearch.topic}</h1>
          <p className="text-xs text-slate-500">
            Goal: <span className="text-slate-700 font-semibold">{activeResearch.goal}</span> • Depth: <span className="text-sky-600 font-semibold">{activeResearch.depth}</span>
          </p>
          {runError && (
            <p className="text-xs text-red-600" role="alert">
              {runError}
            </p>
          )}
        </div>

        {/* Control Buttons */}
        <div className="flex items-center gap-3">
          {isActive && (
            <Button variant="secondary" size="sm" icon={Square} isLoading={cancelling} onClick={handleCancel}>
              Stop Research
            </Button>
          )}
          <Button
            variant="primary"
            size="sm"
            icon={FileText}
            disabled={!isCompleted}
            onClick={() => navigate('/report')}
          >
            {isCompleted ? 'View Generated Report' : 'Report available when complete'}
          </Button>
        </div>
      </div>

      {/* Grid Layout: Left Progress & Live Cards, Right Console Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT COLUMN: Progress & Live Stats */}
        <div className="lg:col-span-7 space-y-6">
          {/* Animated Loader Header */}
          <div className="p-6 rounded-[20px] bg-white border border-slate-200 shadow-sm flex items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <Loader size="sm" text="" />
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  {isCompleted ? 'Research Complete' : 'Swarm Executive Planner Running'}
                </h3>
                <p className="text-xs text-slate-500">
                  {activeStep ? activeStep.description : isCompleted ? 'All pipeline steps finished.' : 'Waiting for the first status update…'}
                </p>
              </div>
            </div>
            <Badge variant={isCompleted ? 'success' : 'cyan'} glow>
              {progressPercent}% Done
            </Badge>
          </div>

          {/* Progress Bar */}
          <div className="p-4 rounded-[20px] bg-white border border-slate-200 shadow-sm space-y-2">
            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden border border-slate-200">
              <div
                className="bg-slate-900 h-full rounded-full transition-all duration-500"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span className="flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5" /> {runSourceCount} source{runSourceCount === 1 ? '' : 's'} found so far
              </span>
              <span className="font-mono">{STATUS_LABELS[runStatus] || '—'}</span>
            </div>
          </div>

          {/* Pipeline Step List */}
          <div className="p-4 rounded-[20px] bg-white border border-slate-200 shadow-sm">
            <div className="space-y-3">
              {liveSteps.map((step) => (
                <div key={step.id} className="flex items-center gap-3 text-xs">
                  <span
                    className={`w-2 h-2 rounded-full flex-shrink-0 ${
                      step.status === 'completed'
                        ? 'bg-emerald-500'
                        : step.status === 'active'
                          ? 'bg-slate-900 animate-pulse'
                          : 'bg-slate-200'
                    }`}
                  />
                  <span className={`flex-1 ${step.status === 'pending' ? 'text-slate-400' : 'text-slate-700 font-medium'}`}>
                    {step.name}
                  </span>
                  <span className="text-slate-400 font-mono">{step.timestamp}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Terminal Log Feed -- real AgentEvent trace */}
        <div className="lg:col-span-5 flex flex-col h-[500px] bg-slate-900 border border-slate-800 rounded-[20px] p-4 shadow-lg overflow-hidden font-mono text-xs">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
            <span className="flex items-center gap-2 text-cyan-400 font-bold">
              <Terminal className="w-4 h-4" /> Agent Telemetry Console
            </span>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto space-y-2 text-slate-300 pr-2">
            {liveTrace.length === 0 && (
              <p className="text-slate-500">Waiting for the first agent event…</p>
            )}
            {liveTrace.map((event) => (
              <motion.div
                key={event.event_id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2 }}
                className="leading-relaxed hover:bg-slate-900/80 p-1 rounded transition-colors"
              >
                <span className={eventTone(event.type)}>
                  [{new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}]{' '}
                  {event.title}: {event.message}
                </span>
              </motion.div>
            ))}
          </div>

          <div className="pt-3 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-500">
            <span>Status: {isActive ? 'Streaming Logs' : isCompleted ? 'Run Finished' : 'Stopped'}</span>
            {isActive && <span className="text-emerald-400 animate-pulse">● Live Telemetry</span>}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LiveResearch;
