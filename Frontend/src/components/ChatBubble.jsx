import React, { useState } from 'react';
import { Brain, User, Copy, Check, ExternalLink, ShieldCheck, ChevronDown, ChevronUp, Sparkles } from 'lucide-react';
import Badge from './Badge';

const ChatBubble = ({ message }) => {
  const isAi = message.sender === 'ai';
  const [copied, setCopied] = useState(false);
  const [showReflection, setShowReflection] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`flex gap-3 md:gap-4 my-4 max-w-4xl ${isAi ? 'self-start' : 'self-end flex-row-reverse'}`}>
      {/* Avatar */}
      <div
        className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 shadow-md ${
          isAi
            ? 'bg-gradient-to-tr from-blue-600 via-cyan-500 to-emerald-400 text-white shadow-blue-500/20'
            : 'bg-slate-700 text-slate-200'
        }`}
      >
        {isAi ? <Brain className="w-5 h-5" /> : <User className="w-5 h-5" />}
      </div>

      {/* Message Card */}
      <div className={`flex flex-col gap-2 max-w-3xl ${isAi ? 'items-start' : 'items-end'}`}>
        {/* Header Metadata */}
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span className="font-medium text-slate-300">{isAi ? 'ResearchMind AI Swarm' : 'You'}</span>
          <span>•</span>
          <span>{message.time}</span>
          {isAi && message.confidence && (
            <Badge variant="success" size="sm" icon={ShieldCheck}>
              {(message.confidence * 100).toFixed(1)}% Confidence
            </Badge>
          )}
        </div>

        {/* Text Content Box */}
        <div
          className={`p-4 md:p-5 rounded-[16px] text-sm leading-relaxed shadow-lg ${
            isAi
              ? 'bg-[#1E293B] border border-slate-700/80 text-slate-100 rounded-tl-none'
              : 'bg-blue-600 text-white rounded-tr-none font-normal'
          }`}
        >
          <div className="whitespace-pre-line font-sans">{message.text}</div>

          {/* Sources Section for AI Messages */}
          {isAi && message.sources && message.sources.length > 0 && (
            <div className="mt-4 pt-3 border-t border-slate-700/60 flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold text-slate-400 flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-cyan-400" /> Grounded Sources:
              </span>
              {message.sources.map((src, idx) => (
                <a
                  key={idx}
                  href={src.url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700/80 text-xs text-cyan-400 hover:text-cyan-300 hover:border-cyan-500/50 transition-all"
                >
                  <span>{src.name}</span>
                  <span className="text-[10px] text-emerald-400 font-semibold">{src.score}</span>
                  <ExternalLink className="w-3 h-3 text-slate-400" />
                </a>
              ))}
            </div>
          )}
        </div>

        {/* Reflection Accordion & Action Controls */}
        {isAi && (
          <div className="flex flex-col gap-2 w-full">
            {message.reflectionNotes && (
              <div className="w-full rounded-xl bg-slate-900/60 border border-slate-800 overflow-hidden text-xs">
                <button
                  onClick={() => setShowReflection(!showReflection)}
                  className="w-full flex items-center justify-between p-2.5 text-slate-400 hover:text-slate-200 transition-colors"
                >
                  <span className="flex items-center gap-1.5 font-medium text-cyan-400">
                    <Brain className="w-3.5 h-3.5" /> Agent Reflection Trace
                  </span>
                  {showReflection ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>

                {showReflection && (
                  <div className="p-3 border-t border-slate-800 text-slate-300 bg-slate-950/40 font-mono text-[11px] leading-relaxed">
                    {message.reflectionNotes}
                  </div>
                )}
              </div>
            )}

            <div className="flex items-center gap-2 self-start">
              <button
                onClick={handleCopy}
                className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200 px-2 py-1 rounded-md hover:bg-slate-800 transition-colors"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatBubble;
