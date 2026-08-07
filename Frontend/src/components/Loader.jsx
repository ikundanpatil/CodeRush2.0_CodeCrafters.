import React from 'react';
import { motion } from 'framer-motion';
import { Cpu, Sparkles, Brain } from 'lucide-react';

const Loader = ({ text = 'Autonomous Agent Analyzing...', size = 'md' }) => {
  const containerSizes = {
    sm: 'w-12 h-12',
    md: 'w-24 h-24',
    lg: 'w-36 h-36',
  };

  return (
    <div className="flex flex-col items-center justify-center p-6 space-y-4">
      <div className={`relative ${containerSizes[size]} flex items-center justify-center`}>
        {/* Outer Rotating Orbit Ring 1 */}
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
          className="absolute inset-0 rounded-full border-2 border-dashed border-cyan-500/40"
        />

        {/* Counter Rotating Orbit Ring 2 */}
        <motion.div
          animate={{ rotate: -360 }}
          transition={{ duration: 12, repeat: Infinity, ease: 'linear' }}
          className="absolute inset-2 rounded-full border border-blue-500/30 border-t-cyan-400"
        />

        {/* Pulsing Glowing Center Circle */}
        <motion.div
          animate={{ scale: [0.9, 1.1, 0.9], opacity: [0.7, 1, 0.7] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          className="absolute inset-4 rounded-full bg-gradient-to-tr from-blue-600/30 via-cyan-500/20 to-emerald-500/20 backdrop-blur-md border border-cyan-400/50 shadow-[0_0_30px_rgba(6,182,212,0.4)] flex items-center justify-center"
        >
          <Brain className="w-8 h-8 text-cyan-300 animate-pulse" />
        </motion.div>

        {/* Orbiting Satellite Particle Nodes */}
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
          className="absolute inset-0 flex items-center justify-center"
        >
          <div className="w-2.5 h-2.5 rounded-full bg-cyan-400 shadow-[0_0_10px_#06b6d4] translate-x-10" />
        </motion.div>
      </div>

      {text && (
        <div className="flex items-center gap-2 text-sm font-medium text-slate-300">
          <Sparkles className="w-4 h-4 text-cyan-400 animate-bounce" />
          <span>{text}</span>
        </div>
      )}
    </div>
  );
};

export default Loader;
