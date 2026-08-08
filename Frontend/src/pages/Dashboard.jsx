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
  Zap,
  Bot,
} from 'lucide-react';
import { useResearch } from '../context/ResearchContext';
import ChatBubble from '../components/ChatBubble';
import AgentStatusCard from '../components/AgentStatusCard';
import PolicyStatusCard from '../components/PolicyStatusCard';
import BenchmarkPanel from '../components/BenchmarkPanel';
import Button from '../components/Button';
import StatCard from '../components/StatCard';
import { promptSuggestions, userProfile } from '../utils/dummyData';

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

  const firstName = userProfile.name.split(' ').slice(-1)[0];

  return (
    <div className="w-full flex flex-col gap-6">
      {/* Welcome Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Welcome back, {firstName}!</h1>
        <p className="text-sm text-slate-500 mt-0.5">Here's your autonomous research overview.</p>
      </div>

      {/* Stat Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          label="Research Runs"
          value={userProfile.stats.totalResearch}
          icon={Bot}
          trend="+3.1%"
          trendDirection="up"
          dark
        />
        <StatCard
          label="Reports Generated"
          value={userProfile.stats.reportsGenerated}
          icon={FileText}
          trend="+1.8%"
          trendDirection="up"
        />
        <StatCard
          label="Knowledge Base Items"
          value={userProfile.stats.knowledgeItems}
          icon={Database}
          trend="+2.4%"
          trendDirection="up"
        />
      </div>

      <div className="w-full grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* CENTER COLUMN: ChatGPT/Perplexity Style Interface */}
        <div className="lg:col-span-8 flex flex-col h-[calc(100vh-16rem)] bg-white border border-slate-200 rounded-[20px] shadow-sm overflow-hidden">
          {/* Chat Scrollable Container */}
          <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
            {/* Hero Welcome Message */}
            <div className="text-center py-6 space-y-3 max-w-xl mx-auto">
              <div className="inline-flex p-3 rounded-2xl bg-slate-50 border border-slate-200">
                <Sparkles className="w-8 h-8 text-slate-900" />
              </div>
              <h2 className="text-2xl md:text-3xl font-extrabold text-slate-900 tracking-tight">
                How can ResearchMind AI help your research today?
              </h2>
              <p className="text-xs md:text-sm text-slate-500">
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
                      className="p-4 rounded-[16px] bg-white border border-slate-200 hover:border-slate-300 hover:bg-slate-50 transition-all text-left group flex flex-col justify-between gap-2 shadow-sm cursor-pointer"
                    >
                      <div className="flex items-center justify-between">
                        <span className="p-2 rounded-xl bg-slate-100 group-hover:bg-slate-900 group-hover:text-white text-slate-600 transition-colors">
                          <IconComp className="w-4 h-4" />
                        </span>
                        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 px-2 py-0.5 rounded bg-slate-100">
                          {card.depth}
                        </span>
                      </div>
                      <div>
                        <h4 className="text-xs font-bold text-slate-800 group-hover:text-slate-900 transition-colors">
                          {card.title}
                        </h4>
                        <p className="text-[11px] text-slate-500 leading-snug mt-1">{card.description}</p>
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
          <div className="p-4 bg-slate-50/80 border-t border-slate-200 space-y-3">
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
                className="w-full bg-white border border-slate-200 rounded-[16px] pl-4 pr-12 py-3 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-slate-400 focus:ring-1 focus:ring-slate-300 resize-none transition-all shadow-sm"
              />
              <button
                type="submit"
                disabled={!inputText.trim()}
                className="absolute right-3 bottom-4.5 p-2 rounded-xl bg-slate-900 text-white disabled:opacity-40 disabled:cursor-not-allowed hover:scale-105 transition-transform shadow-md cursor-pointer"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>

            {/* Quick Input Toolbar */}
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setWebSearchEnabled(!webSearchEnabled)}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs transition-colors cursor-pointer ${
                    webSearchEnabled
                      ? 'bg-sky-50 border-sky-200 text-sky-600 font-medium'
                      : 'bg-white border-slate-200 text-slate-500'
                  }`}
                >
                  <Globe className="w-3.5 h-3.5" />
                  <span>Web Search: {webSearchEnabled ? 'ON' : 'OFF'}</span>
                </button>

                <button
                  type="button"
                  className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-white border border-slate-200 hover:bg-slate-100 text-slate-600 transition-colors cursor-pointer"
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
    </div>
  );
};

export default Dashboard;
