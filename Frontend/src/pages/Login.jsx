import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Brain, ArrowRight, Lock, Mail, Sparkles, Cpu, Network, CheckCircle2 } from 'lucide-react';
import Button from '../components/Button';
import Input from '../components/Input';
import { authAPI } from '../services/api';

const Login = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('sarah.connor@researchmind.ai');
  const [password, setPassword] = useState('••••••••••••');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    await authAPI.login({ email, password });
    setIsLoading(false);
    navigate('/dashboard');
  };

  return (
    <div className="w-full max-w-6xl grid grid-cols-1 lg:grid-cols-2 gap-8 items-center bg-white border border-slate-200 rounded-[24px] p-6 lg:p-12 shadow-lg">
      {/* Left Form Section */}
      <div className="space-y-8 max-w-md mx-auto w-full">
        {/* Brand Logo */}
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-indigo-500 via-sky-500 to-emerald-400 p-0.5 shadow-md shadow-sky-200 flex items-center justify-center">
            <div className="w-full h-full bg-[#0B0D12] rounded-[14px] flex items-center justify-center">
              <Brain className="w-7 h-7 text-sky-400" />
            </div>
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
              ResearchMind <span className="text-sky-600 text-xs px-2 py-0.5 rounded bg-sky-50 border border-sky-200 font-mono">v2.6</span>
            </h1>
            <p className="text-xs text-slate-500">Autonomous Agent Platform</p>
          </div>
        </div>

        {/* Headings */}
        <div className="space-y-2">
          <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight leading-tight">
            Autonomous Research Intelligence
          </h2>
          <p className="text-sm text-slate-500 leading-relaxed">
            AI agents that search, analyze and generate deep research reports automatically.
          </p>
        </div>

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Work Email Address"
            type="email"
            icon={Mail}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="name@company.com"
            required
          />

          <Input
            label="Password"
            type="password"
            icon={Lock}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            required
          />

          <div className="flex items-center justify-between text-xs">
            <label className="flex items-center gap-2 text-slate-500 cursor-pointer">
              <input type="checkbox" defaultChecked className="rounded border-slate-300 bg-white text-slate-900 focus:ring-slate-400" />
              Remember me for 30 days
            </label>
            <a href="#forgot" className="text-sky-600 hover:underline font-medium">Forgot password?</a>
          </div>

          <Button type="submit" variant="primary" size="lg" className="w-full" isLoading={isLoading} icon={ArrowRight}>
            Log In to Workspace
          </Button>

          <div className="relative py-2 flex items-center justify-center">
            <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-slate-200" /></div>
            <span className="relative bg-white px-3 text-xs text-slate-400 font-mono">OR CONTINUE WITH</span>
          </div>

          <button
            type="button"
            onClick={handleSubmit}
            className="w-full flex items-center justify-center gap-3 px-4 py-3 rounded-[14px] bg-white border border-slate-200 hover:border-slate-300 text-slate-700 text-sm font-semibold transition-all cursor-pointer shadow-sm"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path fill="#EA4335" d="M12 5c1.6 0 3 .6 4.1 1.6l3.1-3.1C17.3 1.7 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.4 9 5 12 5z" />
              <path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.8z" />
              <path fill="#FBBC05" d="M5.6 14.8c-.3-.8-.4-1.8-.4-2.8s.1-2 .4-2.8L1.9 6.3C.7 8.7 0 10.3 0 12s.7 3.3 1.9 5.7l3.7-2.9z" />
              <path fill="#34A853" d="M12 23c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2.4-6.4-5.2L1.9 16C3.7 19.7 7.5 23 12 23z" />
            </svg>
            Google Single Sign-On
          </button>
        </form>

        <p className="text-xs text-center text-slate-500">
          Enterprise Security Standard • AES-256 Vector Encryption
        </p>
      </div>

      {/* Right Side: Animated AI Neural Network Illustration */}
      <div className="relative hidden lg:flex flex-col items-center justify-center p-8 bg-gradient-to-br from-[#111827] via-[#0F172A] to-slate-900 border border-slate-800 rounded-[20px] min-h-[500px] overflow-hidden">
        {/* Ambient Glowing Orbs */}
        <div className="absolute top-1/4 left-1/4 w-48 h-48 rounded-full bg-cyan-500/10 blur-3xl animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-48 h-48 rounded-full bg-blue-600/10 blur-3xl animate-pulse" />

        {/* Central Brain Container */}
        <div className="relative w-64 h-64 flex items-center justify-center">
          {/* Rotating Rings */}
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
            className="absolute inset-0 rounded-full border border-dashed border-cyan-500/30"
          />
          <motion.div
            animate={{ rotate: -360 }}
            transition={{ duration: 15, repeat: Infinity, ease: 'linear' }}
            className="absolute inset-4 rounded-full border border-blue-500/30 border-t-cyan-400"
          />

          {/* Central AI Brain Node */}
          <motion.div
            animate={{ scale: [1, 1.05, 1] }}
            transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
            className="w-24 h-24 rounded-2xl bg-gradient-to-tr from-blue-600 via-cyan-500 to-emerald-400 p-0.5 shadow-[0_0_40px_rgba(6,182,212,0.4)] flex items-center justify-center z-10"
          >
            <div className="w-full h-full bg-[#0F172A] rounded-[14px] flex items-center justify-center">
              <Brain className="w-12 h-12 text-cyan-300 animate-pulse" />
            </div>
          </motion.div>

          {/* Floating Research Nodes */}
          <motion.div
            animate={{ y: [-8, 8, -8] }}
            transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
            className="absolute -top-4 -left-4 p-3 rounded-xl bg-slate-900/90 border border-slate-700/80 text-xs shadow-xl flex items-center gap-2"
          >
            <Cpu className="w-4 h-4 text-cyan-400" />
            <div>
              <p className="font-semibold text-slate-200">ArXiv Papers</p>
              <span className="text-[10px] text-emerald-400">42 Ingested</span>
            </div>
          </motion.div>

          <motion.div
            animate={{ y: [8, -8, 8] }}
            transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
            className="absolute -bottom-4 -right-4 p-3 rounded-xl bg-slate-900/90 border border-slate-700/80 text-xs shadow-xl flex items-center gap-2"
          >
            <Network className="w-4 h-4 text-blue-400" />
            <div>
              <p className="font-semibold text-slate-200">GitHub Repos</p>
              <span className="text-[10px] text-cyan-400">AST Parsed</span>
            </div>
          </motion.div>

          <motion.div
            animate={{ x: [-6, 6, -6] }}
            transition={{ duration: 4.5, repeat: Infinity, ease: 'easeInOut' }}
            className="absolute top-1/2 -right-12 p-2.5 rounded-xl bg-slate-900/90 border border-slate-700/80 text-[11px] shadow-xl flex items-center gap-2"
          >
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span className="text-slate-300">Self-Reflection 99.8%</span>
          </motion.div>
        </div>

        {/* Feature Highlights */}
        <div className="mt-10 text-center space-y-2 z-10 max-w-xs">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5" /> Self-Evolving Reasoner
          </span>
          <p className="text-xs text-slate-400 leading-snug">
            Equipped with reflection loops, vector graph memory, and live automated code execution.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;
