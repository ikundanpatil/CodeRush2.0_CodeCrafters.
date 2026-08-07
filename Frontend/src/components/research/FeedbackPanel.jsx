import React, { useState } from 'react';
import { ThumbsUp, ThumbsDown, Check } from 'lucide-react';
import { feedbackAPI } from '../../services/api';
import Button from '../Button';

/** Part I: real feedback, tied to the actual run_id and POSTed to the real
 * backend endpoint -- never a purely cosmetic thumbs button. */
const FeedbackPanel = ({ runId }) => {
  const [submitted, setSubmitted] = useState(false);
  const [helpful, setHelpful] = useState(null);
  const [comment, setComment] = useState('');
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const submit = async (isHelpful) => {
    if (!runId) return;
    setBusy(true);
    setError(null);
    try {
      await feedbackAPI.submit(runId, { helpful: isHelpful, comment: comment || undefined });
      setHelpful(isHelpful);
      setSubmitted(true);
    } catch {
      setError('Could not submit feedback -- service unavailable.');
    } finally {
      setBusy(false);
    }
  };

  if (!runId) return null;

  return (
    <div className="w-full bg-[#1E293B]/90 border border-slate-700/80 rounded-[14px] p-5 shadow-xl flex flex-col gap-3">
      <h4 className="text-sm font-bold text-slate-100">Was this answer useful?</h4>

      {submitted ? (
        <p className="flex items-center gap-1.5 text-xs text-emerald-400">
          <Check className="w-3.5 h-3.5" aria-hidden="true" />
          Thanks -- your feedback was recorded ({helpful ? 'helpful' : 'not helpful'}).
        </p>
      ) : (
        <>
          <textarea
            rows={2}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Optional comment..."
            aria-label="Optional feedback comment"
            className="w-full bg-[#0F172A] border border-slate-700/80 rounded-[12px] px-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/50 resize-none"
          />
          <div className="flex items-center gap-2">
            <Button size="sm" variant="secondary" icon={ThumbsUp} isLoading={busy} onClick={() => submit(true)}>
              Yes
            </Button>
            <Button size="sm" variant="secondary" icon={ThumbsDown} isLoading={busy} onClick={() => submit(false)}>
              No
            </Button>
          </div>
        </>
      )}

      {error && (
        <p className="text-xs text-red-400" role="alert">
          {error}
        </p>
      )}
    </div>
  );
};

export default FeedbackPanel;
