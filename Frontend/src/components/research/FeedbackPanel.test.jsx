import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import FeedbackPanel from './FeedbackPanel';
import { feedbackAPI } from '../../services/api';

vi.mock('../../services/api', () => ({
  feedbackAPI: { submit: vi.fn(), list: vi.fn() },
}));

describe('FeedbackPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    feedbackAPI.submit.mockResolvedValue({ id: 'f1' });
  });

  it('renders nothing without a real run id (never a dangling control)', () => {
    const { container } = render(<FeedbackPanel runId={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('submits real feedback tied to the actual run id', async () => {
    const user = userEvent.setup();
    render(<FeedbackPanel runId="run-123" />);

    await user.click(screen.getByRole('button', { name: /yes/i }));

    await waitFor(() => expect(feedbackAPI.submit).toHaveBeenCalledWith('run-123', { helpful: true, comment: undefined }));
    expect(await screen.findByText(/your feedback was recorded/i)).toBeInTheDocument();
  });

  it('shows a real error when the backend is unavailable, not a fake success', async () => {
    feedbackAPI.submit.mockRejectedValue(new Error('network down'));
    const user = userEvent.setup();
    render(<FeedbackPanel runId="run-123" />);

    await user.click(screen.getByRole('button', { name: /no/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/service unavailable/i);
    expect(screen.queryByText(/your feedback was recorded/i)).not.toBeInTheDocument();
  });
});
