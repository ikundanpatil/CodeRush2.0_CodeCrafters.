import axios from 'axios';

// Base Axios instance pointing to FastAPI backend
const api = axios.create({
  baseURL: 'http://localhost:8000/api',
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
  startResearch: async (config) => {
    try {
      return await api.post('/research/start', config);
    } catch {
      return { success: true, taskId: 'res_' + Date.now(), status: 'queued', message: 'Autonomous research pipeline initialized.' };
    }
  },
  getStatus: async (taskId) => {
    try {
      return await api.get(`/research/status/${taskId}`);
    } catch {
      return { taskId, step: 'Data Analysis', progress: 68, activeAgents: 4 };
    }
  },
};

export const reportAPI = {
  getReport: async (reportId) => {
    try {
      return await api.get(`/reports/${reportId}`);
    } catch {
      return { id: reportId, title: 'Deep Research Report', confidence: 0.98 };
    }
  },
  downloadPDF: async (reportId) => {
    try {
      return await api.get(`/reports/${reportId}/pdf`, { responseType: 'blob' });
    } catch {
      return new Blob(['Mock PDF Research Report Content'], { type: 'application/pdf' });
    }
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
