import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Send,
  Building2,
  TrendingUp,
  Database,
  FileText,
  Sparkles,
  Paperclip,
  Globe,
  PlusCircle,
  Zap,
} from 'lucide-react';
import { useResearch } from '../context/ResearchContext';
import ChatBubble from '../components/ChatBubble';
import AgentStatusCard from '../components/AgentStatusCard';
import PolicyStatusCard from '../components/PolicyStatusCard';
import BenchmarkPanel from '../components/BenchmarkPanel';
import Button from '../components/Button';
import { promptSuggestions } from '../utils/dummyData';

const iconComponents = {
  Building2,
  TrendingUp,
  Database,
  FileText,
};

const Dashboard = () => {
  const navigate = useNavigate();
  const { chatMessages, addChatMessage, triggerResearch } = useResearch();
  const [inputText, setInputText] = useState('');
  const [webSearchEnabled, setWebSearchEnabled] = useState(true);

  const handleSend = (e) => {
    e.preventDefault();
    if (!inputText.trim()) return;
    addChatMessage(inputText);
    setInputText('');
  };

  const handleSuggestionClick = (card) => {
    triggerResearch({
      topic: card.title + ': ' + card.description,
      goal: card.category,
      depth: card.depth,
      sources: ['Websites', 'GitHub', 'Research Papers', 'News'],
      outputFormat: 'Report',
    });
    navigate('/live-research');
  };

  return (
    <div className="w-full grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      {/* CENTER COLUMN: ChatGPT/Perplexity Style Interface */}
      <div className="lg:col-span-8 flex flex-col h-[calc(100vh-6rem)] bg-[#1E293B]/70 border border-slate-700/80 rounded-[20px] shadow-2xl overflow-hidden backdrop-blur-md">
        {/* Chat Scrollable Container */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
          {/* Hero Welcome Message */}
          <div className="text-center py-6 space-y-3 max-w-xl mx-auto">
            <div className="inline-flex p-3 rounded-2xl bg-gradient-to-tr from-blue-600/30 via-cyan-500/20 to-emerald-500/20 border border-cyan-400/40 shadow-lg shadow-cyan-500/10">
              <Sparkles className="w-8 h-8 text-cyan-400 animate-pulse" />
            </div>
            <h2 className="text-2xl md:text-3xl font-extrabold text-slate-100 tracking-tight">
              How can ResearchMind AI help your research today?
            </h2>
            <p className="text-xs md:text-sm text-slate-400">
              Enter any technical topic, market audit, or repository link to deploy our autonomous agent swarm.
            </p>
          </div>

          {/* Prompt Suggestion Cards (Show if messages are short) */}
          {chatMessages.length <= 2 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 my-4">
              {promptSuggestions.map((card) => {
                const IconComp = iconComponents[card.icon] || Sparkles;
                return (
                  <button
                    key={card.id}
                    onClick={() => handleSuggestionClick(card)}
                    className="p-4 rounded-[16px] bg-slate-900/60 border border-slate-800 hover:border-cyan-500/50 hover:bg-slate-800/80 transition-all text-left group flex flex-col justify-between gap-2 shadow-md cursor-pointer"
                  >
                    <div className="flex items-center justify-between">
                      <span className="p-2 rounded-xl bg-slate-800 group-hover:bg-cyan-500/20 text-cyan-400 transition-colors">
                        <IconComp className="w-4 h-4" />
                      </span>
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 px-2 py-0.5 rounded bg-slate-800">
                        {card.depth}
                      </span>
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-200 group-hover:text-cyan-300 transition-colors">
                        {card.title}
                      </h4>
                      <p className="text-[11px] text-slate-400 leading-snug mt-1">{card.description}</p>
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          {/* Chat Messages List */}
          <div className="space-y-4">
            {chatMessages.map((msg) => (
              <ChatBubble key={msg.id} message={msg} />
            ))}
          </div>
        </div>

        {/* Bottom Research Input Container */}
        <div className="p-4 bg-[#111827]/80 border-t border-slate-800 space-y-3">
          <form onSubmit={handleSend} className="relative">
            <textarea
              rows={2}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend(e);
                }
              }}
              placeholder="Ask any research question or paste GitHub/ArXiv URL... (Press Enter to submit)"
              className="w-full bg-[#0F172A] border border-slate-700/80 rounded-[16px] pl-4 pr-12 py-3 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/50 resize-none transition-all shadow-inner"
            />
            <button
              type="submit"
              disabled={!inputText.trim()}
              className="absolute right-3 bottom-4.5 p-2 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 text-white disabled:opacity-40 disabled:cursor-not-allowed hover:scale-105 transition-transform shadow-md shadow-cyan-500/20 cursor-pointer"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>

          {/* Quick Input Toolbar */}
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setWebSearchEnabled(!webSearchEnabled)}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs transition-colors cursor-pointer ${
                  webSearchEnabled
                    ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400 font-medium'
                    : 'bg-slate-800 border-slate-700 text-slate-400'
                }`}
              >
                <Globe className="w-3.5 h-3.5" />
                <span>Web Search: {webSearchEnabled ? 'ON' : 'OFF'}</span>
              </button>

              <button
                type="button"
                className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors cursor-pointer"
              >
                <Paperclip className="w-3.5 h-3.5" />
                <span>Attach Whitepaper</span>
              </button>
            </div>

            <Button
              variant="primary"
              size="sm"
              icon={Zap}
              onClick={() => navigate('/new-research')}
            >
              Configure Deep Agent Run
            </Button>
          </div>
        </div>
      </div>

      {/* RIGHT PANEL: Agent Status + Safety/Policy Status + Benchmarks */}
      <div className="lg:col-span-4 space-y-4">
        <AgentStatusCard />
        <PolicyStatusCard />
        <BenchmarkPanel />
      </div>
    </div>
  );
};

export default Dashboard;
