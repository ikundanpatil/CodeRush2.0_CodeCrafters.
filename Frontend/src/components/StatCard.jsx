import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

const StatCard = ({ label, value, icon: Icon, trend, trendDirection = 'up', dark = false }) => {
  const TrendIcon = trendDirection === 'up' ? TrendingUp : TrendingDown;

  return (
    <div
      className={`rounded-[20px] p-5 flex flex-col justify-between gap-6 shadow-sm border ${
        dark
          ? 'bg-slate-900 border-slate-900 text-white'
          : 'bg-white border-slate-200 text-slate-900'
      }`}
    >
      <div className="flex items-center justify-between">
        <span className={`text-xs font-medium ${dark ? 'text-slate-400' : 'text-slate-500'}`}>{label}</span>
        {Icon && (
          <span className={`p-2 rounded-xl ${dark ? 'bg-white/10 text-white' : 'bg-slate-100 text-slate-600'}`}>
            <Icon className="w-4 h-4" />
          </span>
        )}
      </div>

      <div>
        <div className="text-2xl font-bold tracking-tight">{value}</div>
        {trend && (
          <div className="flex items-center gap-1 mt-1.5 text-xs">
            <span
              className={`flex items-center gap-0.5 font-semibold ${
                trendDirection === 'up' ? 'text-emerald-500' : 'text-red-500'
              }`}
            >
              <TrendIcon className="w-3 h-3" />
              {trend}
            </span>
            <span className={dark ? 'text-slate-500' : 'text-slate-400'}>from last month</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default StatCard;
