import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ResearchQualityPanel from './ResearchQualityPanel';

describe('ResearchQualityPanel', () => {
  it('shows "Calculating..." instead of a fabricated number when quality data is not yet available', () => {
    render(<ResearchQualityPanel quality={null} qualityScore={null} />);
    expect(screen.getByText(/calculating/i)).toBeInTheDocument();
    expect(screen.queryByText('0')).not.toBeInTheDocument();
  });

  it('renders real backend numbers once available', () => {
    render(
      <ResearchQualityPanel
        quality={{
          valid: true, source_count: 18, evidence_count: 42, claim_count: 13,
          supported_claim_count: 11, unverified_claim_count: 2, checks: [],
        }}
        qualityScore={0.87}
      />,
    );
    expect(screen.getByText('18')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('11')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('87%')).toBeInTheDocument();
    expect(screen.getByText('VALID')).toBeInTheDocument();
  });
});
