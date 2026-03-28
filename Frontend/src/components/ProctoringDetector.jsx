import { useEffect, useRef, useState, useCallback } from 'react';
import api from '../utils/api';

/**
 * ProctoringDetector — Browser-side AI proctoring sub-agent.
 *
 * Uses TensorFlow.js models:
 * - BlazeFace: face detection (is face present? looking at camera?)
 * - COCO-SSD: object detection (phone, book, multiple people)
 *
 * Reports violations to the backend DetectorAgent via POST /ai/interview/violation
 *
 * Props:
 * - videoRef: React ref to the <video> element with webcam feed
 * - sessionId: UUID of the current interview session
 * - active: boolean — whether detection is running
 * - onViolation: (type, message) => void — callback for violations
 * - onWarning: (type, message) => void — callback for warnings
 * - onAutoEnd: (reason) => void — callback to auto-end interview
 */

const VIOLATION_TYPES = {
  NO_FACE: 'NO_FACE',
  MULTIPLE_FACES: 'MULTIPLE_FACES',
  LOOKING_AWAY: 'LOOKING_AWAY',
  PHONE_DETECTED: 'PHONE_DETECTED',
  BOOK_DETECTED: 'BOOK_DETECTED',
  MULTIPLE_PEOPLE: 'MULTIPLE_PEOPLE',
};

// Thresholds
const NO_FACE_WARNING_SEC = 8;
const NO_FACE_AUTO_END_SEC = 20;
const LOOKING_AWAY_SEC = 6;
const FACE_CHECK_INTERVAL = 2000;   // every 2s
const OBJECT_CHECK_INTERVAL = 5000; // every 5s

