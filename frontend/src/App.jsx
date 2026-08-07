import React, { useState, useEffect } from 'react';
import { 
  Search, Shield, History, Settings, CheckCircle2, Clock, 
  AlertTriangle, FileText, Database, Activity, Sparkles, Terminal,
  ExternalLink, ArrowRight, RefreshCw, Lock
} from 'lucide-react';

const API_BASE = "http://localhost:8000/api";

export default function App() {
  const [activeTab, setActiveTab] = useState('research');
  const [question, setQuestion] = useState('');
  const [activeRunId, setActiveRunId] = useState(null);
  const [statusData, setStatusData] = useState(null);
  const [resultData, setResultData] = useState(null);
  const [traceData, setTraceData] = useState([]);
  const [historyList, setHistoryList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Sample prompt default
  const samplePrompt = "Compare the impact of generative AI on software developer productivity using recent research papers and industry evidence.";

  // Fetch History
  const loadHistory = async () => {
    try {
      const res = await fetch(`${API_BASE}/history`);
      if (res.ok) {
        const data = await res.json();
        setHistoryList(data);
      }
    } catch (err) {
      console.error("Failed to load history:", err);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  // Poll Active Run
  useEffect(() => {
    if (!activeRunId) return;

    const interval = setInterval(async () => {
      try {
        const [resStatus, resTrace] = await Promise.all([
          fetch(`${API_BASE}/research/${activeRunId}`),
          fetch(`${API_BASE}/research/${activeRunId}/trace`)
        ]);

        if (resStatus.ok) {
          const sData = await resStatus.json();
          setStatusData(sData);

          if (sData.status === 'completed' || sData.status === 'failed') {
            clearInterval(interval);
            setLoading(false);
            // Fetch final result
            const resResult = await fetch(`${API_BASE}/research/${activeRunId}/result`);
            if (resResult.ok) {
              const rData = await resResult.json();
              setResultData(rData);
            }
            loadHistory();
          }
        }

        if (resTrace.ok) {
          const tData = await resTrace.json();
          setTraceData(tData);
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [activeRunId]);

  const handleStartResearch = async (qText) => {
    const targetQ = qText || question;
    if (!targetQ.trim()) return;

    setLoading(true);
    setErrorMsg('');
    setStatusData(null);
    setResultData(null);
    setTraceData([]);

    try {
      const res = await fetch(`${API_BASE}/research`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: targetQ })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to start research run');
      }

      const data = await res.json();
      setActiveRunId(data.run_id);
      setStatusData(data);
      setActiveTab('research');
    } catch (err) {
      setLoading(false);
      setErrorMsg(err.message);
    }
  };

  const handleSelectRunFromHistory = async (runId) => {
    setActiveRunId(runId);
    setLoading(false);
    setActiveTab('research');

    try {
      const [resStatus, resResult, resTrace] = await Promise.all([
        fetch(`${API_BASE}/research/${runId}`),
        fetch(`${API_BASE}/research/${runId}/result`),
        fetch(`${API_BASE}/research/${runId}/trace`)
      ]);

      if (resStatus.ok) setStatusData(await resStatus.json());
      if (resResult.ok) setResultData(await resResult.json());
      if (resTrace.ok) setTraceData(await resTrace.json());
    } catch (err) {
      console.error("Error loading historical run:", err);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header Bar */}
      <header style={{
        padding: '16px 32px',
        borderBottom: '1px solid var(--border-subtle)',
        background: 'rgba(10, 13, 20, 0.8)',
        backdropFilter: 'blur(12px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        sticky: 'top'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, #6366f1, #06b6d4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 16px rgba(99, 102, 241, 0.4)'
          }}>
            <Sparkles size={22} color="white" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.25rem', fontWeight: 700, letterSpacing: '-0.02em' }}>EvoResearch AE-02</h1>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Phase 1 — Observable Autonomous Research MVP v0.1</p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav style={{ display: 'flex', gap: '8px', background: 'rgba(255, 255, 255, 0.04)', padding: '4px', borderRadius: '12px' }}>
          <button 
            onClick={() => setActiveTab('research')}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              border: 'none',
              background: activeTab === 'research' ? 'var(--accent-primary)' : 'transparent',
              color: activeTab === 'research' ? 'white' : 'var(--text-muted)',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              transition: 'all 0.2s'
            }}>
            <Search size={16} /> Research
          </button>
          <button 
            onClick={() => setActiveTab('history')}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              border: 'none',
              background: activeTab === 'history' ? 'var(--accent-primary)' : 'transparent',
              color: activeTab === 'history' ? 'white' : 'var(--text-muted)',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              transition: 'all 0.2s'
            }}>
            <History size={16} /> History ({historyList.length})
          </button>
          <button 
            onClick={() => setActiveTab('settings')}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              border: 'none',
              background: activeTab === 'settings' ? 'var(--accent-primary)' : 'transparent',
              color: activeTab === 'settings' ? 'white' : 'var(--text-muted)',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              transition: 'all 0.2s'
            }}>
            <Settings size={16} /> Settings
          </button>
        </nav>
      </header>

      {/* Main Workspace */}
      <main style={{ flex: 1, padding: '32px', maxWidth: '1400px', margin: '0 auto', width: '100%' }}>
        {activeTab === 'research' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '24px' }}>
            {/* Left Column: Input + Final Answer / State */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              
              {/* Question Input Card */}
              <div className="glass-panel" style={{ padding: '24px' }}>
                <h2 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Search size={18} color="var(--accent-cyan)" /> Autonomous Research Query
                </h2>
                <div style={{ display: 'flex', gap: '12px', marginBottom: '12px' }}>
                  <input 
                    type="text" 
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="Ask a complex research question..."
                    style={{
                      flex: 1,
                      background: 'rgba(0, 0, 0, 0.4)',
                      border: '1px solid var(--border-subtle)',
                      padding: '12px 16px',
                      borderRadius: '10px',
                      color: 'white',
                      fontSize: '0.95rem',
                      outline: 'none'
                    }}
                    onKeyDown={(e) => e.key === 'Enter' && handleStartResearch()}
                  />
                  <button 
                    onClick={() => handleStartResearch()}
                    disabled={loading || !question.trim()}
                    className="btn-primary"
                  >
                    {loading ? <RefreshCw className="animate-spin" size={18} /> : <Sparkles size={18} />}
                    {loading ? 'Researching...' : 'Start Run'}
                  </button>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>Quick Demo Prompt:</span>
                  <button 
                    onClick={() => { setQuestion(samplePrompt); handleStartResearch(samplePrompt); }}
                    style={{
                      background: 'rgba(99, 102, 241, 0.1)',
                      border: '1px solid rgba(99, 102, 241, 0.25)',
                      color: '#a5b4fc',
                      padding: '4px 10px',
                      borderRadius: '6px',
                      fontSize: '0.75rem',
                      cursor: 'pointer'
                    }}>
                    Use Productivity Demo Query
                  </button>
                </div>

                {errorMsg && (
                  <div style={{ marginTop: '12px', padding: '10px 14px', background: 'rgba(244, 63, 94, 0.15)', border: '1px solid var(--accent-rose)', borderRadius: '8px', color: '#fda4af', fontSize: '0.85rem' }}>
                    {errorMsg}
                  </div>
                )}
              </div>

              {/* Status Header / Progress Overview */}
              {statusData && (
                <div className="glass-panel" style={{ padding: '20px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <div>
                      <span className={`badge badge-${statusData.status}`}>
                        {statusData.status}
                      </span>
                      <span style={{ marginLeft: '12px', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                        Run ID: <code style={{ color: 'var(--accent-cyan)' }}>{statusData.run_id.slice(0, 8)}</code>
                      </span>
                    </div>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>
                      Sources gathered: <strong>{statusData.source_count}</strong>
                    </span>
                  </div>

                  <p style={{ fontSize: '0.9rem', color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Activity size={16} color="var(--accent-amber)" /> Active Step: {statusData.current_step}
                  </p>
                </div>
              )}

              {/* Report / Answer Display */}
              {resultData && resultData.answer && (
                <div className="glass-panel" style={{ padding: '28px', borderLeft: '4px solid var(--accent-emerald)' }}>
                  <h3 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', color: '#6ee7b7' }}>
                    <CheckCircle2 size={20} /> Verified Synthesis & Findings
                  </h3>

                  <div style={{
                    whiteSpace: 'pre-wrap',
                    lineHeight: '1.6',
                    color: '#e2e8f0',
                    fontSize: '0.95rem',
                    background: 'rgba(0,0,0,0.25)',
                    padding: '20px',
                    borderRadius: '12px',
                    border: '1px solid var(--border-subtle)'
                  }}>
                    {resultData.answer}
                  </div>

                  {/* Sources List */}
                  <div style={{ marginTop: '24px' }}>
                    <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Database size={16} /> Normalized Evidence Sources ({resultData.sources.length})
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {resultData.sources.map((src, i) => (
                        <div key={src.id || i} style={{ padding: '12px 16px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-subtle)', borderRadius: '8px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <a href={src.url} target="_blank" rel="noreferrer" style={{ color: '#818cf8', fontWeight: 600, fontSize: '0.9rem', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '4px' }}>
                              {src.title} <ExternalLink size={12} />
                            </a>
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>{src.publisher}</span>
                          </div>
                          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '4px' }}>{src.description}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Right Column: Real-Time Event Trace & Security Logs */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              
              {/* Security Boundary Monitor */}
              {resultData && resultData.security_events && resultData.security_events.length > 0 && (
                <div className="glass-panel" style={{ padding: '20px', borderLeft: '4px solid var(--accent-rose)' }}>
                  <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#fda4af', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Shield size={18} /> Untrusted Security Boundary
                  </h3>
                  {resultData.security_events.map((sec, idx) => (
                    <div key={idx} style={{ background: 'rgba(244, 63, 94, 0.1)', padding: '10px 12px', borderRadius: '8px', fontSize: '0.8rem', color: '#fecdd3' }}>
                      <div style={{ fontWeight: 600 }}>{sec.event_type}</div>
                      <div style={{ fontFamily: 'var(--font-mono)', marginTop: '4px', fontSize: '0.75rem', color: '#cbd5e1' }}>
                        Snippet: "{sec.snippet}"
                      </div>
                      <div style={{ fontSize: '0.7rem', color: '#94a3b8', marginTop: '4px' }}>Action: {sec.action_taken}</div>
                    </div>
                  ))}
                </div>
              )}

              {/* Structured Agent Trace Timeline */}
              <div className="glass-panel" style={{ padding: '20px', flex: 1, display: 'flex', flexDirection: 'column' }}>
                <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Terminal size={18} color="var(--accent-cyan)" /> Agent Execution Trace
                </h3>

                <div style={{ flex: 1, overflowY: 'auto', maxHeight: '550px', paddingRight: '4px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {traceData.length === 0 ? (
                    <div style={{ textAlign: 'center', color: 'var(--text-dim)', padding: '32px 0', fontSize: '0.85rem' }}>
                      No active trace. Start a research run to view live events.
                    </div>
                  ) : (
                    traceData.map((ev, i) => (
                      <div key={ev.event_id || i} style={{
                        padding: '12px',
                        background: 'rgba(0, 0, 0, 0.3)',
                        borderLeft: `3px solid ${
                          ev.type === 'security_check' ? 'var(--accent-rose)' :
                          ev.type === 'report_generated' ? 'var(--accent-emerald)' : 'var(--accent-primary)'
                        }`,
                        borderRadius: '6px',
                        fontSize: '0.85rem'
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                          <span style={{ fontWeight: 600, color: 'white' }}>{ev.title}</span>
                          <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                            {new Date(ev.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                        <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{ev.message}</p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* History Tab */}
        {activeTab === 'history' && (
          <div className="glass-panel" style={{ padding: '28px' }}>
            <h2 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <History size={20} color="var(--accent-primary)" /> Research History & Previous Runs
            </h2>
            {historyList.length === 0 ? (
              <p style={{ color: 'var(--text-dim)' }}>No previous research runs recorded.</p>
            ) : (
              <div style={{ display: 'grid', gap: '12px' }}>
                {historyList.map((item) => (
                  <div 
                    key={item.run_id}
                    onClick={() => handleSelectRunFromHistory(item.run_id)}
                    style={{
                      padding: '16px 20px',
                      background: 'rgba(255,255,255,0.02)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '12px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: 'pointer',
                      transition: 'all 0.2s'
                    }}
                  >
                    <div>
                      <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'white' }}>{item.question}</h4>
                      <div style={{ display: 'flex', gap: '16px', marginTop: '6px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        <span>Run ID: <code>{item.run_id.slice(0, 8)}</code></span>
                        <span>Created: {new Date(item.created_at).toLocaleString()}</span>
                        <span>Sources: {item.source_count}</span>
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <span className={`badge badge-${item.status}`}>{item.status}</span>
                      <ArrowRight size={16} color="var(--text-dim)" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Settings Tab */}
        {activeTab === 'settings' && (
          <div className="glass-panel" style={{ padding: '28px' }}>
            <h2 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Settings size={20} color="var(--accent-cyan)" /> Prototype Settings & Module Status
            </h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
              <div style={{ padding: '16px', background: 'rgba(0,0,0,0.2)', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                <h4 style={{ fontSize: '0.9rem', color: 'var(--text-main)', marginBottom: '8px' }}>Phase 1 Status</h4>
                <p style={{ fontSize: '0.8rem', color: 'var(--accent-emerald)' }}>Active & Online (API Endpoint localhost:8000)</p>
              </div>
              <div style={{ padding: '16px', background: 'rgba(0,0,0,0.2)', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                <h4 style={{ fontSize: '0.9rem', color: 'var(--text-main)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Lock size={14} /> Future Phase 2 Modules
                </h4>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>Evidence Graph UI, Verification Engine, Self-evolving Strategy (Disabled for Phase 1 MVP)</p>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
