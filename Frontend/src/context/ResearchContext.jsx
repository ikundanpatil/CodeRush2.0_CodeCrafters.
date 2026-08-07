import React, { createContext, useContext, useState, useEffect } from 'react';
import { agentSteps, sampleChatHistory, researchHistory, knowledgeItems, aiModels, mockReport } from '../utils/dummyData';
import { researchAPI } from '../services/api';

const ResearchContext = createContext();

export const ResearchProvider = ({ children }) => {
  const [selectedModel, setSelectedModel] = useState(aiModels[0]);
  const [activeResearch, setActiveResearch] = useState({
    topic: 'Self-Evolving Autonomous Research Agent Systems',
    goal: 'Market & Tech Analysis',
    depth: 'Expert',
    sources: ['Websites', 'GitHub', 'Research Papers', 'News', 'Documentation'],
    outputFormat: 'Report',
  });
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

  // Poll backend run if activeRunId set
  useEffect(() => {
    if (!activeRunId) return;

    const interval = setInterval(async () => {
      try {
        const [statusRes, resultRes, traceRes] = await Promise.all([
          researchAPI.getStatus(activeRunId),
          researchAPI.getResult(activeRunId).catch(() => null),
          researchAPI.getTrace(activeRunId).catch(() => [])
        ]);

        if (statusRes && statusRes.status === 'completed') {
          clearInterval(interval);
          if (resultRes && resultRes.answer) {
            setCurrentReport({
              id: activeRunId,
              title: statusRes.question,
              executiveSummary: resultRes.answer,
              keyFindings: resultRes.evidence.map(e => e.claim || e.passage),
              methodology: "Multi-agent search, security boundary scanning, evidence normalization.",
              sources: resultRes.sources.map(s => ({ title: s.title, url: s.url, relevance: `${Math.round(s.relevance * 100)}%` })),
              confidenceScore: 0.98,
              generatedAt: resultRes.completed_at || new Date().toISOString()
            });
          }
        }
      } catch (e) {
        console.error('Error polling backend run', e);
      }
    }, 1200);

    return () => clearInterval(interval);
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

    // Trigger backend API
    try {
      const runRes = await researchAPI.startResearch(config.topic);
      if (runRes && runRes.run_id) {
        setActiveRunId(runRes.run_id);
      }
    } catch (e) {
      console.warn('Backend startResearch call fallback:', e);
    }

    // Reset steps animation state
    const resetSteps = agentSteps.map((s, idx) => ({
      ...s,
      status: idx < 3 ? 'completed' : idx === 3 ? 'active' : 'pending',
    }));
    setLiveSteps(resetSteps);
  };

  // Add message to chat thread
  const addChatMessage = (text) => {
    const userMsg = {
      id: 'msg-' + Date.now(),
      sender: 'user',
      text,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setChatMessages((prev) => [...prev, userMsg]);

    setTimeout(() => {
      const aiReply = {
        id: 'msg-ai-' + Date.now(),
        sender: 'ai',
        text: `ResearchMind AI has analyzed your input regarding **${text}**.\n\nKey finding: Our multi-agent swarm cross-referenced 18 web domains and 6 code repositories. Would you like me to compile this into a full PDF Executive Report?`,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        sources: [
          { name: 'DeepSeek Research', url: 'https://deepseek.com', score: '98%' },
          { name: 'Paper Digest', url: 'https://arxiv.org', score: '96%' },
        ],
        confidence: 0.978,
      };
      setChatMessages((prev) => [...prev, aiReply]);
    }, 1000);
  };

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
