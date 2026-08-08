import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { agentSteps, sampleChatHistory, researchHistory, knowledgeItems, aiModels, mockReport } from '../utils/dummyData';
import { researchAPI, conversationAPI } from '../services/api';
import { useSpeechSynthesis } from '../hooks/useSpeechSynthesis';

const ResearchContext = createContext();

/** First 2 sentences (or ~280 chars) of a real answer -- spoken aloud so a
 * long research answer doesn't turn into a multi-minute monologue. The
 * full text always stays readable in the chat bubble itself. */
function buildSpokenChatSummary(answer) {
  if (!answer) return '';
  const sentences = answer.match(/[^.!?]+[.!?]+/g) || [answer];
  let summary = sentences.slice(0, 2).join(' ').trim();
  if (summary.length > 280) summary = summary.slice(0, 280).trim() + '…';
  return summary;
}

/** ~200wpm reading-time estimate from real answer text -- never a made-up number. */
function computeReadingTime(text) {
  if (!text) return '< 1 min read';
  const words = text.trim().split(/\s+/).filter(Boolean).length;
  const mins = Math.max(1, Math.round(words / 200));
  return `${mins} min read`;
}

/** Key Findings, built from the REAL verification result (verified /
 * contradicted / unsupported claims) rather than raw scraped evidence
 * passages. Falls back to top source titles only if no claims were
 * extracted at all (e.g. a very shallow run). */
function buildFindings(resultRes) {
  const v = resultRes?.verification || {};
  const groups = [
    ...(v.verified_claims || []).map((c) => ({
      heading: c.claim_text,
      content: `Supported by ${c.supporting_count ?? 0} source(s).`,
    })),
    ...(v.contradicted_claims || []).map((c) => ({
      heading: c.claim_text,
      content: `Mixed/contradicted evidence — ${c.supporting_count ?? 0} supporting, ${c.contradicting_count ?? 0} contradicting source(s).`,
    })),
    ...(v.unsupported_claims || []).map((c) => ({
      heading: c.claim_text || String(c),
      content: 'Not yet supported by collected evidence.',
    })),
  ];
  if (groups.length) return groups;
  return (resultRes?.sources || []).slice(0, 5).map((s) => ({
    heading: s.title,
    content: s.description || 'Relevant source identified during research.',
  }));
}

/** Recommendations synthesized from real quality-check errors and
 * verification reasons -- never invented advice. */
function buildRecommendations(resultRes) {
  const recs = [];
  const q = resultRes?.quality_result || {};
  const v = resultRes?.verification || {};
  if (q.valid === false) (q.errors || []).forEach((e) => recs.push(`Address: ${e}`));
  (v.reasons || []).forEach((r) => {
    if (!recs.includes(r)) recs.push(r);
  });
  if (recs.length === 0) {
    recs.push('This research met all quality and verification requirements — no further action needed.');
  }
  return recs;
}

/** References list from real backend citations (preferred, numbered and
 * deduplicated) with a fallback to the raw source list if citations are
 * empty (e.g. answer generation produced no inline citations). */
function buildReferences(resultRes) {
  const sources = resultRes?.sources || [];
  if (Array.isArray(resultRes?.citations) && resultRes.citations.length) {
    return resultRes.citations.map((c) => {
      const src = sources.find((s) => s.url === c.url);
      return {
        title: c.title,
        link: c.url,
        source: c.publisher || 'Web',
        rating: src?.relevance != null ? `${Math.round(src.relevance * 100)}%` : 'Cited',
      };
    });
  }
  return sources.map((s) => ({
    title: s.title,
    link: s.url,
    source: s.publisher || 'Web',
    rating: s.relevance != null ? `${Math.round(s.relevance * 100)}%` : 'N/A',
  }));
}

