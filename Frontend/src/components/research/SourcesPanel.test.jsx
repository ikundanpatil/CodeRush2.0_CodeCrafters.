import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import SourcesPanel from './SourcesPanel';

describe('SourcesPanel', () => {
  it('shows a waiting placeholder instead of inventing sources', () => {
    render(<SourcesPanel sources={null} />);
    expect(screen.getByText(/waiting for data/i)).toBeInTheDocument();
  });

  it('renders real source titles and URLs only', () => {
    const sources = [
      { id: '1', title: 'Real Study on AI Productivity', url: 'https://journal.example.com/study', publisher: 'Example Journal', evidence: [{ id: 'e1' }] },
    ];
    render(<SourcesPanel sources={sources} />);
    expect(screen.getByText('Real Study on AI Productivity')).toBeInTheDocument();
    expect(screen.getByRole('link')).toHaveAttribute('href', 'https://journal.example.com/study');
    expect(screen.getByRole('link')).toHaveAttribute('target', '_blank');
    expect(screen.getByRole('link')).toHaveAttribute('rel', expect.stringContaining('noopener'));
  });
});
