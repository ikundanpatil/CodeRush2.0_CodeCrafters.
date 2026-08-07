import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import CommandCenter from './CommandCenter';

vi.mock('../services/api', () => ({
  researchAPI: {
    startResearch: vi.fn(),
    getStatus: vi.fn(),
    getResult: vi.fn(),
    getTrace: vi.fn(),
    getQuality: vi.fn(),
    getIterations: vi.fn(),
    getEvidenceGraph: vi.fn(),
    cancelResearch: vi.fn(),
  },
}));

describe('CommandCenter page', () => {
  beforeEach(() => {
    delete window.SpeechRecognition;
    delete window.webkitSpeechRecognition;
  });

  it('composes AssistantCore + VoiceInput + panels and starts IDLE with no fabricated data', () => {
    render(<CommandCenter />);

    expect(screen.getByText('EVORESEARCH')).toBeInTheDocument();
    expect(screen.getByText('ONLINE')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /speak to evo/i })).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /assistant state: idle/i })).toBeInTheDocument();

    // No active session yet -- every panel must show a placeholder, never a
    // fabricated number. Several panels legitimately share this copy
    // (Sources, Evidence Graph, Report all start with no data).
    expect(screen.getAllByText(/waiting for data/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/calculating/i).length).toBeGreaterThan(0); // Quality/Gap panels
    expect(screen.queryByRole('button', { name: /stop research/i })).not.toBeInTheDocument();
  });
});
