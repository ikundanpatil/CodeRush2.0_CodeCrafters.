import React from 'react';
import {
  Kanban,
  Search,
  Globe,
  BookOpen,
  BarChart2,
  RefreshCw,
  FileCheck,
  CheckCircle2,
  Clock,
  Activity,
  Cpu,
} from 'lucide-react';
import GithubIcon from './GithubIcon';
import { useResearch } from '../context/ResearchContext';
import Badge from './Badge';

const iconMap = {
  Kanban,
  Search,
  Globe,
  Github: GithubIcon,
  BookOpen,
  BarChart2,
  RefreshCw,
  FileCheck,
};

const AgentStatusCard = () => {
  const { liveSteps } = useResearch();

  const completedCount = liveSteps.filter((s) => s.status === 'completed').length;
  const progressPercent = Math.round((completedCount / liveSteps.length) * 100);

  return (
    <div className="w-full bg-[#1E293B]/90 border border-slate-700/80 rounded-[14px] p-5 shadow-xl flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-700/60">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Activity className="w-4 h-4 animate-pulse" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-slate-100">Agent Workflow Pipeline</h4>
            <p className="text-[11px] text-slate-400">8 Autonomous Cognitive Nodes</p>
          </div>
        </div>

        <Badge variant={progressPercent === 100 ? 'success' : 'cyan'} glow>
          {progressPercent}% Done
        </Badge>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-slate-900 rounded-full h-2 overflow-hidden p-0.5 border border-slate-800">
        <div
          className="bg-gradient-to-r from-blue-600 via-cyan-400 to-emerald-400 h-full rounded-full transition-all duration-500 shadow-[0_0_12px_rgba(6,182,212,0.5)]"
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      {/* Workflow Step Timeline */}
      <div className="space-y-3 relative before:absolute before:left-[19px] before:top-3 before:bottom-3 before:w-[2px] before:bg-slate-800">
        {liveSteps.map((step) => {
          const StepIcon = iconMap[step.icon] || Cpu;
          const isCompleted = step.status === 'completed';
          const isActive = step.status === 'active';

          return (
            <div key={step.id} className="relative flex items-start gap-3 text-xs group">
              {/* Timeline Step Circle */}
              <div
                className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 z-10 transition-all ${
                  isCompleted
                    ? 'bg-emerald-500/15 border border-emerald-500/40 text-emerald-400 shadow-md shadow-emerald-500/10'
                    : isActive
                    ? 'bg-cyan-500/20 border border-cyan-400 text-cyan-300 ring-4 ring-cyan-500/20 animate-pulse'
                    : 'bg-slate-900 border border-slate-800 text-slate-500'
                }`}
              >
                {isCompleted ? (
                  <CheckCircle2 className="w-5 h-5" />
                ) : isActive ? (
                  <StepIcon className="w-5 h-5 animate-spin-slow text-cyan-300" />
                ) : (
                  <StepIcon className="w-4 h-4" />
                )}
              </div>

              {/* Step Information */}
              <div className="flex-1 pt-0.5">
                <div className="flex items-center justify-between">
                  <span
                    className={`font-semibold text-xs ${
                      isCompleted ? 'text-slate-200' : isActive ? 'text-cyan-300' : 'text-slate-400'
                    }`}
                  >
                    {step.name}
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">{step.timestamp}</span>
                </div>
                <p className="text-[11px] text-slate-400 mt-0.5 leading-snug">{step.description}</p>

                {isActive && (
                  <div className="mt-2 p-2 rounded-lg bg-slate-900/80 border border-cyan-500/30 text-[10px] font-mono text-cyan-300 space-y-0.5 animate-pulse">
                    {step.logs.map((log, lIdx) => (
                      <div key={lIdx}>&gt; {log}</div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer Metrics */}
      <div className="pt-3 border-t border-slate-700/60 grid grid-cols-2 gap-2 text-center text-xs">
        <div className="p-2 rounded-xl bg-slate-900/60 border border-slate-800">
          <span className="text-[10px] text-slate-400 block">Active Workers</span>
          <span className="font-bold text-slate-200">8 Swarm Threads</span>
        </div>
        <div className="p-2 rounded-xl bg-slate-900/60 border border-slate-800">
          <span className="text-[10px] text-slate-400 block">Reflection Checks</span>
          <span className="font-bold text-emerald-400">Zero Hallucinations</span>
        </div>
      </div>
    </div>
  );
};

export default AgentStatusCard;
