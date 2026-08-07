import '@testing-library/jest-dom/vitest';

// jsdom does not implement the Web Speech API. Individual tests override
// these with more specific mocks (unsupported-browser tests delete them
// entirely); this baseline keeps every other test from crashing on import.
if (!window.SpeechSynthesisUtterance) {
  window.SpeechSynthesisUtterance = class SpeechSynthesisUtterance {
    constructor(text) {
      this.text = text;
    }
  };
}

if (!window.speechSynthesis) {
  window.speechSynthesis = {
    speak: () => {},
    cancel: () => {},
    getVoices: () => [],
  };
}
