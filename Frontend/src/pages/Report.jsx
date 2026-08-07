import React from 'react';
import { useResearch } from '../context/ResearchContext';
import ReportCard from '../components/ReportCard';

const Report = () => {
  const { currentReport } = useResearch();

  return (
    <div className="w-full space-y-6 pb-12">
      <ReportCard report={currentReport} />
    </div>
  );
};

export default Report;