export default function ProctoringDetector({ videoRef, sessionId, active, onViolation, onWarning, onAutoEnd }) {
  const [modelsLoaded, setModelsLoaded] = useState(false);
  const [status, setStatus] = useState('Loading AI models...');
  const blazefaceRef = useRef(null);
  const cocoRef = useRef(null);
  const faceIntervalRef = useRef(null);
  const objectIntervalRef = useRef(null);
  const noFaceCounterRef = useRef(0);
  const lookingAwayCounterRef = useRef(0);
  const mountedRef = useRef(true);

  // Report violation to backend DetectorAgent
  const reportToBackend = useCallback(async (violationType, message, severity = 'warning') => {
    if (!sessionId) return;
    try {
      const res = await api.post('/ai/interview/violation', {
        session_id: sessionId,
        violation_type: violationType,
        message,
        severity,
      });
      // If backend says to end, trigger auto-end
      if (res.data?.should_end) {
        onAutoEnd?.(res.data.reason || violationType);
      }
    } catch (err) {
      // Don't block detection if backend reporting fails
      console.warn('Proctor: failed to report to backend', err);
    }
  }, [sessionId, onAutoEnd]);

  // Load models
  useEffect(() => {
    mountedRef.current = true;
    let cancelled = false;

    const loadModels = async () => {
      try {
        setStatus('Loading face detection...');
        const tf = await import('@tensorflow/tfjs');
        await tf.ready();

        const blazeface = await import('@tensorflow-models/blazeface');
        const blazefaceModel = await blazeface.load();
        if (cancelled) return;
        blazefaceRef.current = blazefaceModel;

        setStatus('Loading object detection...');
        const cocoSsd = await import('@tensorflow-models/coco-ssd');
        const cocoModel = await cocoSsd.load();
        if (cancelled) return;
        cocoRef.current = cocoModel;

        setModelsLoaded(true);
        setStatus('Proctoring active');
      } catch (err) {
        console.error('Failed to load proctoring models:', err);
        setStatus('Proctoring unavailable');
      }
    };

    loadModels();

    return () => {
      cancelled = true;
      mountedRef.current = false;
    };
  }, []);

  // Face detection loop
  const runFaceDetection = useCallback(async () => {
    if (!blazefaceRef.current || !videoRef?.current || !mountedRef.current) return;

    const video = videoRef.current;
    if (video.readyState < 2) return;

    try {
      const predictions = await blazefaceRef.current.estimateFaces(video, false);

      if (predictions.length === 0) {
        // No face detected
        noFaceCounterRef.current += FACE_CHECK_INTERVAL / 1000;

        if (noFaceCounterRef.current >= NO_FACE_AUTO_END_SEC) {
          reportToBackend(VIOLATION_TYPES.NO_FACE, 'No face detected for 20s — auto-ending', 'critical');
          onAutoEnd?.('NO_FACE_TIMEOUT');
          return;
        }
        if (noFaceCounterRef.current >= NO_FACE_WARNING_SEC) {
          const msg = `No face detected for ${Math.round(noFaceCounterRef.current)}s — interview will end soon`;
          onWarning?.(VIOLATION_TYPES.NO_FACE, msg);
          reportToBackend(VIOLATION_TYPES.NO_FACE, msg, 'warning');
        }
      } else {
        noFaceCounterRef.current = 0;

        if (predictions.length > 1) {
          const msg = 'Multiple faces detected — only one person allowed';
          onViolation?.(VIOLATION_TYPES.MULTIPLE_FACES, msg);
          reportToBackend(VIOLATION_TYPES.MULTIPLE_FACES, msg, 'critical');
        }

        // Check if looking away by checking face position relative to frame
        const face = predictions[0];
        const start = face.topLeft;
        const end = face.bottomRight;
        const faceWidth = end[0] - start[0];
        const faceCenterX = start[0] + faceWidth / 2;
        const videoWidth = video.videoWidth;

        // If face center is too far left or right (edge 15% of frame)
        const edgeThreshold = videoWidth * 0.15;
        if (faceCenterX < edgeThreshold || faceCenterX > videoWidth - edgeThreshold) {
          lookingAwayCounterRef.current += FACE_CHECK_INTERVAL / 1000;
          if (lookingAwayCounterRef.current >= LOOKING_AWAY_SEC) {
            const msg = 'Please look at the camera — eyes must be on screen';
            onWarning?.(VIOLATION_TYPES.LOOKING_AWAY, msg);
            reportToBackend(VIOLATION_TYPES.LOOKING_AWAY, msg, 'warning');
          }
        } else {
          lookingAwayCounterRef.current = 0;
        }
      }
    } catch (err) {
      // Silently ignore detection errors
    }
  }, [videoRef, onWarning, onViolation, onAutoEnd, reportToBackend]);

  // Object detection loop
  const runObjectDetection = useCallback(async () => {
    if (!cocoRef.current || !videoRef?.current || !mountedRef.current) return;

    const video = videoRef.current;
    if (video.readyState < 2) return;

    try {
      const predictions = await cocoRef.current.detect(video);

      for (const pred of predictions) {
        const cls = pred.class.toLowerCase();

        if (cls === 'cell phone' && pred.score > 0.5) {
          const msg = '📱 Phone detected! Interview will be terminated.';
          onViolation?.(VIOLATION_TYPES.PHONE_DETECTED, msg);
          reportToBackend(VIOLATION_TYPES.PHONE_DETECTED, msg, 'critical');
          onAutoEnd?.('PHONE_DETECTED');
          return;
        }

        if (cls === 'book' && pred.score > 0.6) {
          const msg = '📖 Book/notes detected — please remove them';
          onWarning?.(VIOLATION_TYPES.BOOK_DETECTED, msg);
          reportToBackend(VIOLATION_TYPES.BOOK_DETECTED, msg, 'warning');
        }
      }

      // Count people
      const personCount = predictions.filter(p => p.class === 'person' && p.score > 0.5).length;
      if (personCount > 1) {
        const msg = `${personCount} people detected — only 1 person allowed`;
        onViolation?.(VIOLATION_TYPES.MULTIPLE_PEOPLE, msg);
        reportToBackend(VIOLATION_TYPES.MULTIPLE_PEOPLE, msg, 'critical');
        onAutoEnd?.('MULTIPLE_PEOPLE');
      }
    } catch (err) {
      // Silently ignore
    }
  }, [videoRef, onWarning, onViolation, onAutoEnd, reportToBackend]);

  // Start/stop detection loops
  useEffect(() => {
    if (active && modelsLoaded) {
      faceIntervalRef.current = setInterval(runFaceDetection, FACE_CHECK_INTERVAL);
      objectIntervalRef.current = setInterval(runObjectDetection, OBJECT_CHECK_INTERVAL);

      // Run immediately once
      runFaceDetection();
      runObjectDetection();
    }

    return () => {
      if (faceIntervalRef.current) clearInterval(faceIntervalRef.current);
      if (objectIntervalRef.current) clearInterval(objectIntervalRef.current);
    };
  }, [active, modelsLoaded, runFaceDetection, runObjectDetection]);

  return (
    <div className="proctor-status">
      <div className={`proctor-dot ${modelsLoaded ? 'active' : 'loading'}`} />
      <span className="proctor-label">{status}</span>
    </div>
  );
}
