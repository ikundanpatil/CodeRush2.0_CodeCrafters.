import React, { useState } from 'react';
import { Search, Bell, Sparkles, ChevronDown, User, LogOut, Settings as SettingsIcon, Menu } from 'lucide-react';
import { useResearch } from '../context/ResearchContext';
import { aiModels, userProfile } from '../utils/dummyData';
import Badge from './Badge';

const Navbar = () => {
  const { selectedModel, setSelectedModel, isSidebarOpen, setIsSidebarOpen } = useResearch();
  const [showModelDropdown, setShowModelDropdown] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);

  const notifications = [
    { id: 1, text: 'Deep Research Task "Self-Evolving Agents" completed successfully.', time: '2m ago' },
    { id: 2, text: 'Vector index updated with 12 new ArXiv paper embeddings.', time: '1h ago' },
    { id: 3, text: 'Agent Reflection Loop achieved 99.8% citation accuracy.', time: '3h ago' },
  ];

  return (
    <header className="h-16 bg-white/90 backdrop-blur-md border-b border-slate-200 px-4 md:px-6 flex items-center justify-between sticky top-0 z-30">
      {/* Left Search Bar & Mobile Menu Toggle */}
      <div className="flex items-center gap-3 w-full max-w-md">
        <button
          onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          className="p-2 rounded-lg text-slate-400 hover:text-slate-900 hover:bg-slate-100 md:hidden"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="relative w-full">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search research topics, ArXiv papers, or knowledge items..."
            className="w-full bg-slate-50 border border-slate-200 rounded-[14px] pl-10 pr-4 py-2 text-xs md:text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:border-slate-400 focus:ring-1 focus:ring-slate-300 transition-all"
          />
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-2 md:gap-4">
        {/* Model Indicator Dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowModelDropdown(!showModelDropdown)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-[12px] bg-white border border-slate-200 hover:border-slate-300 text-xs text-slate-700 transition-all cursor-pointer shadow-sm"
          >
            <Sparkles className="w-3.5 h-3.5 text-sky-500" />
            <span className="hidden sm:inline font-medium">{selectedModel.name}</span>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
          </button>

          {showModelDropdown && (
            <div className="absolute right-0 mt-2 w-64 bg-white border border-slate-200 rounded-[14px] shadow-xl p-2 z-50">
              <div className="text-[11px] font-semibold text-slate-400 px-3 py-1.5 uppercase tracking-wider">
                Select Cognitive Model
              </div>
              {aiModels.map((model) => (
                <button
                  key={model.id}
                  onClick={() => {
                    setSelectedModel(model);
                    setShowModelDropdown(false);
                  }}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-left text-xs transition-colors cursor-pointer ${
                    selectedModel.id === model.id ? 'bg-slate-900 text-white font-semibold' : 'text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex flex-col">
                    <span>{model.name}</span>
                    <span className={`text-[10px] ${selectedModel.id === model.id ? 'text-slate-300' : 'text-slate-400'}`}>{model.provider}</span>
                  </div>
                  <Badge variant="cyan" size="sm">
                    {model.badge}
                  </Badge>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Notifications Dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="p-2 rounded-xl bg-white border border-slate-200 text-slate-500 hover:text-slate-900 hover:bg-slate-50 transition-colors relative cursor-pointer shadow-sm"
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-sky-500 animate-ping" />
            <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-sky-500" />
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 bg-white border border-slate-200 rounded-[14px] shadow-xl p-3 z-50">
              <div className="flex items-center justify-between pb-2 border-b border-slate-100 mb-2">
                <span className="text-xs font-semibold text-slate-800">Notifications</span>
                <span className="text-[10px] text-sky-600 font-medium">Mark all read</span>
              </div>
              <div className="space-y-2">
                {notifications.map((n) => (
                  <div key={n.id} className="p-2 rounded-lg bg-slate-50 hover:bg-slate-100 text-xs space-y-1">
                    <p className="text-slate-700 leading-snug">{n.text}</p>
                    <span className="text-[10px] text-slate-400">{n.time}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* User Profile Menu */}
        <div className="relative">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center gap-2 pl-2 cursor-pointer focus:outline-none"
          >
            <img
              src={userProfile.avatar}
              alt={userProfile.name}
              className="w-8 h-8 rounded-full ring-2 ring-slate-200 object-cover"
            />
            <span className="hidden md:inline text-xs font-semibold text-slate-700">{userProfile.name}</span>
          </button>

          {showUserMenu && (
            <div className="absolute right-0 mt-2 w-56 bg-white border border-slate-200 rounded-[14px] shadow-xl p-2 z-50">
              <div className="px-3 py-2 border-b border-slate-100 mb-1">
                <p className="text-xs font-semibold text-slate-800">{userProfile.name}</p>
                <p className="text-[11px] text-slate-400 truncate">{userProfile.email}</p>
              </div>
              <a href="/profile" className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-slate-600 hover:bg-slate-50">
                <User className="w-3.5 h-3.5" /> Profile & Compute
              </a>
              <a href="/settings" className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-slate-600 hover:bg-slate-50">
                <SettingsIcon className="w-3.5 h-3.5" /> Agent Settings
              </a>
              <a href="/login" className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-red-500 hover:bg-red-50">
                <LogOut className="w-3.5 h-3.5" /> Log Out
              </a>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default Navbar;
