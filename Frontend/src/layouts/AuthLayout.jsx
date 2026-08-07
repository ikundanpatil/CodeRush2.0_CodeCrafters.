import React from 'react';
import { Outlet } from 'react-router-dom';

const AuthLayout = () => {
  return (
    <div className="min-h-screen bg-[#0F172A] text-[#F8FAFC] flex items-center justify-center p-4 selection:bg-cyan-500/30 selection:text-cyan-200">
      <Outlet />
    </div>
  );
};

export default AuthLayout;
