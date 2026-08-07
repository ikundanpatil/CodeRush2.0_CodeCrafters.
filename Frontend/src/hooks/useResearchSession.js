import { useCallback, useEffect, useRef, useState } from 'react';
import { researchAPI } from '../services/api';
import { EMPTY_SESSION, TERMINAL_STATUSES } from '../research/researchState';

const POLL_INTERVAL_MS = 1500;

/**
 * Drives one research session against the REAL existing backend
 * (POST /api/research, then polls status/result/trace/quality/iterations/
 * evidence-graph -- all existing Phase 1-9 endpoints, nothing new except
 * cancelResearch). Never fabricates a value: any field the backend hasn't
 * returned yet stays null so the UI can show "Calculating..."/"Waiting for
 * data" instead of a fake number.
 */
export function useResearchSession() {
  const [session, setSession] = useState(EMPTY_SESSION);
  const pollHandleRef = useRef(null);
  const runIdRef = useRef(null);

  const stopPolling = useCallback(() => {
    if (pollHandleRef.current) {
      clearInterval(pollHandleRef.current);
      pollHandleRef.current = null;
    }
  }, []);

  const poll = useCallback(async () => {
    const runId = runIdRef.current;
    if (!runId) return;

    const [statusRes, resultRes, traceRes, qualityRes, iterationsRes, graphRes] = await Promise.allSettled([
      researchAPI.getStatus(runId),
      researchAPI.getResult(runId),
      researchAPI.getTrace(runId),
      researchAPI.getQuality(runId),
      researchAPI.getIterations(runId),
      researchAPI.getEvidenceGraph(runId),
    ]);

    setSession((prev) => {
      if (prev.runId !== runId) return prev; // a newer session replaced this one mid-flight

      const next = { ...prev };

      if (statusRes.status === 'fulfilled') {
        next.status = statusRes.value.status;
        next.currentStage = statusRes.value.current_step;
        if (statusRes.value.error) next.error = statusRes.value.error;
      }

      if (resultRes.status === 'fulfilled') {
        const r = resultRes.value;
        next.sources = r.sources ?? next.sources;
        next.sourcesFound = Array.isArray(r.sources) ? r.sources.length : next.sourcesFound;
        next.evidenceCount = Array.isArray(r.evidence) ? r.evidence.length : next.evidenceCount;
        next.claimCount = typeof r.claim_count === 'number' ? r.claim_count : next.claimCount;
        next.qualityValid = typeof r.quality_valid === 'boolean' ? r.quality_valid : next.qualityValid;
        next.iterationCount = typeof r.iteration_count === 'number' ? r.iteration_count : next.iterationCount;
        next.researchDecision = r.research_decision ?? next.researchDecision;
        if (r.answer) next.finalReport = r.answer;
        // Final Completion Phase: real verification result + citations,
        // straight from the backend. Left null until the backend actually
        // provides them -- never defaulted to an empty "verified" state.
        if (r.verification && Object.keys(r.verification).length > 0) next.verification = r.verification;
        if (Array.isArray(r.citations)) next.citations = r.citations;
      }

      if (traceRes.status === 'fulfilled') next.trace = traceRes.value;

      if (qualityRes.status === 'fulfilled' && qualityRes.value.quality) {
        const quality = qualityRes.value.quality;
        next.quality = quality;
        // Same completeness ratio Phase 9's benchmark metrics use
        // (passed checks / total checks) -- derived from real data, not
        // a new invented number.
        const checks = quality.checks || [];
        next.qualityScore = checks.length ? checks.filter((c) => c.passed).length / checks.length : null;
      }

      if (iterationsRes.status === 'fulfilled') {
        const iterations = iterationsRes.value.iterations || [];
        next.gaps = iterations.length ? iterations[iterations.length - 1].gaps || [] : [];
      }

      if (graphRes.status === 'fulfilled') next.evidenceGraph = graphRes.value;

      return next;
    });

    const finished = statusRes.status === 'fulfilled' && TERMINAL_STATUSES.has(statusRes.value.status);
    if (finished) stopPolling();
  }, [stopPolling]);

  const start = useCallback(
    async (question) => {
      stopPolling();
      runIdRef.current = null;
      setSession({ ...EMPTY_SESSION, query: question, loading: true, status: 'queued' });

      try {
        const created = await researchAPI.startResearch(question);
        runIdRef.current = created.run_id;
        setSession((prev) => ({ ...prev, runId: created.run_id, status: created.status, loading: false }));
        await poll();
        pollHandleRef.current = setInterval(poll, POLL_INTERVAL_MS);
      } catch (err) {
        setSession((prev) => ({
          ...prev,
          loading: false,
          status: 'failed',
          error: err?.response?.data?.detail || err?.message || 'Research could not be started.',
        }));
      }
    },
    [poll, stopPolling],
  );

  const cancel = useCallback(async () => {
    const runId = runIdRef.current;
    if (!runId) return;
    try {
      await researchAPI.cancelResearch(runId);
    } catch (err) {
      setSession((prev) => ({
        ...prev,
        error: err?.response?.data?.detail || err?.message || 'Could not stop the research run.',
      }));
    }
  }, []);

  const reset = useCallback(() => {
    stopPolling();
    runIdRef.current = null;
    setSession(EMPTY_SESSION);
  }, [stopPolling]);

  useEffect(() => stopPolling, [stopPolling]);

  return { session, start, cancel, reset };
}
