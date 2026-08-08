import React from 'react';
import { Loader2 } from 'lucide-react';

const Button = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled = false,
  icon: Icon = null,
  onClick,
  className = '',
  type = 'button',
  ...props
}) => {
  const baseStyles =
    'inline-flex items-center justify-center font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer active:scale-[0.98]';

  const sizeStyles = {
    sm: 'text-xs px-3 py-1.5 rounded-lg gap-1.5',
    md: 'text-sm px-4 py-2.5 rounded-[14px] gap-2',
    lg: 'text-base px-6 py-3.5 rounded-[14px] gap-2.5 font-semibold',
  };

  const variantStyles = {
    primary:
      'bg-slate-900 hover:bg-slate-800 text-white shadow-md shadow-slate-900/10 focus:ring-slate-400 border border-slate-900',
    secondary:
      'bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 hover:border-slate-300 focus:ring-slate-300 shadow-sm',
    danger:
      'bg-red-50 hover:bg-red-100 text-red-600 border border-red-200 hover:border-red-300 focus:ring-red-400',
    ghost:
      'bg-transparent hover:bg-slate-100 text-slate-500 hover:text-slate-900 border border-transparent focus:ring-slate-300',
  };

  return (
    <button
      type={type}
      disabled={disabled || isLoading}
      onClick={onClick}
      className={`${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
      {...props}
    >
      {isLoading ? (
        <Loader2 className="w-4 h-4 animate-spin text-current" />
      ) : Icon ? (
        <Icon className="w-4 h-4 text-current" />
      ) : null}
      <span>{children}</span>
    </button>
  );
};

export default Button;
