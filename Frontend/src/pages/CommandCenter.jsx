import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Square } from 'lucide-react';
import AssistantCore from '../components/voice/AssistantCore';
import VoiceInput from '../components/voice/VoiceInput';
import VoiceStatus from '../components/voice/VoiceStatus';
import ResearchActivityPanel from '../components/research/ResearchActivityPanel';
import SourcesPanel from '../components/research/SourcesPanel';
import EvidenceGraphPanel from '../components/research/EvidenceGraphPanel';
import ResearchQualityPanel from '../components/research/ResearchQualityPanel';
import ResearchGapPanel from '../components/research/ResearchGapPanel';
import ResearchReportPanel from '../components/research/ResearchReportPanel';
import VerificationPanel from '../components/research/VerificationPanel';
import CitationsPanel from '../components/research/CitationsPanel';
import FeedbackPanel from '../components/research/FeedbackPanel';
import Badge from '../components/Badge';
import Button from '../components/Button';
import { useResearchSession } from '../hooks/useResearchSession';
import { useSpeechSynthesis } from '../hooks/useSpeechSynthesis';
import { parseVoiceCommand, TERMINAL_STATUSES } from '../research/researchState';
import { handleVoiceIntent } from '../services/voiceApi';
import { reportAPI } from '../services/api';

const RESEARCHING_STATUSES = new Set(['queued', 'planning', 'searching', 'analyzing', 'generating']);

/** Part J's 9 states, derived from real state only. ANALYZING and
 * VERIFYING come from the backend's own status/current_step -- never
 * simulated on a timer. */
function deriveAssistantState({ micError, micListening, speaking, session }) {
  if (micError || session.status === 'failed') return 'error';
  if (session.status === 'cancelled') return 'cancelled';
  if (speaking) return 'speaking';
  if (micListening) return 'listening';
  if (session.loading) return 'processing';
  if (session.status === 'analyzing') return 'analyzing';
  if (/verif/i.test(session.currentStage || '')) return 'verifying';
  if (session.status && RESEARCHING_STATUSES.has(session.status)) return 'researching';
  if (session.status === 'completed') return 'completed';
  return 'idle';
}

function buildSpokenSummary(session) {
  if (!session.runId) return "I haven't started any research yet. Ask me to research something.";
  if (session.status && RESEARCHING_STATUSES.has(session.status)) {
    return "I'm still researching -- I'll let you know when I have results.";
  }
  if (session.status === 'failed') return 'That research run failed. Please try again.';
  if (session.status === 'cancelled') return 'That research was stopped before it finished.';

  const parts = [];
  if (typeof session.sourcesFound === 'number') parts.push(`${session.sourcesFound} source${session.sourcesFound === 1 ? '' : 's'}`);
  if (typeof session.claimCount === 'number') parts.push(`${session.claimCount} claim${session.claimCount === 1 ? '' : 's'}`);
  const foundText = parts.length ? `I found ${parts.join(' and ')}.` : 'I finished gathering evidence.';
  const validityText =
    session.qualityValid === true
      ? ' The research meets quality requirements.'
      : session.qualityValid === false
        ? ' There are still some quality gaps.'
        : '';
  return `${foundText}${validityText}`;
}

