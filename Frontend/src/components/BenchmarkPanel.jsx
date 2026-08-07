import React, { useState } from 'react';
import { BarChart3, PlayCircle, TrendingUp, TrendingDown, Minus, Shuffle } from 'lucide-react';
import { benchmarkAPI } from '../services/api';
import Badge from './Badge';
import Button from './Button';

const statusMeta = {
  IMPROVED: { variant: 'success', icon: TrendingUp },
  REGRESSED: { variant: 'danger', icon: TrendingDown },
  UNCHANGED: { variant: 'neutral', icon: Minus },
  MIXED: { variant: 'warning', icon: Shuffle },
};

const BenchmarkPanel = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [suite, setSuite] = useState(null);
  const [comparison, setComparison] = useState(null);

  const runBenchmark = async () => {
    setLoading(true);
    setError(false);
    try {
      const runResult = await benchmarkAPI.run();
      setSuite(runResult.suite);

      // Real-data comparison: find the most recent prior run against a
      // different strategy so baseline/candidate/improvement reflect
      // actual stored benchmark results, never placeholders.
      const { history } = await benchmarkAPI.getHistory();
      const previous = [...history]
        .reverse()
        .find((h) => h.strategy_id !== runResult.strategy_id && h.benchmark_run_id !== runResult.benchmark_run_id);

      if (previous) {
        const comparisonResult = await benchmarkAPI.compare(previous.benchmark_run_id, runResult.benchmark_run_id);
        setComparison(comparisonResult);
      } else {
        setComparison(null);
      }
    } catch (err) {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  const StatusIcon = comparison ? statusMeta[comparison.status]?.icon || Minus : null;

  return (
    <div className="w-full bg-[#1E293B]/90 border border-slate-700/80 rounded-[14px] p-5 shadow-xl flex flex-col gap-3">
      <div className="flex items-center justify-between pb-3 border-b border-slate-700/60">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <BarChart3 className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-slate-100">Benchmark Status</h4>
            <p className="text-[11px] text-slate-400">Offline, deterministic research quality suite</p>
          </div>
        </div>
        <Button size="sm" variant="secondary" icon={PlayCircle} isLoading={loading} onClick={runBenchmark}>
          Run Benchmark
        </Button>
      </div>

      {error && (
        <p className="text-[11px] text-slate-400 py-1">Benchmark unavailable -- backend unreachable.</p>
      )}

      {!error && !suite && (
        <p className="text-[11px] text-slate-500 py-1">No benchmark has been run yet in this session.</p>
      )}

      {suite && (
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="p-2 rounded-xl bg-slate-900/60 border border-slate-800">
            <span className="text-[10px] text-slate-400 block">Questions</span>
            <span className="font-bold text-slate-200">{suite.benchmark_count}</span>
          </div>
          <div className="p-2 rounded-xl bg-slate-900/60 border border-slate-800">
            <span className="text-[10px] text-slate-400 block">Average Score</span>
            <span className="font-bold text-slate-200">{suite.average_score.toFixed(2)}</span>
          </div>
          <div className="p-2 rounded-xl bg-slate-900/60 border border-slate-800">
            <span className="text-[10px] text-slate-400 block">Passed</span>
            <span className="font-bold text-emerald-400">
              {suite.passed_count} / {suite.benchmark_count}
            </span>
          </div>
          <div className="p-2 rounded-xl bg-slate-900/60 border border-slate-800">
            <span className="text-[10px] text-slate-400 block">Median Score</span>
            <span className="font-bold text-slate-200">{suite.median_score.toFixed(2)}</span>
          </div>
        </div>
      )}

      {comparison && (
        <div className="pt-3 border-t border-slate-700/60 space-y-2">
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="p-2 rounded-xl bg-slate-900/60 border border-slate-800">
              <span className="text-[10px] text-slate-400 block">Baseline</span>
              <span className="font-bold text-slate-200">{comparison.baseline_score.toFixed(2)}</span>
            </div>
            <div className="p-2 rounded-xl bg-slate-900/60 border border-slate-800">
              <span className="text-[10px] text-slate-400 block">Candidate</span>
              <span className="font-bold text-slate-200">{comparison.candidate_score.toFixed(2)}</span>
            </div>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400">
              Improvement:{' '}
              <span className="font-semibold text-slate-200">
                {comparison.improvement_percentage === null
                  ? 'n/a'
                  : `${comparison.improvement_percentage >= 0 ? '+' : ''}${comparison.improvement_percentage.toFixed(2)}%`}
              </span>
            </span>
            <Badge variant={statusMeta[comparison.status]?.variant || 'neutral'} icon={StatusIcon}>
              {comparison.status}
            </Badge>
          </div>
        </div>
      )}
    </div>
  );
};

export default BenchmarkPanel;
