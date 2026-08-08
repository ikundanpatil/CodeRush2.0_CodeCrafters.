import React from 'react';
import { Outlet } from 'react-router-dom';

const AuthLayout = () => {
  return (
    <div className="min-h-screen bg-[#F6F7FB] text-slate-900 flex items-center justify-center p-4 selection:bg-sky-200 selection:text-sky-900">
      <Outlet />
    </div>
  );
};

export default AuthLayout;
