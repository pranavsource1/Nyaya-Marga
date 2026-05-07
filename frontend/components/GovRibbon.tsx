'use client';

import React, { useCallback } from 'react';

/**
 * GovRibbon — Standard Indian Government accessibility top-ribbon.
 * Functional controls only: Skip-to-content + A-/A/A+ font-size toggles.
 * Non-functional placeholders (Screen Reader, Language Toggle) removed.
 */
export function GovRibbon() {
  const adjustFontSize = useCallback((delta: number) => {
    const html = document.documentElement;
    const current = parseFloat(getComputedStyle(html).fontSize);
    const next = Math.max(12, Math.min(22, current + delta));
    html.style.fontSize = `${next}px`;
  }, []);

  const resetFontSize = useCallback(() => {
    document.documentElement.style.fontSize = '16px';
  }, []);

  return (
    <div
      className="bg-gov-900 text-white text-xs select-none border-b-[3px] border-ka-gold-500"
      role="banner"
      aria-label="Government accessibility ribbon"
    >
      <div className="flex items-center justify-between px-4 md:px-6 py-1.5">
        {/* Left — Official Designation */}
        <div className="flex items-center gap-2">
          <span className="font-bold tracking-wide text-[11px] uppercase">
            Government of Karnataka
          </span>
          <span className="text-white/30 font-light" aria-hidden="true">|</span>
          <span className="font-semibold text-[11px] text-ka-gold-300 tracking-wide">
            ಕರ್ನಾಟಕ ಸರ್ಕಾರ
          </span>
        </div>

        {/* Right — Functional Accessibility Controls */}
        <div className="hidden md:flex items-center gap-3">
          {/* Skip to Content */}
          <a
            href="#main-content"
            className="text-white/60 hover:text-white hover:underline underline-offset-2 transition-colors text-[11px] font-medium"
          >
            Skip to Main Content
          </a>

          <span className="text-white/20" aria-hidden="true">|</span>

          {/* Font Size Controls */}
          <div className="flex items-center gap-0.5" role="group" aria-label="Font size controls">
            <button
              onClick={() => adjustFontSize(-1)}
              className="w-6 h-5 flex items-center justify-center border border-white/20 text-white/70 hover:bg-white hover:text-gov-900 transition-all text-[10px] font-bold"
              aria-label="Decrease font size"
            >
              A-
            </button>
            <button
              onClick={resetFontSize}
              className="w-6 h-5 flex items-center justify-center border border-white/20 text-white/70 hover:bg-white hover:text-gov-900 transition-all text-[11px] font-bold"
              aria-label="Reset font size"
            >
              A
            </button>
            <button
              onClick={() => adjustFontSize(1)}
              className="w-6 h-5 flex items-center justify-center border border-white/20 text-white/70 hover:bg-white hover:text-gov-900 transition-all text-[12px] font-bold"
              aria-label="Increase font size"
            >
              A+
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
