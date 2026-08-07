// Thin glue between a parsed voice intent and the research session --
// deliberately NOT a second HTTP client. Every network call this module
// triggers goes through researchAPI (services/api.js), i.e. the exact same
// POST /api/research / POST /api/research/{id}/cancel every other part of
// the app uses. This is what keeps the Policy Engine boundary intact: there
// is no other way for voice input to reach the backend.

import { RESEARCH_INTENTS } from '../research/researchState';

/**
 * @param {{ intent: string, payload: any }} command
 * @param {{
 *   session: import('../research/researchState').EMPTY_SESSION,
 *   start: (question: string) => Promise<void>,
 *   cancel: () => Promise<void>,
 *   speakSummary: () => void,
 *   speakFullReport: () => void,
 * }} handlers
 */
export function handleVoiceIntent(command, handlers) {
  const { intent, payload } = command;
  const { session, start, cancel, speakSummary, speakFullReport, speakComparison, generatePDF } = handlers;

  switch (intent) {
    case RESEARCH_INTENTS.STOP:
      if (session.runId) return cancel();
      return Promise.resolve();

    case RESEARCH_INTENTS.START_RESEARCH:
    case RESEARCH_INTENTS.FOLLOW_UP:
    case RESEARCH_INTENTS.FIND_MORE_EVIDENCE:
      if (!payload?.question) return Promise.resolve();
      return start(payload.question);

    case RESEARCH_INTENTS.SUMMARIZE:
      speakSummary();
      return Promise.resolve();

    case RESEARCH_INTENTS.COMPARE:
      speakComparison?.();
      return Promise.resolve();

    case RESEARCH_INTENTS.GENERATE_PDF:
      return generatePDF?.() ?? Promise.resolve();

    case RESEARCH_INTENTS.READ_REPORT:
      speakFullReport();
      return Promise.resolve();

    case RESEARCH_INTENTS.EMPTY:
    default:
      return Promise.resolve();
  }
}
