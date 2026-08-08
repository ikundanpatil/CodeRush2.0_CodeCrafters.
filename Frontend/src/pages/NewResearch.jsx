import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Sparkles,
  Zap,
  CheckCircle2,
  Globe,
  BookOpen,
  Newspaper,
  FileCode,
  FileCheck,
  Brain,
  Rocket,
} from 'lucide-react';
import GithubIcon from '../components/GithubIcon';
import { useResearch } from '../context/ResearchContext';
import Button from '../components/Button';
import Input from '../components/Input';
import Badge from '../components/Badge';

const NewResearch = () => {
  const navigate = useNavigate();
  const { triggerResearch } = useResearch();

  const [topic, setTopic] = useState(
    'Self-Evolving Autonomous Research Agents: Architecture, Benchmarks & Future Trajectory'
  );
  const [goal, setGoal] = useState('Market & Tech Analysis');
  const [depth, setDepth] = useState('Expert');
  const [selectedSources, setSelectedSources] = useState([
    'Websites',
    'GitHub',
    'Research Papers',
    'News',
    'Documentation',
  ]);
  const [outputFormat, setOutputFormat] = useState('Report');

  const goalOptions = [
    'Market & Tech Analysis',
    'Competitor Benchmarking',
    'Academic Literature Review',
    'Codebase AST Security Audit',
    'Technology Selection Guide',
  ];

  const depthLevels = [
    { id: 'Quick', title: 'Quick Scan', duration: '~30 sec', workers: '2 Workers', desc: 'Fast web digest and key summary' },
    { id: 'Standard', title: 'Standard Audit', duration: '~1 min', workers: '4 Workers', desc: 'Web + ArXiv papers analysis' },
    { id: 'Deep', title: 'Deep Research', duration: '~2.5 min', workers: '6 Workers', desc: 'Scrapes code repos & whitepapers' },
    { id: 'Expert', title: 'Expert Swarm', duration: '~4 min', workers: '8 Swarm Workers', desc: 'Self-reflection & AST parsing' },
  ];

  const sourceItems = [
    { id: 'Websites', name: 'Websites', icon: Globe, count: '40+ Domains' },
    { id: 'GitHub', name: 'GitHub', icon: GithubIcon, count: 'Code & AST' },
    { id: 'Research Papers', name: 'Research Papers', icon: BookOpen, count: 'ArXiv / IEEE' },
    { id: 'News', name: 'News & Blogs', icon: Newspaper, count: 'TechCrunch' },
    { id: 'Documentation', name: 'Documentation', icon: FileCode, count: 'Official Docs' },
  ];

  const outputOptions = ['Report', 'Summary', 'Presentation'];

  const toggleSource = (sourceId) => {
    if (selectedSources.includes(sourceId)) {
      if (selectedSources.length > 1) {
        setSelectedSources(selectedSources.filter((s) => s !== sourceId));
      }
    } else {
      setSelectedSources([...selectedSources, sourceId]);
    }
  };

  const handleStart = (e) => {
    e.preventDefault();
    if (!topic.trim()) return;

    triggerResearch({
      topic,
      goal,
      depth,
      sources: selectedSources,
      outputFormat,
    });

    navigate('/live-research');
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-8 pb-12">
      {/* Page Title */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Badge variant="cyan" glow icon={Sparkles}>
            Configure Autonomous Agent Pipeline
          </Badge>
        </div>
        <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">New Autonomous Research Task</h1>
        <p className="text-sm text-slate-500">
          Set up parameters for your self-evolving research agent. The swarm will plan, search, analyze, and self-correct automatically.
        </p>
      </div>

      {/* Main Form Box */}
      <form onSubmit={handleStart} className="space-y-8 bg-white border border-slate-200 rounded-[20px] p-6 md:p-8 shadow-md">
        {/* 1. Research Topic */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-sm font-bold text-slate-700 uppercase tracking-wider flex items-center gap-2">
              <Brain className="w-4 h-4 text-sky-600" /> 1. Research Topic or Question
            </label>
            <span className="text-xs text-slate-500">Be as specific as possible</span>
          </div>
          <Input
            type="textarea"
            rows={3}
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. Compare Qdrant vs Pinecone on 10M embeddings, latency benchmarks, and pricing..."
            required
          />
        </div>

        {/* 2. Research Goal */}
        <div className="space-y-3">
          <label className="text-sm font-bold text-slate-700 uppercase tracking-wider flex items-center gap-2">
            <Zap className="w-4 h-4 text-sky-600" /> 2. Primary Objective / Goal
          </label>
          <Input
            type="select"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            options={goalOptions}
          />
        </div>

        {/* 3. Research Depth */}
        <div className="space-y-3">
          <label className="text-sm font-bold text-slate-700 uppercase tracking-wider flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-sky-600" /> 3. Research Depth & Swarm Budget
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {depthLevels.map((lvl) => {
              const isSelected = depth === lvl.id;
              return (
                <div
                  key={lvl.id}
                  onClick={() => setDepth(lvl.id)}
                  className={`p-4 rounded-[16px] border transition-all cursor-pointer flex flex-col justify-between gap-3 ${
                    isSelected
                      ? 'bg-slate-900 border-slate-900 text-white ring-2 ring-slate-300 shadow-md'
                      : 'bg-slate-50 border-slate-200 text-slate-500 hover:border-slate-300 hover:bg-slate-100'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className={`font-bold text-sm ${isSelected ? 'text-white' : 'text-slate-700'}`}>{lvl.title}</span>
                    {isSelected && <CheckCircle2 className="w-4 h-4 text-white" />}
                  </div>
                  <p className="text-xs leading-snug">{lvl.desc}</p>
                  <div className={`flex items-center justify-between text-[11px] pt-2 border-t font-mono ${isSelected ? 'border-white/20' : 'border-slate-200'}`}>
                    <span className={isSelected ? 'text-sky-300' : 'text-sky-600'}>{lvl.duration}</span>
                    <span className={isSelected ? 'text-slate-300' : 'text-slate-400'}>{lvl.workers}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* 4. Target Data Sources */}
        <div className="space-y-3">
          <label className="text-sm font-bold text-slate-700 uppercase tracking-wider flex items-center gap-2">
            <Globe className="w-4 h-4 text-sky-600" /> 4. Data Sources to Ingest
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {sourceItems.map((src) => {
              const IconComponent = src.icon;
              const isChecked = selectedSources.includes(src.id);
              return (
                <button
                  type="button"
                  key={src.id}
                  onClick={() => toggleSource(src.id)}
                  className={`p-3.5 rounded-[14px] border text-left transition-all cursor-pointer flex flex-col gap-2 ${
                    isChecked
                      ? 'bg-sky-50 border-sky-300 text-sky-700 shadow-sm'
                      : 'bg-slate-50 border-slate-200 text-slate-500 hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <IconComponent className={`w-4 h-4 ${isChecked ? 'text-sky-600' : 'text-slate-400'}`} />
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => {}}
                      className="rounded border-slate-300 bg-white text-slate-900 focus:ring-slate-400"
                    />
                  </div>
                  <span className="text-xs font-semibold">{src.name}</span>
                  <span className="text-[10px] text-slate-400 font-mono">{src.count}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* 5. Output Format */}
        <div className="space-y-3">
          <label className="text-sm font-bold text-slate-700 uppercase tracking-wider flex items-center gap-2">
            <FileCheck className="w-4 h-4 text-sky-600" /> 5. Target Output Deliverable
          </label>
          <div className="flex flex-wrap gap-4">
            {outputOptions.map((opt) => (
              <label
                key={opt}
                className={`flex items-center gap-2.5 px-5 py-3 rounded-[14px] border text-sm font-semibold cursor-pointer transition-all ${
                  outputFormat === opt
                    ? 'bg-sky-50 border-sky-300 text-sky-700'
                    : 'bg-slate-50 border-slate-200 text-slate-500 hover:border-slate-300'
                }`}
              >
                <input
                  type="radio"
                  name="outputFormat"
                  value={opt}
                  checked={outputFormat === opt}
                  onChange={() => setOutputFormat(opt)}
                  className="text-slate-900 focus:ring-slate-400"
                />
                <span>{opt}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Submit CTA Button */}
        <div className="pt-4 border-t border-slate-200 flex items-center justify-between flex-wrap gap-4">
          <div className="text-xs text-slate-500">
            Estimated execution time: <span className="font-semibold text-sky-600 font-mono">2 min 15 sec</span>
          </div>

          <Button type="submit" variant="primary" size="lg" icon={Rocket}>
            Start Autonomous Research
          </Button>
        </div>
      </form>
    </div>
  );
};

export default NewResearch;
