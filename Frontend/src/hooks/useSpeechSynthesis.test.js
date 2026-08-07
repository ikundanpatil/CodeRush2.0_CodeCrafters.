import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSpeechSynthesis } from './useSpeechSynthesis';

describe('useSpeechSynthesis', () => {
  const originalSynthesis = window.speechSynthesis;
  const originalUtterance = window.SpeechSynthesisUtterance;

  beforeEach(() => {
    window.speechSynthesis = { speak: vi.fn(), cancel: vi.fn(), getVoices: () => [] };
    window.SpeechSynthesisUtterance = class {
      constructor(text) {
        this.text = text;
      }
    };
  });

  afterEach(() => {
    window.speechSynthesis = originalSynthesis;
    window.SpeechSynthesisUtterance = originalUtterance;
  });

  it('reports unsupported and still calls onEnd when speechSynthesis is missing', () => {
    delete window.speechSynthesis;
    const { result } = renderHook(() => useSpeechSynthesis());
    const onEnd = vi.fn();

    act(() => result.current.speak('hello', { onEnd }));

    expect(result.current.supported).toBe(false);
    expect(result.current.error).toMatch(/not supported/i);
    expect(onEnd).toHaveBeenCalled();
  });

  it('speaks text and tracks the speaking state through the utterance lifecycle', () => {
    const { result } = renderHook(() => useSpeechSynthesis());
    const onEnd = vi.fn();

    act(() => result.current.speak('short summary', { onEnd }));

    expect(window.speechSynthesis.speak).toHaveBeenCalledTimes(1);
    const utterance = window.speechSynthesis.speak.mock.calls[0][0];

    act(() => utterance.onstart());
    expect(result.current.speaking).toBe(true);

    act(() => utterance.onend());
    expect(result.current.speaking).toBe(false);
    expect(onEnd).toHaveBeenCalled();
  });

  it('never speaks empty text', () => {
    const { result } = renderHook(() => useSpeechSynthesis());
    act(() => result.current.speak(''));
    expect(window.speechSynthesis.speak).not.toHaveBeenCalled();
  });

  it('cancel() stops synthesis and clears the speaking flag', () => {
    const { result } = renderHook(() => useSpeechSynthesis());
    act(() => result.current.cancel());
    expect(window.speechSynthesis.cancel).toHaveBeenCalled();
    expect(result.current.speaking).toBe(false);
  });
});
