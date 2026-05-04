import React, { useEffect, useRef } from 'react';
import '../style/transcriptPanel.css';

/**
 * TranscriptPanel
 * Displays a slide-in side panel with the real-time AI and User conversation.
 * Groups messages by InterviewTurn.
 */
export default function TranscriptPanel({ isOpen, onClose, turns }) {
  const contentRef = useRef(null);

  // Auto-scroll to the bottom when new turns/messages arrive
  useEffect(() => {
    if (contentRef.current) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [turns, isOpen]);

  return (
    <div className={`transcript-panel ${isOpen ? 'open' : ''}`}>
      <div className="transcript-panel-inner">
        <div className="transcript-header">
          <h3>
            <svg className="cc-icon" viewBox="0 0 24 24" style={{ width: '20px', height: '20px' }}>
              <rect x="2" y="4" width="20" height="16" rx="2" ry="2"/>
              <path d="M10 10a2 2 0 1 0 0 4"/>
              <path d="M18 10a2 2 0 1 0 0 4"/>
            </svg>
            Live Transcript
          </h3>
          <button onClick={onClose} title="Close transcript">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        <div className="transcript-content" ref={contentRef}>
          {turns.length === 0 ? (
            <p style={{ color: '#9ca3af', textAlign: 'center', marginTop: '20px', fontStyle: 'italic', fontSize: '0.9rem' }}>
              The conversation will appear here...
            </p>
          ) : (
            turns.map((turn, idx) => (
              <div key={idx} className="turn-group">
                {turn.q && (
                  <div className="msg-bubble msg-ai">
                    {turn.q}
                  </div>
                )}
                {turn.a && (
                  <div className="msg-bubble msg-user">
                    {turn.a}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
