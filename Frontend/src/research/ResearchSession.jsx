import React, { createContext, useContext } from 'react';
import { useResearchSession } from './useResearchSession';

// A small, local provider scoped to the voice/command-center feature only --
// deliberately separate from the existing global ResearchContext (which
// mixes real polling with mock chat/step data) so this feature never
// inherits that fabrication and never risks destabilizing it.
const ResearchSessionContext = createContext(null);

export const ResearchSessionProvider = ({ children }) => {
  const value = useResearchSession();
  return <ResearchSessionContext.Provider value={value}>{children}</ResearchSessionContext.Provider>;
};

export const useResearchSessionContext = () => {
  const ctx = useContext(ResearchSessionContext);
  if (!ctx) throw new Error('useResearchSessionContext must be used within a ResearchSessionProvider');
  return ctx;
};

export default ResearchSessionProvider;
