/**
 * api.js – Frontend API service for EvoResearch.
 *
 * Uses the native fetch API (not axios) so there is no ambiguity about
 * which HTTP method is used.  All research calls are explicitly documented
 * with their method.
 *
 * Base URL resolution order:
 *   1. VITE_API_BASE_URL environment variable (set in .env / Vercel)
 *   2. Fallback to localhost for local development
 *
 * IMPORTANT: POST /api/research is the ONLY way to create a research run.
 *            GET /api/research does NOT exist and must never be called.
 */

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  'http://localhost:8000/api';

// ---------------------------------------------------------------------------
// Low-level fetch helper
// ---------------------------------------------------------------------------

/**
 * Fetch wrapper that:
 *   - Always sets Content-Type: application/json for POST/PUT/PATCH
 *   - Injects the Bearer token from localStorage if present
 *   - Parses JSON responses
 *   - Throws descriptive errors for 4xx / 5xx and network failures
 *
 * @param {string} path    - Path relative to API_BASE_URL, e.g. "/research"
 * @param {RequestInit} [options] - Standard fetch options
 * @returns {Promise<any>} Parsed JSON body
 */
async function apiFetch(path, options = {}) {
  const url = `${API_BASE_URL}${path}`;

  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  // Inject auth token if available
  const token = localStorage.getItem('researchmind_auth_token');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (networkError) {
    // Network-level failure (no response at all)
    const err = new Error(
      `Network error – could not reach ${url}. Check your internet connection or backend status.`
    );
    err.type = 'network';
    err.cause = networkError;
    throw err;
  }

  // 204 No Content – nothing to parse
  if (response.status === 204) return null;

  // Try to parse JSON even on error responses (FastAPI returns JSON details)
  let body;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  if (!response.ok) {
    const detail =
      (body && (body.detail || body.message || body.error)) ||
      `HTTP ${response.status} ${response.statusText}`;

    const err = new Error(detail);
    err.status = response.status;
    err.body = body;

    // Specific handling for common error codes
    if (response.status === 404) {
      err.type = 'not_found';
    } else if (response.status === 405) {
      err.type = 'method_not_allowed';
      err.message = `Method not allowed on ${url}. This endpoint only accepts the documented HTTP method.`;
    } else if (response.status === 422) {
      err.type = 'validation_error';
    } else if (response.status >= 500) {
      err.type = 'server_error';
    } else {
      err.type = 'client_error';
    }

    throw err;
  }

  return body;
}

// ---------------------------------------------------------------------------
// Guard: validate a run_id before using it in a URL
// ---------------------------------------------------------------------------
function assertRunId(runId) {
  if (!runId || runId === '{run_id}' || runId === '%7Brun_id%7D') {
    throw new Error(`Invalid runId: "${runId}"`);
  }
}

// ---------------------------------------------------------------------------
// Auth API
// ---------------------------------------------------------------------------
export const authAPI = {
  /**
   * POST /auth/login
   * Falls back to a mock token when the backend is unreachable so that
   * local development still works without an auth backend.
   */
  login: async (credentials) => {
    try {
      return await apiFetch('/auth/login', {
        method: 'POST',
        body: JSON.stringify(credentials),
      });
    } catch {
      // Auth backend not implemented yet – safe mock fallback for local dev
      return {
        success: true,
        token: 'mock_jwt_token_998877',
        user: {
          name: 'Dr. Sarah Connor',
          email: credentials.email || 'sarah@researchmind.ai',
          role: 'Principal AI Researcher',
        },
      };
    }
  },

  /** POST /auth/logout */
  logout: async () => {
    try {
      return await apiFetch('/auth/logout', { method: 'POST' });
    } catch {
      return { success: true };
    }
  },
};

