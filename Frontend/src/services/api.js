import axios from 'axios';

// Base Axios instance pointing to FastAPI backend. Set VITE_API_BASE_URL in
// production (e.g. Vercel env vars pointing at the Railway backend URL,
// like https://your-app.up.railway.app/api). Falls back to localhost for
// local development so `npm run dev` keeps working with no setup.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor (Inject Auth Bearer Token if available)
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('researchmind_auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.warn('API call failed or backend offline. Falling back to local state.', error.message);
    return Promise.reject(error);
  }
);

// API Service Placeholders ready for FastAPI integration
export const authAPI = {
  login: async (credentials) => {
    try {
      return await api.post('/auth/login', credentials);
    } catch {
      return { success: true, token: 'mock_jwt_token_998877', user: { name: 'Dr. Sarah Connor', email: credentials.email || 'sarah@researchmind.ai', role: 'Principal AI Researcher' } };
    }
  },
  logout: async () => {
    try {
      return await api.post('/auth/logout');
    } catch {
      return { success: true };
    }
  },
};

export const researchAPI = {
  startResearch: async (question) => {
    try {
      const payload = typeof question === 'string' ? { question } : question;
      return await api.post('/research', payload);
    } catch (err) {
      console.error('Failed to start research run:', err);
      throw err;
    }
  },
  getStatus: async (runId) => {
    try {
      return await api.get(`/research/${runId}`);
    } catch (err) {
      console.error('Failed to fetch run status:', err);
      throw err;
    }
  },
  getResult: async (runId) => {
    try {
      return await api.get(`/research/${runId}/result`);
    } catch (err) {
      console.error('Failed to fetch run result:', err);
      throw err;
    }
  },
  getTrace: async (runId) => {
    try {
      return await api.get(`/research/${runId}/trace`);
    } catch (err) {
      console.error('Failed to fetch run trace:', err);
      throw err;
    }
  },
  getHistory: async () => {
    try {
      return await api.get('/history');
    } catch (err) {
      console.error('Failed to fetch research history:', err);
      throw err;
    }
  },
  // Phase 10 additions -- same "throw on failure, never fabricate" contract
  // as the calls above (and as policyAPI/benchmarkAPI): the voice UI must
  // show a real error/placeholder state, never invent a value.
  cancelResearch: async (runId) => {
    try {
      return await api.post(`/research/${runId}/cancel`);
    } catch (err) {
      console.error('Failed to cancel research run:', err);
      throw err;
    }
  },
  getQuality: async (runId) => {
    try {
      return await api.get(`/research/${runId}/quality`);
    } catch (err) {
      console.error('Failed to fetch research quality:', err);
      throw err;
    }
  },
  getIterations: async (runId) => {
    try {
      return await api.get(`/research/${runId}/iterations`);
    } catch (err) {
      console.error('Failed to fetch research iterations:', err);
      throw err;
    }
  },
  getEvidenceGraph: async (runId) => {
    try {
      return await api.get(`/evidence/graph/${runId}`);
    } catch (err) {
      console.error('Failed to fetch evidence graph:', err);
      throw err;
    }
  },
  // Part G: richer history than /history -- includes quality, verification
  // status and report availability, all real backend values.
  getResearchHistory: async () => {
    return await api.get('/research/history');
  },
  getResearchHistoryItem: async (runId) => {
    return await api.get(`/research/history/${runId}`);
  },
};

// Triggers a real browser download from an already-fetched Blob.
const downloadBlob = (blob, filename) => {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

// Part F/H/O: the ONE authoritative report path. The previous
// `/reports/{id}` + `/reports/{id}/pdf` endpoints never existed on the
// backend and their catch-blocks fabricated a fake report object and a
// text blob mislabeled as application/pdf -- both removed. These call the
// real endpoints and throw (no fake fallback) so the UI can show a real
// error instead of fake research data.
export const reportAPI = {
  getRunReport: async (runId) => {
    return await api.get(`/research/${runId}/report`);
  },
  downloadRunPDF: async (runId) => {
    const blob = await api.get(`/research/${runId}/report/pdf`, { responseType: 'blob' });
    downloadBlob(blob, `evoresearch-${runId}.pdf`);
    return blob;
  },
  exportRunJSON: async (runId) => {
    const data = await api.get(`/research/${runId}/export/json`);
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    downloadBlob(blob, `evoresearch-${runId}.json`);
    return data;
  },
  getShareView: async (runId) => {
    return await api.get(`/research/${runId}/share`);
  },
};

// Part C - Conversational research. No mock fallback: a failed call must
// surface as an error, never as fabricated conversation content.
export const conversationAPI = {
  create: async (message) => {
    return await api.post('/conversations', { message });
  },
  list: async () => {
    return await api.get('/conversations');
  },
  get: async (sessionId) => {
    return await api.get(`/conversations/${sessionId}`);
  },
  sendMessage: async (sessionId, message) => {
    return await api.post(`/conversations/${sessionId}/messages`, { message });
  },
  remove: async (sessionId) => {
    return await api.delete(`/conversations/${sessionId}`);
  },
};

// Part I - User feedback / answer rating.
export const feedbackAPI = {
  submit: async (runId, { helpful, rating, comment } = {}) => {
    return await api.post(`/research/${runId}/feedback`, { helpful, rating, comment });
  },
  list: async (runId) => {
    return await api.get(`/research/${runId}/feedback`);
  },
};

// Phase 8 - Safety / Policy Engine. Deliberately has NO mock fallback: this
// is security status, so if the backend is unreachable the UI must show
// "unavailable", never a fabricated ALLOW/BLOCK decision.
export const policyAPI = {
  getStatus: async () => {
    return await api.get('/policy/status');
  },
  check: async (payload) => {
    return await api.post('/policy/check', payload);
  },
};

// Phase 9 - Benchmarks + Improvement Tests. No mock fallback, same reasoning
// as policyAPI: these are measured results, never fabricated placeholders.
export const benchmarkAPI = {
  run: async (strategyId) => {
    return await api.post('/benchmark/run', strategyId ? { strategy_id: strategyId } : {});
  },
  getRun: async (benchmarkRunId) => {
    return await api.get(`/benchmark/${benchmarkRunId}`);
  },
  getResults: async (benchmarkRunId) => {
    return await api.get(`/benchmark/${benchmarkRunId}/results`);
  },
  compare: async (baselineRunId, candidateRunId) => {
    return await api.post('/benchmark/compare', {
      baseline_run_id: baselineRunId,
      candidate_run_id: candidateRunId,
    });
  },
  getHistory: async () => {
    return await api.get('/benchmark/history/list');
  },
};

export const knowledgeAPI = {
  getKnowledgeItems: async (query = '') => {
    try {
      return await api.get('/knowledge', { params: { q: query } });
    } catch {
      return [];
    }
  },
  addKnowledgeChunk: async (chunk) => {
    try {
      return await api.post('/knowledge', chunk);
    } catch {
      return { success: true, id: 'kn_' + Date.now(), ...chunk };
    }
  },
};

export default api;
