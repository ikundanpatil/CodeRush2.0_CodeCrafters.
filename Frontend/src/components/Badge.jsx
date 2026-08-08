import React from 'react';

const Badge = ({ children, variant = 'info', size = 'md', glow = false, icon: Icon = null, className = '' }) => {
  const variantStyles = {
    success: 'bg-emerald-50 text-emerald-600 border-emerald-200',
    warning: 'bg-amber-50 text-amber-600 border-amber-200',
    info: 'bg-indigo-50 text-indigo-600 border-indigo-200',
    cyan: 'bg-sky-50 text-sky-600 border-sky-200',
    danger: 'bg-red-50 text-red-600 border-red-200',
    neutral: 'bg-slate-100 text-slate-600 border-slate-200',
  };

  const dotColors = {
    success: 'bg-emerald-500',
    warning: 'bg-amber-500',
    info: 'bg-indigo-500',
    cyan: 'bg-sky-500',
    danger: 'bg-red-500',
    neutral: 'bg-slate-400',
  };

  const sizeStyles = {
    sm: 'text-[11px] px-2 py-0.5 rounded-md gap-1 font-medium',
    md: 'text-xs px-2.5 py-1 rounded-full gap-1.5 font-medium',
    lg: 'text-sm px-3 py-1 rounded-full gap-2 font-semibold',
  };

  return (
    <span
      className={`inline-flex items-center border ${variantStyles[variant]} ${sizeStyles[size]} ${
        glow ? 'shadow-sm' : ''
      } ${className}`}
    >
      {glow && (
        <span className="relative flex h-2 w-2">
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${dotColors[variant]}`}></span>
          <span className={`relative inline-flex rounded-full h-2 w-2 ${dotColors[variant]}`}></span>
        </span>
      )}
      {Icon && <Icon className="w-3.5 h-3.5" />}
      <span>{children}</span>
    </span>
  );
};

export default Badge;