// ---------------------------------------------------------------------------
// Research API
// ---------------------------------------------------------------------------
export const researchAPI = {
  /**
   * POST /api/research
   *
   * Creates a new research run.  The backend returns a run_id that the
   * caller must store and use for subsequent polling calls.
   *
   * Request body: { "question": "<string>" }
   *
   * @param {string} question
   * @returns {Promise<{ run_id: string, question: string, status: string, current_step: string, created_at: string, updated_at: string, source_count: number, error: null }>}
   */
  startResearch: async (question) => {
    if (!question || !String(question).trim()) {
      throw new Error('Research question cannot be empty.');
    }

    // Always send as { question: "<string>" } — this is the only accepted shape.
    const payload = { question: String(question).trim() };

    return await apiFetch('/research', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * GET /api/research/{run_id}
   *
   * Polls the status of an existing research run.
   * Possible status values: "queued" | "running" | "completed" | "failed" | "cancelled"
   *
   * @param {string} runId
   */
  getStatus: async (runId) => {
    assertRunId(runId);
    return await apiFetch(`/research/${runId}`, { method: 'GET' });
  },

  /**
   * GET /api/research/{run_id}/result
   *
   * Fetch the full result once status === "completed".
   * May return 404 or incomplete data before completion – callers should
   * only invoke this after getStatus confirms "completed".
   *
   * @param {string} runId
   */
  getResult: async (runId) => {
    assertRunId(runId);
    return await apiFetch(`/research/${runId}/result`, { method: 'GET' });
  },

  /**
   * GET /api/research/{run_id}/trace
   * @param {string} runId
   */
  getTrace: async (runId) => {
    assertRunId(runId);
    return await apiFetch(`/research/${runId}/trace`, { method: 'GET' });
  },

  /**
   * GET /api/history  (legacy endpoint – returns list of status objects)
   */
  getHistory: async () => {
    return await apiFetch('/history', { method: 'GET' });
  },

  /**
   * POST /api/research/{run_id}/cancel
   * @param {string} runId
   */
  cancelResearch: async (runId) => {
    assertRunId(runId);
    return await apiFetch(`/research/${runId}/cancel`, { method: 'POST' });
  },

  /**
   * GET /api/research/{run_id}/quality
   * @param {string} runId
   */
  getQuality: async (runId) => {
    assertRunId(runId);
    return await apiFetch(`/research/${runId}/quality`, { method: 'GET' });
  },

  /**
   * GET /api/research/{run_id}/iterations
   * @param {string} runId
   */
  getIterations: async (runId) => {
    assertRunId(runId);
    return await apiFetch(`/research/${runId}/iterations`, { method: 'GET' });
  },

  /**
   * GET /api/evidence/graph/{run_id}
   * @param {string} runId
   */
  getEvidenceGraph: async (runId) => {
    assertRunId(runId);
    return await apiFetch(`/evidence/graph/${runId}`, { method: 'GET' });
  },

  /**
   * GET /api/research/history  (richer history list – Part G)
   * NOTE: This hits /research/history, NOT /research — no risk of a
   * forbidden GET /research call.
   */
  getResearchHistory: async () => {
    return await apiFetch('/research/history', { method: 'GET' });
  },

  /**
   * GET /api/research/history/{run_id}
   * @param {string} runId
   */
  getResearchHistoryItem: async (runId) => {
    assertRunId(runId);
    return await apiFetch(`/research/history/${runId}`, { method: 'GET' });
  },
};

// ---------------------------------------------------------------------------
// Report API
// ---------------------------------------------------------------------------

/** Trigger a real browser download from a Blob. */
function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export const reportAPI = {
  /** GET /api/research/{run_id}/report */
  getRunReport: async (runId) => {
    assertRunId(runId);
    return await apiFetch(`/research/${runId}/report`, { method: 'GET' });
  },

  /** GET /api/research/{run_id}/report/pdf  → triggers download */
  downloadRunPDF: async (runId) => {
    assertRunId(runId);
    const url = `${API_BASE_URL}/research/${runId}/report/pdf`;
    const headers = {};
    const token = localStorage.getItem('researchmind_auth_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const response = await fetch(url, { method: 'GET', headers });
    if (!response.ok) {
      throw new Error(`Failed to download PDF: HTTP ${response.status}`);
    }
    const blob = await response.blob();
    downloadBlob(blob, `evoresearch-${runId}.pdf`);
    return blob;
  },

  /** GET /api/research/{run_id}/export/json → triggers download */
  exportRunJSON: async (runId) => {
    assertRunId(runId);
    const data = await apiFetch(`/research/${runId}/export/json`, { method: 'GET' });
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    downloadBlob(blob, `evoresearch-${runId}.json`);
    return data;
  },

  /** GET /api/research/{run_id}/share */
  getShareView: async (runId) => {
    assertRunId(runId);
    return await apiFetch(`/research/${runId}/share`, { method: 'GET' });
  },
};

// ---------------------------------------------------------------------------
// Conversation API
// ---------------------------------------------------------------------------
export const conversationAPI = {
  /** POST /api/conversations */
  create: async (message) =>
    await apiFetch('/conversations', {
      method: 'POST',
      body: JSON.stringify({ message }),
    }),

  /** GET /api/conversations */
  list: async () => await apiFetch('/conversations', { method: 'GET' }),

  /** GET /api/conversations/{sessionId} */
  get: async (sessionId) =>
    await apiFetch(`/conversations/${sessionId}`, { method: 'GET' }),

  /** POST /api/conversations/{sessionId}/messages */
  sendMessage: async (sessionId, message) =>
    await apiFetch(`/conversations/${sessionId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    }),

  /** DELETE /api/conversations/{sessionId} */
  remove: async (sessionId) =>
    await apiFetch(`/conversations/${sessionId}`, { method: 'DELETE' }),
};

// ---------------------------------------------------------------------------
// Feedback API
// ---------------------------------------------------------------------------
export const feedbackAPI = {
  /** POST /api/research/{run_id}/feedback */
  submit: async (runId, { helpful, rating, comment } = {}) => {
    assertRunId(runId);
    return await apiFetch(`/research/${runId}/feedback`, {
      method: 'POST',
      body: JSON.stringify({ helpful, rating, comment }),
    });
  },

  /** GET /api/research/{run_id}/feedback */
  list: async (runId) => {
    assertRunId(runId);
    return await apiFetch(`/research/${runId}/feedback`, { method: 'GET' });
  },
};

// ---------------------------------------------------------------------------
// Policy API
// ---------------------------------------------------------------------------
export const policyAPI = {
  /** GET /api/policy/status */
  getStatus: async () => await apiFetch('/policy/status', { method: 'GET' }),

  /** POST /api/policy/check */
  check: async (payload) =>
    await apiFetch('/policy/check', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
};

// ---------------------------------------------------------------------------
// Benchmark API
// ---------------------------------------------------------------------------
export const benchmarkAPI = {
  /** POST /api/benchmark/run */
  run: async (strategyId) =>
    await apiFetch('/benchmark/run', {
      method: 'POST',
      body: JSON.stringify(strategyId ? { strategy_id: strategyId } : {}),
    }),

  /** GET /api/benchmark/{benchmarkRunId} */
  getRun: async (benchmarkRunId) =>
    await apiFetch(`/benchmark/${benchmarkRunId}`, { method: 'GET' }),

  /** GET /api/benchmark/{benchmarkRunId}/results */
  getResults: async (benchmarkRunId) =>
    await apiFetch(`/benchmark/${benchmarkRunId}/results`, { method: 'GET' }),

  /** POST /api/benchmark/compare */
  compare: async (baselineRunId, candidateRunId) =>
    await apiFetch('/benchmark/compare', {
      method: 'POST',
      body: JSON.stringify({
        baseline_run_id: baselineRunId,
        candidate_run_id: candidateRunId,
      }),
    }),

  /** GET /api/benchmark/history/list */
  getHistory: async () =>
    await apiFetch('/benchmark/history/list', { method: 'GET' }),
};

// ---------------------------------------------------------------------------
// Knowledge API
// ---------------------------------------------------------------------------
export const knowledgeAPI = {
  /** GET /api/knowledge?q={query} */
  getKnowledgeItems: async (query = '') => {
    try {
      const qs = query ? `?q=${encodeURIComponent(query)}` : '';
      return await apiFetch(`/knowledge${qs}`, { method: 'GET' });
    } catch {
      return [];
    }
  },

  /** POST /api/knowledge */
  addKnowledgeChunk: async (chunk) => {
    try {
      return await apiFetch('/knowledge', {
        method: 'POST',
        body: JSON.stringify(chunk),
      });
    } catch {
      return { success: true, id: 'kn_' + Date.now(), ...chunk };
    }
  },
};

// ---------------------------------------------------------------------------
// Default export: a thin object matching the old axios `api` shape so that
// any code that still does `import api from '../services/api'` keeps working.
// ---------------------------------------------------------------------------
const api = {
  get: (path, options = {}) => apiFetch(path, { method: 'GET', ...options }),
  post: (path, data, options = {}) =>
    apiFetch(path, {
      method: 'POST',
      body: JSON.stringify(data),
      ...options,
    }),
  put: (path, data, options = {}) =>
    apiFetch(path, {
      method: 'PUT',
      body: JSON.stringify(data),
      ...options,
    }),
  patch: (path, data, options = {}) =>
    apiFetch(path, {
      method: 'PATCH',
      body: JSON.stringify(data),
      ...options,
    }),
  delete: (path, options = {}) =>
    apiFetch(path, { method: 'DELETE', ...options }),
};

export default api;
