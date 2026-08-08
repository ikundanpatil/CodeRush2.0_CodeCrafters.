import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useResearchSession } from './useResearchSession';
import { researchAPI } from '../services/api';

vi.mock('../services/api', () => ({
  researchAPI: {
    startResearch: vi.fn(),
    getStatus: vi.fn(),
    getResult: vi.fn(),
    getTrace: vi.fn(),
    getQuality: vi.fn(),
    getIterations: vi.fn(),
    getEvidenceGraph: vi.fn(),
    cancelResearch: vi.fn(),
  },
}));

const baseStatus = { run_id: 'run-1', status: 'searching', current_step: 'Searching', error: null };
const baseResult = {
  run_id: 'run-1', status: 'searching', answer: null, sources: [], evidence: [],
  claim_count: undefined, quality_valid: undefined, iteration_count: undefined, research_decision: null,
};

describe('useResearchSession', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    researchAPI.startResearch.mockResolvedValue({ run_id: 'run-1', status: 'queued' });
    researchAPI.getStatus.mockResolvedValue(baseStatus);
    researchAPI.getResult.mockResolvedValue(baseResult);
    researchAPI.getTrace.mockResolvedValue([]);
    researchAPI.getQuality.mockResolvedValue({ run_id: 'run-1', quality: null });
    researchAPI.getIterations.mockResolvedValue({ run_id: 'run-1', iterations: [] });
    researchAPI.getEvidenceGraph.mockResolvedValue({ research_run_id: 'run-1', nodes: [], edges: [] });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('starts a session by calling the real POST /api/research endpoint', async () => {
    const { result, unmount } = renderHook(() => useResearchSession());

    await act(async () => {
      await result.current.start('Does exercise improve health outcomes?');
    });

    expect(researchAPI.startResearch).toHaveBeenCalledWith('Does exercise improve health outcomes?');
    expect(result.current.session.runId).toBe('run-1');
    expect(researchAPI.getStatus).toHaveBeenCalledWith('run-1');
    unmount();
  });

  it('never fabricates a value for fields the backend has not returned yet', async () => {
    const { result, unmount } = renderHook(() => useResearchSession());

    await act(async () => {
      await result.current.start('Does exercise improve health outcomes?');
    });

    // The mocked /result response has no claim_count/quality_valid/etc. --
    // those must stay null, never default to 0/false.
    expect(result.current.session.claimCount).toBeNull();
    expect(result.current.session.qualityValid).toBeNull();
    expect(result.current.session.iterationCount).toBeNull();
    expect(result.current.session.finalReport).toBeNull();
    unmount();
  });

  it('populates real fields once the backend provides them', async () => {
    researchAPI.getResult.mockResolvedValue({
      ...baseResult,
      answer: 'Real generated report text.',
      sources: [{ id: 's1', title: 'Source', url: 'https://a.com' }],
      claim_count: 4,
      quality_valid: true,
      iteration_count: 2,
    });

    const { result, unmount } = renderHook(() => useResearchSession());
    await act(async () => {
      await result.current.start('Q');
    });

    expect(result.current.session.finalReport).toBe('Real generated report text.');
    expect(result.current.session.claimCount).toBe(4);
    expect(result.current.session.qualityValid).toBe(true);
    expect(result.current.session.iterationCount).toBe(2);
    expect(result.current.session.sourcesFound).toBe(1);
    unmount();
  });

  it('calls the real cancel endpoint', async () => {
    const { result, unmount } = renderHook(() => useResearchSession());
    await act(async () => {
      await result.current.start('Q');
    });
    await act(async () => {
      await result.current.cancel();
    });
    expect(researchAPI.cancelResearch).toHaveBeenCalledWith('run-1');
    unmount();
  });

  it('surfaces a real error instead of a silent fake success when the API call fails', async () => {
    researchAPI.startResearch.mockRejectedValue({ response: { data: { detail: 'Policy prevented this action.' } } });
    const { result, unmount } = renderHook(() => useResearchSession());

    await act(async () => {
      await result.current.start('Q');
    });

    expect(result.current.session.status).toBe('failed');
    expect(result.current.session.error).toBe('Policy prevented this action.');
    unmount();
  });
});
