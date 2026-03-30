import { useState, useEffect } from 'react';

/**
 * DeviceGuard — Blocks mobile & tablet access to the interview.
 *
 * Detection layers:
 * 1. User-Agent string matching (Android, iPhone, iPad, etc.)
 * 2. Screen width < 1024px
 * 3. Touch-primary device (pointer: coarse)
 * 4. navigator.maxTouchPoints > 2
 * 5. Resize listener — if screen shrinks mid-session
 *
 * Props:
 * - children: JSX to render if device is allowed
 */
export default function DeviceGuard({ children }) {
  const [blocked, setBlocked] = useState(false);

  const checkDevice = () => {
    const ua = navigator.userAgent || navigator.vendor || window.opera || '';

    // 1. User-Agent mobile/tablet patterns
    const mobileRegex = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini|Mobile|Tablet|Silk|Kindle|PlayBook/i;
    const isMobileUA = mobileRegex.test(ua);

    // 2. Screen width < 1024
    const isSmallScreen = window.screen.width < 1024 || window.innerWidth < 1024;

    // 3. Touch-primary device
    const isCoarsePointer = window.matchMedia?.('(pointer: coarse)')?.matches;

    // 4. High touch points (most desktop trackpads report 0 or 1)
    const isTouchDevice = navigator.maxTouchPoints > 2;

    // 5. iPad detection (iPadOS 13+ reports as Mac)
    const isIPad = /Macintosh/i.test(ua) && navigator.maxTouchPoints > 1;

    // Block if ANY strong indicator is present
    if (isMobileUA || isIPad || (isSmallScreen && isCoarsePointer) || (isSmallScreen && isTouchDevice)) {
      return true;
    }
    return false;
  };

  useEffect(() => {
    setBlocked(checkDevice());

    const handleResize = () => {
      setBlocked(checkDevice());
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  if (blocked) {
    return (
      <div className="device-block-screen">
        <div className="device-block-card">
          <div className="device-block-icon">🖥️</div>
          <h1 className="device-block-title">Desktop Only</h1>
          <p className="device-block-text">
            This AI interview can only be conducted on a <strong>Laptop or PC</strong>.
          </p>
          <p className="device-block-text">
            Mobile phones and tablets are not permitted for security reasons.
            Please switch to a desktop computer and try again.
          </p>
          <div className="device-block-requirements">
            <div className="device-block-req-item">
              <span className="device-block-check">✓</span> Laptop or Desktop PC
            </div>
            <div className="device-block-req-item">
              <span className="device-block-check">✓</span> Working webcam
            </div>
            <div className="device-block-req-item">
              <span className="device-block-check">✓</span> Chrome or Edge browser
            </div>
            <div className="device-block-req-item">
              <span className="device-block-cross">✗</span> Mobile phones
            </div>
            <div className="device-block-req-item">
              <span className="device-block-cross">✗</span> Tablets / iPad
            </div>
          </div>
        </div>
      </div>
    );
  }

  return children;
}
