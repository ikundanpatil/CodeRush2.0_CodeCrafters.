import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useVoiceRecognition, VOICE_STATES } from './useVoiceRecognition';

class FakeSpeechRecognition {
  constructor() {
    FakeSpeechRecognition.instances.push(this);
  }
  start() {
    this.onstart?.();
  }
  stop() {
    this.onend?.();
  }
  abort() {}
}
FakeSpeechRecognition.instances = [];

describe('useVoiceRecognition', () => {
  const originalSpeechRecognition = window.SpeechRecognition;
  const originalWebkit = window.webkitSpeechRecognition;

  beforeEach(() => {
    FakeSpeechRecognition.instances = [];
  });

  afterEach(() => {
    window.SpeechRecognition = originalSpeechRecognition;
    window.webkitSpeechRecognition = originalWebkit;
  });

  it('reports unsupported when no SpeechRecognition implementation exists', () => {
    delete window.SpeechRecognition;
    delete window.webkitSpeechRecognition;

    const { result } = renderHook(() => useVoiceRecognition());
    expect(result.current.supported).toBe(false);

    act(() => result.current.startListening());

    expect(result.current.state).toBe(VOICE_STATES.ERROR);
    expect(result.current.error).toMatch(/does not support/i);
  });

  it('never listens without an explicit startListening() call', () => {
    window.SpeechRecognition = FakeSpeechRecognition;
    const { result } = renderHook(() => useVoiceRecognition());
    expect(result.current.state).toBe(VOICE_STATES.IDLE);
    expect(FakeSpeechRecognition.instances.length).toBe(0);
  });

  it('transitions IDLE -> LISTENING and delivers a final transcript', () => {
    window.SpeechRecognition = FakeSpeechRecognition;
    const onResult = vi.fn();
    const { result } = renderHook(() => useVoiceRecognition({ onResult }));

    act(() => result.current.startListening());
    expect(result.current.state).toBe(VOICE_STATES.LISTENING);

    const instance = FakeSpeechRecognition.instances[0];
    act(() => {
      const finalChunk = Object.assign([{ transcript: 'research quantum computing' }], { isFinal: true });
      instance.onresult({ resultIndex: 0, results: [finalChunk] });
    });

    expect(result.current.transcript).toBe('research quantum computing');
    expect(onResult).toHaveBeenCalledWith('research quantum computing');
  });

  it('surfaces a clear message on permission-denied errors', () => {
    window.SpeechRecognition = FakeSpeechRecognition;
    const { result } = renderHook(() => useVoiceRecognition());

    act(() => result.current.startListening());
    const instance = FakeSpeechRecognition.instances[0];
    act(() => instance.onerror({ error: 'not-allowed' }));

    expect(result.current.state).toBe(VOICE_STATES.ERROR);
    expect(result.current.error).toMatch(/microphone permission/i);
  });
});
