import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Brain, User, Copy, Check, ExternalLink, ShieldCheck, ChevronDown, ChevronUp, Sparkles } from 'lucide-react';
import Badge from './Badge';

/* ── Markdown renderer components ─────────────────────────────────────── */
const mdComponents = {
  // Headings
  h1: ({ children }) => (
    <h1 className="text-lg font-bold text-white mt-3 mb-1.5 border-b border-slate-700 pb-1">{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-base font-semibold text-cyan-300 mt-3 mb-1">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-sm font-semibold text-slate-200 mt-2 mb-0.5">{children}</h3>
  ),

  // Paragraphs
  p: ({ children }) => (
    <p className="mb-2 last:mb-0 leading-relaxed text-slate-100">{children}</p>
  ),

  // Bold & italic
  strong: ({ children }) => (
    <strong className="font-semibold text-white">{children}</strong>
  ),
  em: ({ children }) => (
    <em className="italic text-slate-300">{children}</em>
  ),

  // Ordered / unordered lists
  ul: ({ children }) => (
    <ul className="list-disc list-inside space-y-1 my-2 pl-2 text-slate-200">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="list-decimal list-inside space-y-1 my-2 pl-2 text-slate-200">{children}</ol>
  ),
  li: ({ children }) => (
    <li className="leading-relaxed marker:text-cyan-400">{children}</li>
  ),

  // Inline code
  code: ({ inline, children }) =>
    inline ? (
      <code className="px-1.5 py-0.5 rounded bg-slate-800 text-cyan-300 font-mono text-[12px] border border-slate-700">
        {children}
      </code>
    ) : (
      <code className="block">{children}</code>
    ),

  // Code blocks
  pre: ({ children }) => (
    <pre className="my-3 p-3 rounded-xl bg-slate-900 border border-slate-700 overflow-x-auto font-mono text-[12px] text-slate-200 leading-relaxed">
      {children}
    </pre>
  ),

  // Blockquote
  blockquote: ({ children }) => (
    <blockquote className="my-2 pl-3 border-l-2 border-cyan-500 text-slate-400 italic">{children}</blockquote>
  ),

  // Horizontal rule
  hr: () => <hr className="my-3 border-slate-700" />,

  // Links
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="text-cyan-400 hover:text-cyan-300 underline underline-offset-2 transition-colors"
    >
      {children}
    </a>
  ),

  // Tables (GFM)
  table: ({ children }) => (
    <div className="my-3 overflow-x-auto rounded-xl border border-slate-700">
      <table className="w-full text-xs text-slate-200">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-slate-800 text-slate-300 font-semibold">{children}</thead>,
  tbody: ({ children }) => <tbody className="divide-y divide-slate-700/60">{children}</tbody>,
  tr: ({ children }) => <tr className="hover:bg-slate-800/40 transition-colors">{children}</tr>,
  th: ({ children }) => <th className="px-3 py-2 text-left text-cyan-300">{children}</th>,
  td: ({ children }) => <td className="px-3 py-2">{children}</td>,
};

/* ── Component ─────────────────────────────────────────────────────────── */
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
          className={`p-4 md:p-5 rounded-[16px] text-sm shadow-lg ${
            isAi
              ? 'bg-[#1E293B] border border-slate-700/80 text-slate-100 rounded-tl-none'
              : 'bg-blue-600 text-white rounded-tr-none font-normal leading-relaxed'
          }`}
        >
          {isAi ? (
            /* ── Rendered markdown for AI messages ── */
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
              {message.text}
            </ReactMarkdown>
          ) : (
            /* ── Plain text for user messages ── */
            <div className="whitespace-pre-line font-sans">{message.text}</div>
          )}

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
                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
                      {message.reflectionNotes}
                    </ReactMarkdown>
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
