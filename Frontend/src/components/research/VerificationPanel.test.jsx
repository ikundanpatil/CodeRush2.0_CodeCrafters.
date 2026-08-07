import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import VerificationPanel from './VerificationPanel';
import CitationsPanel from './CitationsPanel';

describe('VerificationPanel', () => {
  it('shows a waiting placeholder instead of a fabricated verdict', () => {
    render(<VerificationPanel verification={null} />);
    expect(screen.getByText(/waiting for data/i)).toBeInTheDocument();
    expect(screen.queryByText('VERIFIED')).not.toBeInTheDocument();
  });

  it('renders the real verification counts and verdict', () => {
    render(
      <VerificationPanel
        verification={{
          valid: true, score: 1.0,
          verified_claims: [{ claim_text: 'A' }, { claim_text: 'B' }],
          unsupported_claims: [], contradicted_claims: [], citation_errors: [],
        }}
      />,
    );
    expect(screen.getByText('VERIFIED')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('100%')).toBeInTheDocument();
  });

  it('surfaces unsupported claims rather than hiding them', () => {
    render(
      <VerificationPanel
        verification={{
          valid: false, score: 0.5, verified_claims: [],
          unsupported_claims: [{ claim_text: 'An unverified claim.' }],
          contradicted_claims: [], citation_errors: ['Fabricated URL detected'],
        }}
      />,
    );
    expect(screen.getByText('ISSUES FOUND')).toBeInTheDocument();
    expect(screen.getByText('An unverified claim.')).toBeInTheDocument();
    expect(screen.getByText('Fabricated URL detected')).toBeInTheDocument();
  });
});

describe('CitationsPanel', () => {
  it('shows a placeholder instead of inventing citations', () => {
    render(<CitationsPanel citations={null} />);
    expect(screen.getByText(/waiting for data/i)).toBeInTheDocument();
  });

  it('renders only real citation data', () => {
    render(
      <CitationsPanel
        citations={[
          { citation_id: 1, title: 'Real Study', publisher: 'Real Journal', url: 'https://real.example.com' },
        ]}
      />,
    );
    expect(screen.getByText('[1]')).toBeInTheDocument();
    expect(screen.getByText('Real Study')).toBeInTheDocument();
    expect(screen.getByText('Real Journal')).toBeInTheDocument();
    expect(screen.getByRole('link')).toHaveAttribute('href', 'https://real.example.com');
  });
});