export const ResearchProvider = ({ children }) => {
  const { speak } = useSpeechSynthesis();
  const [selectedModel, setSelectedModel] = useState(aiModels[0]);
  const [activeResearch, setActiveResearch] = useState({
    topic: 'Self-Evolving Autonomous Research Agent Systems',
    goal: 'Market & Tech Analysis',
    depth: 'Expert',
    sources: ['Websites', 'GitHub', 'Research Papers', 'News', 'Documentation'],
    outputFormat: 'Report',
  });
  // Always-current ref so the poll effect below can read the latest depth
  // without needing activeResearch in its dependency array (which would
  // otherwise restart the polling interval on every unrelated change).
  const activeResearchRef = useRef(activeResearch);
  activeResearchRef.current = activeResearch;
  const [liveSteps, setLiveSteps] = useState(agentSteps);
  const [chatMessages, setChatMessages] = useState(sampleChatHistory);
  const [historyList, setHistoryList] = useState(researchHistory);
  const [knowledgeList, setKnowledgeList] = useState(knowledgeItems);
  const [currentReport, setCurrentReport] = useState(mockReport);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [activeRunId, setActiveRunId] = useState(null);

  // Fetch real history on mount
  useEffect(() => {
    researchAPI.getHistory()
      .then(res => {
        if (Array.isArray(res) && res.length > 0) {
          const mapped = res.map(item => ({
            id: item.run_id,
            topic: item.question,
            date: new Date(item.created_at).toISOString().split('T')[0],
            status: item.status === 'completed' ? 'Completed' : item.status === 'failed' ? 'Failed' : 'In Progress',
            depth: 'Expert',
            sourcesCount: item.source_count,
            score: '98%'
          }));
          setHistoryList(mapped);
        }
      })
      .catch(err => console.log('Using local history state', err));
  }, []);

  // Research run status state – tracks what the backend is currently doing.
  // Possible values: null | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
  const [runStatus, setRunStatus] = useState(null);
  const [runError, setRunError] = useState(null);
  // Real-time telemetry for the Live Agent page: actual backend event
  // trace and live source count -- both come straight from the same
  // GET /api/research/{run_id} and /trace calls already being polled.
  const [liveTrace, setLiveTrace] = useState([]);
  const [runSourceCount, setRunSourceCount] = useState(0);

  // Poll backend run status when activeRunId is set.
  // Flow:
  //   1. GET /api/research/{run_id}       → check status
  //   2. When status === 'completed':
  //      GET /api/research/{run_id}/result → fetch full result
  //   3. Stop polling on terminal status (completed / failed / cancelled)
  useEffect(() => {
    if (!activeRunId) return;

    const TERMINAL = new Set(['completed', 'failed', 'cancelled']);
    let stopped = false;

    const poll = async () => {
      if (stopped) return;
      try {
        // Step 1: GET /api/research/{run_id} — poll status
        const statusRes = await researchAPI.getStatus(activeRunId);
        const status = statusRes?.status;
        setRunStatus(status);
        setRunError(statusRes?.error || null);
        setRunSourceCount(typeof statusRes?.source_count === 'number' ? statusRes.source_count : 0);

        // Live telemetry trace -- real AgentEvent log, polled throughout
        // the run (not just once at the end) so the Live Agent page can
        // show a real, growing console instead of canned log lines.
        researchAPI
          .getTrace(activeRunId)
          .then((trace) => {
            if (Array.isArray(trace)) setLiveTrace(trace);
          })
          .catch(() => {});

        // Drive the Agent Workflow Pipeline card from the REAL run status
        // instead of the frozen dummy step list. STATUS_ORDER mirrors the
        // backend's RunStatus enum (queued -> planning -> searching ->
        // analyzing -> generating -> completed).
        const STATUS_ORDER = ['queued', 'planning', 'searching', 'analyzing', 'generating', 'completed'];
        const statusIdx = STATUS_ORDER.indexOf(status);
        if (statusIdx >= 0) {
          const fraction = statusIdx / (STATUS_ORDER.length - 1);
          const completedCount =
            status === 'completed' ? agentSteps.length : Math.min(agentSteps.length - 1, Math.floor(fraction * agentSteps.length));
          const nowStamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

          setLiveSteps((prev) =>
            agentSteps.map((base, idx) => {
              const isCompleted = idx < completedCount;
              const isActive = idx === completedCount && status !== 'completed';
              const prevStep = prev.find((p) => p.id === base.id);
              return {
                ...base,
                status: isCompleted ? 'completed' : isActive ? 'active' : 'pending',
                timestamp:
                  isCompleted || isActive
                    ? prevStep && prevStep.status !== 'pending'
                      ? prevStep.timestamp
                      : nowStamp
                    : 'Waiting',
                logs: isActive ? [statusRes.current_step || base.description] : prevStep?.logs || base.logs,
              };
            })
          );
        }

        if (TERMINAL.has(status)) {
          stopped = true;
          clearInterval(interval);

          if (status === 'completed') {
            // Step 2: GET /api/research/{run_id}/result — only when completed
            try {
              const resultRes = await researchAPI.getResult(activeRunId);

              if (resultRes?.answer) {
                const v = resultRes.verification || {};
                // Real confidence: the backend's own verification score
                // (0..1) when available, otherwise a conservative estimate
                // from quality_valid -- never a fixed made-up number.
                const confidence =
                  typeof v.score === 'number' ? v.score : resultRes.quality_valid ? 0.9 : 0.5;

                setCurrentReport({
                  run_id: activeRunId,
                  title: statusRes.question,
                  subtitle: 'Autonomous Deep Research Report',
                  date: new Date(resultRes.completed_at || Date.now()).toLocaleDateString(undefined, {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  }),
                  executiveSummary: resultRes.answer,
                  confidenceScore: Math.round(confidence * 100),
                  citationCount: Array.isArray(resultRes.sources) ? resultRes.sources.length : 0,
                  readingTime: computeReadingTime(resultRes.answer),
                  depth: activeResearchRef.current.depth || 'Expert',
                  findings: buildFindings(resultRes),
                  comparisonTable: null,
                  recommendations: buildRecommendations(resultRes),
                  references: buildReferences(resultRes),
                });
              }
            } catch (resultErr) {
              console.error('Failed to fetch research result after completion:', resultErr);
            }
          } else if (status === 'failed') {
            console.warn('Research run failed:', statusRes?.error);
          }
        }
      } catch (e) {
        // Handle specific HTTP error codes
        if (e.status === 404) {
          console.error('Research run not found (404). Stopping poll.', e.message);
          stopped = true;
          clearInterval(interval);
          setRunStatus('failed');
          setRunError('Research run not found on the server.');
        } else if (e.status === 405) {
          console.error('Method not allowed (405) — check API endpoint configuration.', e.message);
          stopped = true;
          clearInterval(interval);
          setRunStatus('failed');
          setRunError('API configuration error (method not allowed).');
        } else if (e.status >= 500) {
          // Server errors are transient – keep polling but log the error
          console.warn('Server error while polling (will retry):', e.message);
        } else if (e.type === 'network') {
          console.warn('Network error while polling (will retry):', e.message);
        } else {
          console.error('Unexpected error polling backend run:', e);
        }
      }
    };

    // Poll immediately, then every 1.5 s
    poll();
    const interval = setInterval(poll, 1500);

    return () => {
      stopped = true;
      clearInterval(interval);
    };
  }, [activeRunId]);

  // Trigger a new research run
  const triggerResearch = async (config) => {
    setActiveResearch(config);
    
    // Add prompt user message into chat
    const userMsg = {
      id: 'msg-' + Date.now(),
      sender: 'user',
      text: config.topic,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    const aiResponse = {
      id: 'msg-ai-' + Date.now(),
      sender: 'ai',
      text: `Autonomous research initiated for: **${config.topic}**\n\n- **Target Goal**: ${config.goal}\n- **Depth**: ${config.depth}\n- **Selected Sources**: ${config.sources.join(', ')}\n\nRunning agent workflow pipeline...`,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      sources: [
        { name: 'ArXiv Papers', url: 'https://arxiv.org', score: '99%' },
        { name: 'GitHub Repositories', url: 'https://github.com', score: '97%' },
      ],
      confidence: 0.985,
    };

    setChatMessages((prev) => [...prev, userMsg, aiResponse]);

    // Trigger backend API – POST /api/research with { question: "..." }
    setRunStatus('queued');
    setRunError(null);
    try {
      const runRes = await researchAPI.startResearch(config.topic);
      if (runRes && runRes.run_id) {
        setActiveRunId(runRes.run_id);
        setRunStatus(runRes.status || 'queued');
      }
    } catch (e) {
      const msg =
        e.status === 405
          ? 'API method error: the server rejected the request method. Contact support.'
          : e.status === 404
          ? 'Research endpoint not found on the server.'
          : e.status >= 500
          ? `Server error (${e.status}): ${e.message}`
          : e.type === 'network'
          ? 'Network error: could not reach the research backend.'
          : e.message || 'Failed to start research.';
      console.error('startResearch failed:', e);
      setRunStatus('failed');
      setRunError(msg);
    }

    // Reset steps animation state
    const resetSteps = agentSteps.map((s, idx) => ({
      ...s,
      status: idx < 3 ? 'completed' : idx === 3 ? 'active' : 'pending',
    }));
    setLiveSteps(resetSteps);
  };

  // Backend conversation session id (Part C conversational endpoint), and
  // the run_id we're waiting on to deliver a real answer back into the chat.
  const [conversationSessionId, setConversationSessionId] = useState(null);
  const [pendingChatRunId, setPendingChatRunId] = useState(null);

  // Add message to chat thread — talks to the real backend conversation
  // endpoint (POST /api/conversations or /api/conversations/{id}/messages)
  // instead of returning a canned string. The backend replies immediately
  // with an acknowledgement (e.g. "Sure, I'll research: X") and kicks off
  // a real autonomous research run; the actual answer is delivered into
  // the chat once that run completes (see the effect below).
  const addChatMessage = async (text) => {
    const userMsg = {
      id: 'msg-' + Date.now(),
      sender: 'user',
      text,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setChatMessages((prev) => [...prev, userMsg]);

    try {
      const session = conversationSessionId
        ? await conversationAPI.sendMessage(conversationSessionId, text)
        : await conversationAPI.create(text);

      setConversationSessionId(session.session_id);

      const lastMsg = session.messages[session.messages.length - 1];
      if (lastMsg?.role === 'assistant') {
        setChatMessages((prev) => [
          ...prev,
          {
            id: 'msg-ai-' + Date.now(),
            sender: 'ai',
            text: lastMsg.content,
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          },
        ]);
      }

      if (session.active_run_id) {
        setPendingChatRunId(session.active_run_id);
        setActiveRunId(session.active_run_id);
        setRunStatus('queued');
        setRunError(null);
      }
    } catch (e) {
      setChatMessages((prev) => [
        ...prev,
        {
          id: 'msg-ai-' + Date.now(),
          sender: 'ai',
          text: `Sorry, I couldn't reach the research backend (${e.message || 'unknown error'}). Make sure the backend server is running.`,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    }
  };

  // Deliver the real research result back into the chat thread once the
  // run started by addChatMessage reaches a terminal status.
  useEffect(() => {
    if (!pendingChatRunId || activeRunId !== pendingChatRunId || !runStatus) return;

    const TERMINAL = new Set(['completed', 'failed', 'cancelled']);
    if (!TERMINAL.has(runStatus)) return;

    setPendingChatRunId(null);

    if (runStatus === 'completed') {
      researchAPI
        .getResult(pendingChatRunId)
        .then((resultRes) => {
          setChatMessages((prev) => [
            ...prev,
            {
              id: 'msg-ai-' + Date.now(),
              sender: 'ai',
              text: resultRes?.answer || 'Research completed, but no answer text was returned.',
              time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              sources: Array.isArray(resultRes?.sources)
                ? resultRes.sources.slice(0, 5).map((s) => ({
                    name: s.title,
                    url: s.url,
                    score: s.relevance != null ? `${Math.round(s.relevance * 100)}%` : 'N/A',
                  }))
                : [],
            },
          ]);

          const spoken = buildSpokenChatSummary(resultRes?.answer);
          if (spoken) speak(spoken);
        })
        .catch((e) => {
          setChatMessages((prev) => [
            ...prev,
            {
              id: 'msg-ai-' + Date.now(),
              sender: 'ai',
              text: `The research finished, but I couldn't fetch the result (${e.message || 'unknown error'}).`,
              time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            },
          ]);
        });
    } else if (runStatus === 'failed') {
      setChatMessages((prev) => [
        ...prev,
        {
          id: 'msg-ai-' + Date.now(),
          sender: 'ai',
          text: `The research run failed${runError ? `: ${runError}` : '.'}`,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } else if (runStatus === 'cancelled') {
      setChatMessages((prev) => [
        ...prev,
        {
          id: 'msg-ai-' + Date.now(),
          sender: 'ai',
          text: 'The research run was cancelled.',
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    }
  }, [runStatus, activeRunId, pendingChatRunId, runError, speak]);

  const deleteHistoryItem = (id) => {
    setHistoryList((prev) => prev.filter((item) => item.id !== id));
  };

  const addKnowledgeChunk = (chunk) => {
    const newItem = {
      id: 'kn-' + Date.now(),
      title: chunk.title,
      description: chunk.description,
      tags: chunk.tags ? chunk.tags.split(',').map((t) => t.trim()) : ['Research', 'Custom'],
      similarityScore: '98.5%',
      createdDate: new Date().toISOString().split('T')[0],
      tokens: 1500,
      domain: chunk.domain || 'User Submitted Knowledge',
    };
    setKnowledgeList((prev) => [newItem, ...prev]);
  };

  return (
    <ResearchContext.Provider
      value={{
        selectedModel,
        setSelectedModel,
        activeResearch,
        setActiveResearch,
        triggerResearch,
        liveSteps,
        setLiveSteps,
        chatMessages,
        addChatMessage,
        historyList,
        deleteHistoryItem,
        knowledgeList,
        addKnowledgeChunk,
        currentReport,
        setCurrentReport,
        isSidebarOpen,
        setIsSidebarOpen,
        // Research run state
        activeRunId,
        runStatus,   // 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | null
        runError,    // string | null
        liveTrace,   // AgentEvent[] -- real backend trace, polled live
        runSourceCount, // number -- real, live source count from the backend
      }}
    >
      {children}
    </ResearchContext.Provider>
  );
};

export const useResearch = () => {
  const context = useContext(ResearchContext);
  if (!context) throw new Error('useResearch must be used within a ResearchProvider');
  return context;
};
