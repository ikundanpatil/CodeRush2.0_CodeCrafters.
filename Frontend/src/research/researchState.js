// Phase 10 research-session state shape + voice command interpretation.
//
// parseVoiceCommand is intentionally a PURE, LOCAL, regex-based function --
// no LLM call, no network request. This is what makes "voice cannot bypass
// the Policy Engine" true by construction: there is no code path here that
// produces anything other than these five intents, and only
// START_RESEARCH/FOLLOW_UP ever reach the network -- both via the exact
// same POST /api/research every other part of the app already uses, which
// flows through the existing orchestrator -> Policy Engine unchanged.

export const RESEARCH_INTENTS = {
  START_RESEARCH: 'START_RESEARCH',
  STOP: 'STOP',
  READ_REPORT: 'READ_REPORT',
  SUMMARIZE: 'SUMMARIZE',
  FOLLOW_UP: 'FOLLOW_UP',
  FIND_MORE_EVIDENCE: 'FIND_MORE_EVIDENCE',
  COMPARE: 'COMPARE',
  GENERATE_PDF: 'GENERATE_PDF',
  EMPTY: 'EMPTY',
};

const STOP_PATTERN = /\b(stop|cancel|halt)\b/i;
const READ_REPORT_PATTERN = /\bread\s+(the\s+)?(report|final answer|answer|that|it)\b/i;
const SUMMARIZE_PATTERN = /\bsummar(y|ize|ise)\b/i;
const PDF_PATTERN = /\b(pdf|create a report|generate a report)\b/i;
const COMPARE_PATTERN = /\bcompare\b/i;
const MORE_EVIDENCE_PATTERN = /\b(find more|more evidence|continue research|keep researching)\b/i;
const FOLLOW_UP_PATTERN = /\b(go deeper|dig into|more on|expand on|look further into)\b/i;
const WAKE_WORD_PATTERN = /^\s*(hey\s+)?evo[,:]?\s*/i;

function stripWakeWord(text) {
  const stripped = text.replace(WAKE_WORD_PATTERN, '').trim();
  return stripped || text;
}

/**
 * @param {string} rawTranscript
 * @param {{ hasActiveSession?: boolean, originalQuestion?: string|null }} context
 * @returns {{ intent: string, payload: { question: string } | null }}
 */
export function parseVoiceCommand(rawTranscript, context = {}) {
  const transcript = (rawTranscript || '').trim();
  if (!transcript) return { intent: RESEARCH_INTENTS.EMPTY, payload: null };

  if (STOP_PATTERN.test(transcript)) {
    return { intent: RESEARCH_INTENTS.STOP, payload: null };
  }
  if (READ_REPORT_PATTERN.test(transcript)) {
    return { intent: RESEARCH_INTENTS.READ_REPORT, payload: null };
  }
  if (SUMMARIZE_PATTERN.test(transcript)) {
    return { intent: RESEARCH_INTENTS.SUMMARIZE, payload: null };
  }
  if (PDF_PATTERN.test(transcript)) {
    return { intent: RESEARCH_INTENTS.GENERATE_PDF, payload: null };
  }
  if (context.hasActiveSession && COMPARE_PATTERN.test(transcript)) {
    return { intent: RESEARCH_INTENTS.COMPARE, payload: null };
  }
  if (context.hasActiveSession && MORE_EVIDENCE_PATTERN.test(transcript)) {
    const topic = context.originalQuestion ? ` on: ${context.originalQuestion}` : '';
    return {
      intent: RESEARCH_INTENTS.FIND_MORE_EVIDENCE,
      payload: { question: `Find additional evidence${topic}. Specifically: ${transcript}` },
    };
  }
  if (context.hasActiveSession && FOLLOW_UP_PATTERN.test(transcript)) {
    const topic = context.originalQuestion ? ` on: ${context.originalQuestion}` : '';
    return {
      intent: RESEARCH_INTENTS.FOLLOW_UP,
      // Phase 3 memory automatically supplies continuity for this new run --
      // no separate memory glue needed here.
      payload: { question: `Continue the research${topic}. Specifically: ${transcript}` },
    };
  }

  return { intent: RESEARCH_INTENTS.START_RESEARCH, payload: { question: stripWakeWord(transcript) } };
}

// Every field starts null/undefined-safe. Components must render a
// "Calculating..." / "Waiting for data" placeholder for null fields --
// never invent a number.
export const EMPTY_SESSION = {
  runId: null,
  query: null,
  status: null,
  currentStage: null,
  sourcesFound: null,
  evidenceCount: null,
  claimCount: null,
  qualityScore: null,
  qualityValid: null,
  iterationCount: null,
  researchDecision: null,
  sources: null,
  trace: null,
  gaps: null,
  quality: null,
  evidenceGraph: null,
  finalReport: null,
  verification: null,
  citations: null,
  error: null,
  loading: false,
};

export const TERMINAL_STATUSES = new Set(['completed', 'failed', 'cancelled']);
