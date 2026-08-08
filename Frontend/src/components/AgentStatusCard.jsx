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
    <div className="w-full bg-white border border-slate-200 rounded-[14px] p-5 shadow-sm flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-sky-50 border border-sky-200 text-sky-600">
            <Activity className="w-4 h-4 animate-pulse" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-slate-900">Agent Workflow Pipeline</h4>
            <p className="text-[11px] text-slate-500">8 Autonomous Cognitive Nodes</p>
          </div>
        </div>

        <Badge variant={progressPercent === 100 ? 'success' : 'cyan'} glow>
          {progressPercent}% Done
        </Badge>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden p-0.5 border border-slate-200">
        <div
          className="bg-slate-900 h-full rounded-full transition-all duration-500"
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      {/* Workflow Step Timeline */}
      <div className="space-y-3 relative before:absolute before:left-[19px] before:top-3 before:bottom-3 before:w-[2px] before:bg-slate-100">
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
                    ? 'bg-emerald-50 border border-emerald-200 text-emerald-600'
                    : isActive
                    ? 'bg-slate-900 border border-slate-900 text-white ring-4 ring-slate-200 animate-pulse'
                    : 'bg-white border border-slate-200 text-slate-400'
                }`}
              >
                {isCompleted ? (
                  <CheckCircle2 className="w-5 h-5" />
                ) : isActive ? (
                  <StepIcon className="w-5 h-5 animate-spin-slow text-white" />
                ) : (
                  <StepIcon className="w-4 h-4" />
                )}
              </div>

              {/* Step Information */}
              <div className="flex-1 pt-0.5">
                <div className="flex items-center justify-between">
                  <span
                    className={`font-semibold text-xs ${
                      isCompleted ? 'text-slate-800' : isActive ? 'text-slate-900' : 'text-slate-400'
                    }`}
                  >
                    {step.name}
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">{step.timestamp}</span>
                </div>
                <p className="text-[11px] text-slate-500 mt-0.5 leading-snug">{step.description}</p>

                {isActive && (
                  <div className="mt-2 p-2 rounded-lg bg-slate-900 border border-slate-900 text-[10px] font-mono text-emerald-300 space-y-0.5">
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
      <div className="pt-3 border-t border-slate-100 grid grid-cols-2 gap-2 text-center text-xs">
        <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
          <span className="text-[10px] text-slate-500 block">Active Workers</span>
          <span className="font-bold text-slate-800">8 Swarm Threads</span>
        </div>
        <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
          <span className="text-[10px] text-slate-500 block">Reflection Checks</span>
          <span className="font-bold text-emerald-600">Zero Hallucinations</span>
        </div>
      </div>
    </div>
  );
};

export default AgentStatusCard;
