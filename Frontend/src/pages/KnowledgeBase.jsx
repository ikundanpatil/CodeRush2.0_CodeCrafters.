import React, { useState } from 'react';
import { Database, Search, PlusCircle, Sparkles, Tag, Calendar, Layers, ShieldCheck, Code } from 'lucide-react';
import { useResearch } from '../context/ResearchContext';
import Button from '../components/Button';
import Input from '../components/Input';
import Badge from '../components/Badge';
import Modal from '../components/Modal';

const KnowledgeBase = () => {
  const { knowledgeList, addKnowledgeChunk } = useResearch();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTag, setSelectedTag] = useState('All');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [selectedCard, setSelectedCard] = useState(null);

  // Form State
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newTags, setNewTags] = useState('AI, Vector, Custom');
  const [newDomain, setNewDomain] = useState('Custom Context');

  const allTags = ['All', 'AI', 'LLM', 'Research', 'Agents', 'Vector', 'RAG', 'Benchmark'];

  const filteredItems = knowledgeList.filter((item) => {
    const matchesSearch =
      item.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesTag = selectedTag === 'All' || item.tags.includes(selectedTag);
    return matchesSearch && matchesTag;
  });

  const handleAddSubmit = (e) => {
    e.preventDefault();
    if (!newTitle.trim() || !newDesc.trim()) return;

    addKnowledgeChunk({
      title: newTitle,
      description: newDesc,
      tags: newTags,
      domain: newDomain,
    });

    setNewTitle('');
    setNewDesc('');
    setIsAddModalOpen(false);
  };

  return (
    <div className="w-full space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Badge variant="cyan" glow icon={Database}>
              Long-Term Vector Memory (1536-dim)
            </Badge>
          </div>
          <h1 className="text-2xl font-extrabold text-slate-100">Persistent Knowledge Base</h1>
          <p className="text-xs text-slate-400">
            Semantic embeddings stored across autonomous agent reasoning runs.
          </p>
        </div>

        <Button variant="primary" size="md" icon={PlusCircle} onClick={() => setIsAddModalOpen(true)}>
          Add Knowledge Chunk
        </Button>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-[16px] bg-[#1E293B]/70 border border-slate-700/80">
        <div className="w-full sm:w-80">
          <Input
            icon={Search}
            placeholder="Search vector embeddings..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        {/* Tag Chips */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0">
          {allTags.map((tag) => (
            <button
              key={tag}
              onClick={() => setSelectedTag(tag)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                selectedTag === tag
                  ? 'bg-gradient-to-r from-blue-600 to-cyan-500 text-white shadow-md'
                  : 'bg-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              {tag}
            </button>
          ))}
        </div>
      </div>

      {/* Memory Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredItems.map((item) => (
          <div
            key={item.id}
            onClick={() => setSelectedCard(item)}
            className="p-5 rounded-[18px] bg-[#1E293B] border border-slate-700/80 hover:border-cyan-500/50 transition-all shadow-xl hover:shadow-cyan-500/10 flex flex-col justify-between gap-4 cursor-pointer group"
          >
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono text-cyan-400 px-2 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/30">
                  {item.domain}
                </span>
                <Badge variant="success" size="sm">
                  {item.similarityScore} Similarity
                </Badge>
              </div>

              <h3 className="text-base font-bold text-slate-100 group-hover:text-cyan-300 transition-colors leading-snug">
                {item.title}
              </h3>

              <p className="text-xs text-slate-400 leading-relaxed line-clamp-3">{item.description}</p>
            </div>

            <div className="pt-3 border-t border-slate-800 space-y-2">
              {/* Tags */}
              <div className="flex flex-wrap gap-1.5">
                {item.tags.map((t, idx) => (
                  <span key={idx} className="text-[10px] px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 border border-slate-700/60">
                    #{t}
                  </span>
                ))}
              </div>

              <div className="flex items-center justify-between text-[11px] text-slate-500 font-mono">
                <span className="flex items-center gap-1">
                  <Calendar className="w-3 h-3 text-slate-400" />
                  {item.createdDate}
                </span>
                <span>{item.tokens} Tokens</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Add Knowledge Modal */}
      <Modal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        title="Add Custom Knowledge Embedding"
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setIsAddModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" onClick={handleAddSubmit}>
              Store Vector Embedding
            </Button>
          </>
        }
      >
        <form onSubmit={handleAddSubmit} className="space-y-4">
          <Input
            label="Title / Document Heading"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="e.g. Transformer Attention Formulas"
            required
          />

          <Input
            label="Knowledge Domain"
            value={newDomain}
            onChange={(e) => setNewDomain(e.target.value)}
            placeholder="e.g. Deep Learning Architecture"
          />

          <Input
            label="Text Context / Markdown Snippet"
            type="textarea"
            rows={4}
            value={newDesc}
            onChange={(e) => setNewDesc(e.target.value)}
            placeholder="Paste raw research excerpt, latex math formula, or code snippet..."
            required
          />

          <Input
            label="Tags (Comma Separated)"
            value={newTags}
            onChange={(e) => setNewTags(e.target.value)}
            placeholder="AI, Vector, Benchmark"
          />
        </form>
      </Modal>

      {/* View Detail Modal */}
      <Modal
        isOpen={Boolean(selectedCard)}
        onClose={() => setSelectedCard(null)}
        title={selectedCard?.title || 'Knowledge Chunk Details'}
      >
        {selectedCard && (
          <div className="space-y-4 text-xs">
            <div className="flex items-center gap-3">
              <Badge variant="cyan" glow>
                Similarity: {selectedCard.similarityScore}
              </Badge>
              <span className="text-slate-400 font-mono">Domain: {selectedCard.domain}</span>
            </div>

            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-slate-200 leading-relaxed font-sans">
              {selectedCard.description}
            </div>

            <div className="p-3 rounded-xl bg-[#0F172A] border border-slate-800 font-mono text-[11px] text-cyan-300 space-y-1">
              <div>// Vector Embedding Dimensions: 1536-dim (HNSW Graph Index)</div>
              <div>// Hash: 0x8f7a99b24cd01...</div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default KnowledgeBase;