const CommandCenter = () => {
  const { session, start, cancel } = useResearchSession();
  const { supported: ttsSupported, speaking, error: ttsError, speak } = useSpeechSynthesis();
  const [micError, setMicError] = useState(null);
  const [micListening, setMicListening] = useState(false);
  const [banner, setBanner] = useState(null);
  const announcedCompletionForRunId = useRef(null);
  const hasGreetedRef = useRef(false);

  const assistantState = deriveAssistantState({ micError, micListening, speaking, session });

  const speakSummary = useCallback(() => speak(buildSpokenSummary(session)), [session, speak]);
  const speakFullReport = useCallback(() => {
    speak(session.finalReport || "There's no report to read yet.");
  }, [session.finalReport, speak]);

  // Spoken comparison built ONLY from the real verification result --
  // never invented "pros and cons" prose.
  const speakComparison = useCallback(() => {
    const v = session.verification;
    if (!v) {
      speak("I don't have verified findings to compare yet.");
      return;
    }
    const supported = (v.verified_claims || []).map((c) => c.claim_text);
    const contradicted = (v.contradicted_claims || []).map((c) => c.claim_text);
    const parts = [];
    if (supported.length) parts.push(`Supported findings: ${supported.slice(0, 3).join('; ')}.`);
    if (contradicted.length) parts.push(`Conflicting findings: ${contradicted.slice(0, 3).join('; ')}.`);
    speak(parts.length ? parts.join(' ') : "I don't have both supporting and conflicting findings to compare yet.");
  }, [session.verification, speak]);

  const generatePDF = useCallback(async () => {
    if (!session.runId || session.status !== 'completed') {
      speak("I don't have a completed research run to turn into a PDF yet.");
      return;
    }
    try {
      await reportAPI.downloadRunPDF(session.runId);
      speak('Your PDF report is ready.');
    } catch {
      setBanner('Report service unavailable -- the PDF could not be generated.');
    }
  }, [session.runId, session.status, speak]);

  // Spoken greeting the first time the mic is activated in this session --
  // fires and finishes speaking BEFORE recognition starts (see VoiceInput's
  // onBeforeListen), so Evo's own voice can never be misheard as a command.
  const greetOnFirstListen = useCallback(() => {
    if (hasGreetedRef.current) return Promise.resolve();
    hasGreetedRef.current = true;
    return new Promise((resolve) => {
      speak(
        "Hi, I'm Evo. Ask me to research anything, or say summarize, compare, read the report, or stop.",
        { onEnd: resolve },
      );
    });
  }, [speak]);

  const handleTranscript = useCallback(
    async (text) => {
      const hasActiveSession = Boolean(session.runId) && !TERMINAL_STATUSES.has(session.status);
      const command = parseVoiceCommand(text, { hasActiveSession, originalQuestion: session.query });

      if (['START_RESEARCH', 'FOLLOW_UP', 'FIND_MORE_EVIDENCE'].includes(command.intent)) {
        speak("Sure, I'll research that and check the evidence.");
      } else if (command.intent === 'STOP') {
        speak(session.runId && !TERMINAL_STATUSES.has(session.status) ? "Okay, stopping the research." : "There's nothing running to stop.");
      } else if (command.intent === 'EMPTY') {
        speak("I didn't catch a request there. Try asking me to research something.");
      }

      await handleVoiceIntent(command, {
        session, start, cancel, speakSummary, speakFullReport, speakComparison, generatePDF,
      });
    },
    [session, start, cancel, speak, speakSummary, speakFullReport, speakComparison, generatePDF],
  );

  // Speak a short summary once when a run completes -- never the full
  // report automatically (only "read the report" does that).
  useEffect(() => {
    if (session.status === 'completed' && announcedCompletionForRunId.current !== session.runId) {
      announcedCompletionForRunId.current = session.runId;
      speakSummary();
    }
  }, [session.status, session.runId, speakSummary]);

  useEffect(() => {
    if (session.error) setBanner(session.error);
  }, [session.error]);

  const handleStop = () => {
    cancel();
  };

  const isActive = Boolean(session.runId) && !TERMINAL_STATUSES.has(session.status);

  return (
    <div className="w-full flex flex-col gap-6">
      {/* Top bar */}
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-extrabold text-slate-900 tracking-widest">EVORESEARCH</h1>
        <Badge variant="success" glow>
          ONLINE
        </Badge>
      </div>

      {banner && (
        <div
          role="alert"
          className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2 flex items-center justify-between"
        >
          <span>{banner}</span>
          <button onClick={() => setBanner(null)} className="text-red-600 hover:text-red-800 cursor-pointer" aria-label="Dismiss">
            &times;
          </button>
        </div>
      )}

      {/* Assistant core + voice input */}
      <div className="order-1 flex flex-col items-center gap-4 py-8 bg-white border border-slate-200 shadow-sm rounded-[20px]">
        <AssistantCore state={assistantState} />
        <VoiceStatus
          state={assistantState}
          detail={
            !ttsSupported && assistantState === 'speaking'
              ? 'Text-to-speech is not supported in this browser.'
              : ttsError || undefined
          }
        />
        <VoiceInput
          onTranscript={(text) => {
            setMicError(null);
            handleTranscript(text);
          }}
          onStateChange={({ listening, error }) => {
            setMicListening(listening);
            setMicError(error);
          }}
          onBeforeListen={greetOnFirstListen}
          disabled={session.loading}
        />
        {isActive && (
          <Button size="sm" variant="danger" icon={Square} onClick={handleStop}>
            Stop Research
          </Button>
        )}
      </div>

      {/* Panel grid -- mobile stack order: Sources, Activity, Quality, Gaps, Evidence, Report */}
      <div className="order-2 grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="order-1">
          <SourcesPanel sources={session.sources} />
        </div>
        <div className="order-2">
          <ResearchActivityPanel trace={session.trace} />
        </div>
        <div className="order-3">
          <ResearchQualityPanel quality={session.quality} qualityScore={session.qualityScore} />
        </div>
        <div className="order-4">
          <ResearchGapPanel gaps={session.gaps} iterationCount={session.iterationCount} />
        </div>
        <div className="order-5">
          <VerificationPanel verification={session.verification} />
        </div>
        <div className="order-6">
          <CitationsPanel citations={session.citations} />
        </div>
      </div>

      <div className="order-3">
        <EvidenceGraphPanel graph={session.evidenceGraph} />
      </div>

      {session.finalReport && (
        <div className="order-4 space-y-4">
          <ResearchReportPanel
            finalReport={session.finalReport}
            query={session.query}
            onReadAloud={speakFullReport}
            speaking={speaking}
            onGeneratePDF={generatePDF}
            canGeneratePDF={session.status === 'completed'}
          />
          <FeedbackPanel runId={session.runId} />
        </div>
      )}
    </div>
  );
};

export default CommandCenter;
