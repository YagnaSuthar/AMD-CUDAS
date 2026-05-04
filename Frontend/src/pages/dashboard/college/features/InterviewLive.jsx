import { useState, useEffect, useRef, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import api from '../../../../utils/api';
import ProctoringDetector from '../../../../components/ProctoringDetector';
import DeviceGuard from '../../../../components/DeviceGuard';
import TranscriptPanel from '../../../../components/TranscriptPanel';
import '../../../../style/interviewLive.css';

/**
 * InterviewLive â€” Google Meet-Style Full-Screen AI Interview.
 *
 * Layout:
 * â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
 * â”‚              TOP BAR                     â”‚
 * â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
 * â”‚  AI INTERVIEWER   â”‚   STUDENT CAMERA     â”‚
 * â”‚  avatar+waveform  â”‚   webcam preview     â”‚
 * â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
 * â”‚  QUESTION OVERLAY (glassmorphism)        â”‚
 * â”‚  TRANSCRIPT OVERLAY                      â”‚
 * â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
 * â”‚  FLOATING CONTROL BAR                    â”‚
 * â”‚  ðŸŽ¤  ðŸ“¹  ðŸ”Š  â±  âš™  ðŸ”´                  â”‚
 * â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
 */

const STATES = {
  LOADING: 'loading',
  RULES: 'rules',
  GREETING: 'greeting',
  CONFIRM_START: 'confirm_start',
  QUESTION: 'question',
  LISTENING: 'listening',
  EVALUATING: 'evaluating',
  EARLY_EXIT: 'early_exit',
  REPORT: 'report',
  CLOSED: 'closed',
  ERROR: 'error',
};

const SOFT_PAUSE = 10;
const HARD_PAUSE = 15;
const SKIP_PATTERNS = [
  'skip',
  "i don't know",
  'i dont know',
  'no idea',
  'not sure',
  'pass',
];

/* â”€â”€ SVG Icons â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */

const MicIcon   = () => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>;
const MicOffIcon = () => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="1" y1="1" x2="23" y2="23"/><path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6"/><path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2c0 .76-.12 1.5-.34 2.18"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>;
const CamIcon   = () => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>;
const CamOffIcon = () => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 16v1a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h2m5.66 0H14a2 2 0 0 1 2 2v3.34l1 1L23 7v10"/><line x1="1" y1="1" x2="23" y2="23"/></svg>;
const VolumeIcon = () => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>;
const PhoneOff  = () => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.68 13.31a16 16 0 0 0 3.41 2.6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7 2 2 0 0 1 1.72 2v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.42 19.42 0 0 1-3.33-2.67m-2.67-3.34a19.79 19.79 0 0 1-3.07-8.63A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91"/><line x1="23" y1="1" x2="1" y2="23"/></svg>;
const StopIcon  = () => <svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>;

export default function InterviewLive() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const jobIdUrl = queryParams.get('job_id');
  const modeParam = queryParams.get('mode') || 'practice';
  const roleParam = queryParams.get('role') || 'basic';

  /* â”€â”€ state â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
  const [state, setState]   = useState(STATES.LOADING);
  const [config, setConfig] = useState({ max_questions: 15, min_questions: 5, answer_timeout: 20, silence_timeout: 10 });
  const [sessionId, setSessionId]     = useState(null);
  const [agentText, setAgentText]     = useState('');
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [questionNumber, setQuestionNumber]   = useState(0);
  const [questionCount, setQuestionCount] = useState(0);
  const [showTranscript, setShowTranscript]   = useState(false);
  const [sessionTurns, setSessionTurns]       = useState([]);
  const [transcript, setTranscript]   = useState('');
  const [liveTranscript, setLiveTranscript] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isSpeaking, setIsSpeaking]   = useState(false);
  const [agentSpeaking, setAgentSpeaking] = useState(false);
  const [timeLeft, setTimeLeft]       = useState(0);
  const [globalTimeLeft, setGlobalTimeLeft] = useState(20 * 60);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [interviewStarted, setInterviewStarted] = useState(false);
  const [speechHint, setSpeechHint]   = useState('');
  const [userSpeaking, setUserSpeaking] = useState(false);
  const [startTimer, setStartTimer] = useState(0);
  const [silenceTimer, setSilenceTimer] = useState(0);
  const [report, setReport]           = useState(null);
  const [studentReport, setStudentReport] = useState(null);
  const [reportTab, setReportTab]     = useState('student');
  const [error, setError]             = useState('');
  const [difficulty, setDifficulty]   = useState('medium');
  const [runningScore, setRunningScore] = useState(0);
  const [tabSwitchCount, setTabSwitchCount] = useState(0);
  const [showTabWarning, setShowTabWarning] = useState(false);
  const [cameraOn, setCameraOn] = useState(false);
  const [volumeOn, setVolumeOn] = useState(true);
  const [proctorWarning, setProctorWarning] = useState(null);
  const [cameraRequired, setCameraRequired] = useState(true);
  const [pdfLoading, setPdfLoading] = useState(false);
  const proctorWarningTimer = useRef(null);

  const recognitionRef  = useRef(null);
  const timerRef        = useRef(null);
  const silenceTimerRef = useRef(null);
  const videoRef        = useRef(null);
  const streamRef       = useRef(null);
  const micStreamRef    = useRef(null);
  const audioCtxRef     = useRef(null);
  const analyserRef     = useRef(null);
  const rafRef          = useRef(null);
  const listeningStartTsRef = useRef(null);
  const userSpeakingRef = useRef(false);
  const userHasSpokenRef = useRef(false);
  const lastWaitingTickTsRef = useRef(null);
  const waitingTimeRef = useRef(0);
  const silenceTimerRef2 = useRef(0);
  const blankSubmittedRef = useRef(false);
  const silenceStartTsRef = useRef(null);
  const answerStartTsRef = useRef(null);
  const autoListenRef   = useRef(false);
  const submitAnswerRef  = useRef(null);
  const hasStartedRef   = useRef(false);
  const finalTranscriptRef = useRef('');         // accumulates final results across STT segments
  const isListeningRef     = useRef(false);      // tracks if we WANT to keep listening

  /* â”€â”€ fullscreen is now handled by DashboardLayout.jsx â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */

  /* â”€â”€ utils â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
  const goBack = useCallback(() => navigate('/dashboard/interview'), [navigate]);

  const clearTimers = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
  }, []);

  const stopAudioAnalysis = useCallback(() => {
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
  }, []);

  const stopMicStream = useCallback(() => {
    stopAudioAnalysis();
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach(t => t.stop());
      micStreamRef.current = null;
    }
    if (audioCtxRef.current) {
      try { audioCtxRef.current.close(); } catch {}
      audioCtxRef.current = null;
    }
    analyserRef.current = null;
  }, [stopAudioAnalysis]);

  const ensureMicStream = useCallback(async () => {
    if (micStreamRef.current) return micStreamRef.current;
    const s = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      }
    });
    micStreamRef.current = s;

    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    const ctx = new AudioCtx();
    audioCtxRef.current = ctx;
    const source = ctx.createMediaStreamSource(s);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 2048;
    source.connect(analyser);
    analyserRef.current = analyser;
    return s;
  }, []);

  const fetchStudentReport = useCallback(async () => {
    if (!sessionId) return;
    try {
      const r = await api.get(`/ai/interview/report/${sessionId}/student`);
      setStudentReport(r.data);
    } catch { /* ok */ }
  }, [sessionId]);

  const fetchReport = useCallback(async () => {
    if (!sessionId) return;
    try {
      const r = await api.get(`/ai/interview/report/${sessionId}`);
      setReport(r.data);
      await fetchStudentReport();
      setState(STATES.REPORT);
    } catch {
      setState(STATES.REPORT);
    }
  }, [sessionId, fetchStudentReport]);

  /* â”€â”€ camera toggle (camera is MANDATORY â€” cannot be turned off) â”€â”€â”€â”€â”€â”€ */
  const startCamera = useCallback(async () => {
    try {
      const s = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      streamRef.current = s;
      if (videoRef.current) videoRef.current.srcObject = s;
      setCameraOn(true);
      return true;
    } catch {
      setCameraOn(false);
      return false;
    }
  }, []);

  const toggleCamera = useCallback(async () => {
    if (cameraOn) {
      // Camera must stay on during interview â€” show warning
      setProctorWarning('âš ï¸ Camera is required for the interview. You cannot turn it off.');
      if (proctorWarningTimer.current) clearTimeout(proctorWarningTimer.current);
      proctorWarningTimer.current = setTimeout(() => setProctorWarning(null), 4000);
      return;
    } else {
      await startCamera();
    }
  }, [cameraOn, startCamera]);


  // Reattach stream to video element whenever cameraOn or state changes
  // (video element may not exist yet when startCamera runs during init)
  useEffect(() => {
    if (cameraOn && streamRef.current && videoRef.current && !videoRef.current.srcObject) {
      videoRef.current.srcObject = streamRef.current;
    }
  }, [cameraOn, state]);

  useEffect(() => () => streamRef.current?.getTracks().forEach(t => t.stop()), []);

  useEffect(() => {
    setAgentSpeaking(isSpeaking);
  }, [isSpeaking]);

  /* â”€â”€ TTS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
  const speak = useCallback((text, onEnd) => {
    if (!window.speechSynthesis || !volumeOn) { onEnd?.(); return; }
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 0.95; u.pitch = 1; u.volume = 1;
    setIsSpeaking(true);
    u.onend = () => { setIsSpeaking(false); onEnd?.(); };
    u.onerror = () => { setIsSpeaking(false); onEnd?.(); };
    window.speechSynthesis.speak(u);
  }, [volumeOn]);

  const stopRecording = useCallback(() => {
    isListeningRef.current = false;
    if (recognitionRef.current) {
      try { recognitionRef.current.abort(); } catch {}
      recognitionRef.current = null;
    }
    setIsRecording(false);
    setLiveTranscript('');
    setState(s => (s === STATES.LISTENING ? STATES.QUESTION : s));
    stopAudioAnalysis();
  }, [stopAudioAnalysis]);

  const submitFromCurrentTranscript = useCallback(() => {
    const accumulated = (finalTranscriptRef.current || '').trim() || (transcript || '').trim();
    if (!accumulated) return null;
    return accumulated;
  }, [transcript]);

  /* â”€â”€ end / recording â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
  const runSilenceMonitor = useCallback(() => {
    const analyser = analyserRef.current;
    if (!analyser) return;

    const buf = new Uint8Array(analyser.fftSize);
    const threshold = 0.01;

    const tick = () => {
      if (!isListeningRef.current || blankSubmittedRef.current) {
        return;
      }
      analyser.getByteTimeDomainData(buf);
      let sum = 0;
      for (let i = 0; i < buf.length; i++) {
        const v = (buf[i] - 128) / 128;
        sum += v * v;
      }
      const rms = Math.sqrt(sum / buf.length);
      const now = Date.now();

      const speaking = rms > threshold;
      userSpeakingRef.current = speaking;

      // No time-based cutoffs. We only end an answer after the user has spoken
      // and then stays silent for HARD_PAUSE seconds.
      lastWaitingTickTsRef.current = null;

      if (speaking) {
        userHasSpokenRef.current = true;
        if (!userSpeaking) setUserSpeaking(true);
        waitingTimeRef.current = 0;
        setStartTimer(0);
        if (silenceTimerRef2.current !== 0) {
          silenceTimerRef2.current = 0;
          setSilenceTimer(0);
        }
        setSpeechHint('');
        silenceStartTsRef.current = null;
        if (!answerStartTsRef.current) answerStartTsRef.current = now;
      } else {
        if (userHasSpokenRef.current) {
          if (!silenceStartTsRef.current) silenceStartTsRef.current = now;
          const silenceSec = (now - silenceStartTsRef.current) / 1000;

          // Phase 2 (Silence Timer): only active after user started speaking.
          silenceTimerRef2.current = silenceSec;
          setSilenceTimer(silenceSec);
          setStartTimer(0);
          waitingTimeRef.current = 0;
          const remaining = Math.max(0, Math.ceil(HARD_PAUSE - silenceSec));
          setTimeLeft(remaining);

          if (silenceSec >= SOFT_PAUSE && silenceSec < HARD_PAUSE) {
            setSpeechHint("You can continue if you're not finished");
          }

          if (silenceSec >= HARD_PAUSE) {
            const payload = submitFromCurrentTranscript();
            stopRecording();
            if (payload) {
              submitAnswerRef.current?.(payload);
              return;
            }
          }
        }
      }

      if (blankSubmittedRef.current) {
        return;
      }
      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
  }, [isRecording, isSpeaking, stopRecording, submitFromCurrentTranscript, userSpeaking]);

  const startRecording = useCallback(async () => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      setError('Use Chrome for speech.');
      return;
    }

    try {
      await ensureMicStream();
    } catch {
      setError('Microphone permission denied or not available.');
      return;
    }

    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    finalTranscriptRef.current = '';
    isListeningRef.current = true;
    userHasSpokenRef.current = false;
    blankSubmittedRef.current = false;
    silenceStartTsRef.current = null;
    answerStartTsRef.current = null;
    listeningStartTsRef.current = Date.now();
    lastWaitingTickTsRef.current = null;
    waitingTimeRef.current = 0;
    silenceTimerRef2.current = 0;
    setStartTimer(0);
    setSilenceTimer(0);
    setUserSpeaking(false);
    setTimeLeft(HARD_PAUSE);
    setSpeechHint('');

    const createRecognition = () => {
      const r = new SR();
      r.continuous = true;
      r.interimResults = true;
      r.lang = 'en-US';

      r.onresult = e => {
        let finalDelta = '';
        let interimDelta = '';
        for (let i = e.resultIndex; i < e.results.length; i++) {
          const result = e.results[i];
          const transcript = result[0].transcript;
          if (result.isFinal) {
            finalDelta += transcript + ' ';
          } else {
            interimDelta += transcript;
          }
        }

        // Instant live transcript (browser-based). Do not wait for finalization.
        // Keep this separate from persisted transcript used for submission.
        const liveNow = interimDelta.trim();
        if (liveNow) {
          setLiveTranscript(liveNow);
        }

        // Update live UI with final + interim text
        const liveText = (finalTranscriptRef.current + ' ' + finalDelta + ' ' + interimDelta).trim();
        setTranscript(liveText);
        console.log('[STT Live]', { finalDelta: finalDelta.trim(), interimDelta: interimDelta.trim(), liveText });

        // Persist only final results for submission
        if (finalDelta.trim()) {
          finalTranscriptRef.current = `${finalTranscriptRef.current} ${finalDelta}`.trim();
          setLiveTranscript('');
        }

        const currentTranscript = (finalTranscriptRef.current || '').trim();

        // Treat STT activity itself as speech to avoid premature silence cutoff
        // when the user speaks softly and RMS threshold doesn't trigger.
        if (currentTranscript) {
          userHasSpokenRef.current = true;
          if (!userSpeakingRef.current) userSpeakingRef.current = true;
          setUserSpeaking(true);
          waitingTimeRef.current = 0;
          setStartTimer(0);
          silenceStartTsRef.current = null;
          setSpeechHint('');
          if (!answerStartTsRef.current) answerStartTsRef.current = Date.now();
        }

        const lower = currentTranscript.toLowerCase();
        if (SKIP_PATTERNS.some(p => lower.includes(p))) {
          stopRecording();
          submitAnswerRef.current?.(currentTranscript);
        }
      };

      r.onerror = e => {
        // Keep mic/listening on even if SpeechRecognition reports transient errors.
        // The onend handler will restart as long as isListeningRef.current is true.
        if (e.error !== 'aborted') {
          setIsRecording(true);
        }
      };

      r.onend = () => {
        if (isListeningRef.current) {
          try {
            const newR = createRecognition();
            recognitionRef.current = newR;
            newR.start();
          } catch {
            setIsRecording(false);
            isListeningRef.current = false;
          }
        } else {
          setIsRecording(false);
        }
      };

      return r;
    };

    const r = createRecognition();
    recognitionRef.current = r;
    r.start();
    setIsRecording(true);
    setState(STATES.LISTENING);
    setTranscript('');
    setLiveTranscript('');
    runSilenceMonitor();
  }, [ensureMicStream, runSilenceMonitor, stopRecording]);

  const endInterview = useCallback(async (reason = 'normal') => {
    if (!sessionId) return;
    clearTimers();
    stopRecording();
    window.speechSynthesis?.cancel();
    setIsSpeaking(false);
    setInterviewStarted(false);
    
    setState(STATES.EVALUATING);
    setAgentText('Generating report...');
    
    try {
      const r = await api.post('/ai/interview/end', { session_id: sessionId, ended_reason: reason });
      setReport(r.data.report);
      await fetchStudentReport();
      setState(STATES.REPORT);
    } catch (e) {
      // Best-effort: even if the end call fails, try fetching any already-generated report.
      try {
        await fetchReport();
      } catch {
        setError(e.response?.data?.detail || 'Failed');
        setState(STATES.ERROR);
      }
    }
  }, [sessionId, stopRecording, clearTimers, fetchStudentReport]);

  const isBasicMode = roleParam === 'basic';

  // Count-up timer for non-basic modes
  useEffect(() => {
    if (!interviewStarted || isBasicMode) return;

    const timer = setInterval(() => {
      setElapsedTime(prev => prev + 1);
    }, 1000);

    return () => clearInterval(timer);
  }, [interviewStarted, isBasicMode]);

  // Existing countdown timer for basic mode
  useEffect(() => {
    if (!interviewStarted || !isBasicMode) return;

    const timer = setInterval(() => {
      setGlobalTimeLeft(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          endInterview();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [interviewStarted, isBasicMode, endInterview]);

  /* â”€â”€ proctoring callbacks (must be after endInterview) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
  const handleProctorWarning = useCallback((type, message) => {
    setProctorWarning(message);
    if (proctorWarningTimer.current) clearTimeout(proctorWarningTimer.current);
    proctorWarningTimer.current = setTimeout(() => setProctorWarning(null), 5000);
  }, []);

  const handleProctorViolation = useCallback((type, message) => {
    setProctorWarning('ðŸ”´ ' + message);
  }, []);

  const handleProctorAutoEnd = useCallback(async (reason) => {
    setProctorWarning(`ðŸ”´ Interview terminated: ${reason.replace(/_/g, ' ')}`);
    setTimeout(async () => {
      await endInterview(reason);
    }, 2000);
  }, [endInterview]);

  const handleTabSwitch = useCallback(async () => {
    if (![STATES.QUESTION, STATES.LISTENING, STATES.EVALUATING].includes(state)) return;
    setShowTabWarning(true);
    await endInterview('TAB_SWITCH');
  }, [state, endInterview]);

  const handleTerminate = useCallback(async () => {
    await endInterview('USER_TERMINATED');
  }, [endInterview]);

  const formatApiError = useCallback((err, fallback = 'Something went wrong') => {
    const data = err?.response?.data;
    const detail = data?.detail ?? data;

    if (typeof detail === 'string' && detail.trim()) return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0];
      if (typeof first === 'string') return first;
      if (first && typeof first === 'object') {
        const loc = Array.isArray(first.loc) ? first.loc.join('.') : '';
        const msg = typeof first.msg === 'string' ? first.msg : '';
        const composed = [loc, msg].filter(Boolean).join(': ');
        if (composed) return composed;
        try {
          return JSON.stringify(first);
        } catch {
          return fallback;
        }
      }
    }
    if (detail && typeof detail === 'object') {
      try {
        return JSON.stringify(detail);
      } catch {
        return fallback;
      }
    }
    if (typeof err?.message === 'string' && err.message.trim()) return err.message;
    return fallback;
  }, []);

  /* â”€â”€ submit answer â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
  const submitAnswer = useCallback(async (txt) => {
    if (!currentQuestion || !sessionId) return;

    const normalizedTxt = (txt ?? '').toString();
    const displayTxt = normalizedTxt.trim() ? normalizedTxt : '[No response]';

    const questionId = currentQuestion.question_id || currentQuestion.questionId || currentQuestion.id;
    if (!questionId) {
      setError('Unable to submit answer: missing question id. Please restart the interview.');
      setState(STATES.ERROR);
      return;
    }

    clearTimers();
    stopRecording();
    setLiveTranscript('');
    setState(STATES.EVALUATING);
    setAgentText('Analyzing your response...');
    
    // Update local transcript with user's answer
    setSessionTurns(prev => {
      const newTurns = [...prev];
      if (newTurns.length > 0) {
        newTurns[newTurns.length - 1].a = displayTxt;
      }
      return newTurns;
    });

    try {
      const r = await api.post('/ai/interview/answer', { 
        session_id: sessionId, 
        question_id: questionId, 
        answer_text: normalizedTxt 
      });
      const d = r.data;
      setRunningScore(d.running_avg_score || 0);
      setDifficulty(d.next_difficulty || 'medium');
      
      if (d.next_action === 'early_exit') {
        setAgentText(d.early_exit_message || 'Interview concluded.');
        speak(d.early_exit_message || 'Interview concluded.', () => fetchReport());
        setState(STATES.EARLY_EXIT);
        setInterviewStarted(false);
      } else if (d.next_action === 'end') {
        setAgentText((d.agent_response || '') + ' Preparing your report...');
        speak(d.agent_response, () => endInterview());
      } else {
        setAgentText(d.agent_response);
        speak(d.agent_response, () => {
          if (d.next_question) {
            const nextQid = d.next_question.question_id || d.next_question.questionId || d.next_question.id;
            if (!nextQid) {
              setError('Received next question without an id. Please restart the interview.');
              setState(STATES.ERROR);
              return;
            }
            setCurrentQuestion(d.next_question);
            setQuestionNumber(p => p + 1);
            setQuestionCount(prev => prev + 1);
            setSessionTurns(prev => [...prev, { q: d.next_question.question, a: null }]);
            setTranscript('');
            setLiveTranscript('');
            setDifficulty(d.next_question.difficulty || 'medium');
            setAgentText(d.next_question.question);
            setState(STATES.QUESTION);
            speak(d.next_question.question, () => {
              autoListenRef.current = true;   // arm auto-listen after TTS ends
            });
          }
        });
      }
    } catch (e) {
      setError(formatApiError(e, 'Failed to submit answer'));
      // If submit fails mid-interview, still try to end and show report so the user can download.
      await endInterview('ERROR');
    }
  }, [currentQuestion, sessionId, stopRecording, clearTimers, speak, fetchReport, endInterview, formatApiError]);

  useEffect(() => {
    submitAnswerRef.current = submitAnswer;
  }, [submitAnswer]);

  const downloadPDF = async () => {
    if (!sessionId || pdfLoading) return;
    try {
      setPdfLoading(true);
      const res = await api.get(`/ai/interview/report/pdf/${sessionId}`, {
        responseType: 'blob'
      });
      const blob = new Blob([res.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Interview_Report_${sessionId.substring(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (err) {
      console.error("Download failed", err);
      setError("Failed to download PDF report");
    } finally {
      setPdfLoading(false);
    }
  };

  const toggleMic = useCallback(() => {
    if (isRecording) {
      isListeningRef.current = false;
      stopRecording();
      const accumulated = finalTranscriptRef.current.trim() || transcript.trim();
      if (accumulated) submitAnswer(accumulated);
      else if (!userHasSpokenRef.current) submitAnswer('');
    } else {
      startRecording();
    }
  }, [isRecording, transcript, startRecording, stopRecording, submitAnswer]);

  useEffect(() => {
    if (isSpeaking) {
      autoListenRef.current = false;
      setSpeechHint('');
      stopRecording();
      if (micStreamRef.current) {
        micStreamRef.current.getAudioTracks().forEach(t => { t.enabled = false; });
      }
    } else {
      if (micStreamRef.current) {
        micStreamRef.current.getAudioTracks().forEach(t => { t.enabled = true; });
      }
      if (autoListenRef.current && state === STATES.QUESTION && !isRecording) {
        autoListenRef.current = false;
        startRecording();
      }
    }
  }, [isSpeaking, startRecording, stopRecording, state, isRecording, setSpeechHint]);

  /* â”€â”€ greeting â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
  const handleGreeting = useCallback(async (ans) => {
    if (!sessionId) return;
    try {
      const r = await api.post('/ai/interview/greet', { session_id: sessionId, answer: ans });
      const d = r.data;
      setAgentText(d.agent_message);
      speak(d.agent_message);
      if (d.next_step === 'confirm_start') setState(STATES.CONFIRM_START);
      else if (d.next_step === 'session_closed') setState(STATES.CLOSED);
      else if (d.next_step === 'first_question' && d.first_question) {
        const firstQid = d.first_question.question_id || d.first_question.questionId || d.first_question.id;
        if (!firstQid) {
          setError('Received first question without an id. Please restart the interview.');
          setState(STATES.ERROR);
          return;
        }
        setCurrentQuestion(d.first_question);
        setQuestionNumber(1);
        setQuestionCount(1);
        setGlobalTimeLeft(20 * 60);
        setElapsedTime(0);
        setInterviewStarted(true);
        setSessionTurns([{ q: d.first_question.question, a: null }]);
        setDifficulty(d.first_question.difficulty || 'medium');
        setTranscript('');
        setLiveTranscript('');
        speak(d.agent_message, () => {
          setAgentText(d.first_question.question);
          setState(STATES.QUESTION);
          speak(d.first_question.question, () => {
              autoListenRef.current = true;   // arm auto-listen after TTS ends
            });
        });
        return;
      }
    } catch (e) {
      setError(formatApiError(e, 'Error'));
      setState(STATES.ERROR);
    }
  }, [sessionId, speak, formatApiError]);

  /* â”€â”€ Effects â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
  useEffect(() => {
    if (hasStartedRef.current) return;
    hasStartedRef.current = true;
    (async () => {
      try {
        // MANDATORY: Start camera first
        const cameraOk = await startCamera();
        if (!cameraOk) {
          setError('Camera access is required for the interview. Please allow camera access and try again.');
          setState(STATES.ERROR);
          return;
        }

        let jr = 'Software Developer';
        let interviewMode = modeParam;
        let selectedRole = roleParam;
        if (jobIdUrl) {
          const pr = await api.get('/pipeline/student');
          const pipelineData = pr.data?.find(p => String(p.job_id) === String(jobIdUrl));
          if (pipelineData?.status === 'AI_COMPLETED') { 
              setError('Already completed Round 1 for this job. No retakes allowed.'); 
              setState(STATES.ERROR); 
              return; 
          }
          if (pipelineData) {
              jr = pipelineData.job_title || pipelineData.job_role || jr;
              interviewMode = 'recruiter';
              // In recruiter flow, job_role comes from the job title; mode must remain a valid enum value.
              selectedRole = 'basic';
          }
        }
        const c = await api.get('/ai/interview/config');
        setConfig(c.data);
        const r = await api.post('/ai/interview/start', { 
            job_role: jr,
            job_id: jobIdUrl || null,
            interview_type: interviewMode,
            mode: selectedRole,
        });
        setSessionId(r.data.session_id);
        setAgentText(r.data.greeting);
        setState(STATES.GREETING);
        // We do not auto-speak here due to browser gesture requirements; the user can read the text and click 'Yes' to proceed.
      } catch (e) { setError(formatApiError(e, 'Failed to start')); setState(STATES.ERROR); }
    })();
    return () => { clearTimers(); stopRecording(); window.speechSynthesis?.cancel(); streamRef.current?.getTracks().forEach(t => t.stop()); };
  }, [jobIdUrl, modeParam, speak, clearTimers, stopRecording, startCamera, formatApiError]);

  useEffect(() => {
    const onVis = () => { if (document.hidden) handleTabSwitch(); };
    const block = e => e.preventDefault();
    document.addEventListener('visibilitychange', onVis);
    document.addEventListener('copy', block);
    document.addEventListener('paste', block);
    document.addEventListener('contextmenu', block);
    return () => {
      document.removeEventListener('visibilitychange', onVis);
      document.removeEventListener('copy', block);
      document.removeEventListener('paste', block);
      document.removeEventListener('contextmenu', block);
    };
  }, [handleTabSwitch]);

  /* â”€â”€ helper circle â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
  const circ = 2 * Math.PI * 18;
  const activeTotal = HARD_PAUSE;
  const off  = circ - (timeLeft / Math.max(activeTotal, 1)) * circ;
  const tCls = timeLeft <= 5 ? 'danger' : timeLeft <= 10 ? 'warn' : '';

  const isActive = [STATES.QUESTION, STATES.LISTENING, STATES.EVALUATING].includes(state);

  const minutes = Math.floor(globalTimeLeft / 60);
  const seconds = globalTimeLeft % 60;
  const formattedTime = `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;

  // Count-up timer display for non-basic modes
  const elapsedMinutes = Math.floor(elapsedTime / 60);
  const elapsedSeconds = elapsedTime % 60;
  const formattedElapsed = `${elapsedMinutes}:${elapsedSeconds < 10 ? '0' : ''}${elapsedSeconds}`;

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     RENDER
     â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */

  return (
    <DeviceGuard>
    <div className="meet-root">

      {/* â”€â”€ Proctoring Warning Banner â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      {proctorWarning && (
        <div className="meet-proctor-warning">
          <span>{proctorWarning}</span>
          <button onClick={() => setProctorWarning(null)}>âœ•</button>
        </div>
      )}

      {/* â”€â”€ Tab-switch warning â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      {showTabWarning && (
        <div className="meet-warn-overlay">
          <div className="meet-warn-icon">âš ï¸</div>
          <div className="meet-warn-title">TAB SWITCH DETECTED</div>
          <div className="meet-warn-text">Please stay on the interview screen. Switching tabs is monitored and may affect your evaluation.</div>
          <div className="meet-warn-count">Warnings: {tabSwitchCount}</div>
        </div>
      )}

      {/* â”€â”€ TOP BAR â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <div className="meet-topbar">
        <div className="meet-topbar-left">
          <div className={`meet-live-dot ${state === STATES.ERROR ? 'err' : state === STATES.EARLY_EXIT ? 'warn' : ''}`} />
          <span className="meet-brand">AI INTERVIEW</span>
        </div>
        <div className="meet-topbar-center">
          {questionCount > 0 && <>
            <span className="meet-badge">Question {questionCount} / {isBasicMode ? 20 : 15}</span>
            <span className={`meet-badge meet-diff ${difficulty}`}>{difficulty}</span>
            <span className="meet-badge">{isBasicMode ? formattedTime : `⏱ ${formattedElapsed}`}</span>
          </>}
          {runningScore > 0 && <span className="meet-badge">{(runningScore * 100).toFixed(0)}% ({(runningScore * 10).toFixed(1)}/10)</span>}
        </div>
        <div className="meet-topbar-right">
          {tabSwitchCount > 0 && <span className="meet-badge" style={{ color: '#f59e0b' }}>⚠️ {tabSwitchCount}</span>}
        </div>
      </div>

      {/* ── MAIN CONTENT AREA ── */}
      <div style={{ flex: 1, display: 'flex', minHeight: 0, overflow: 'hidden', width: '100%' }}>

        {/* === LEFT: Video Grid & Overlays === */}
        <div style={{
          flex: showTranscript ? '0 0 70%' : '1',
          maxWidth: showTranscript ? '70%' : '100%',
          position: 'relative',
          display: 'flex',
          flexDirection: 'column',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
        }}>

          {/* ── VIDEO GRID ── */}
          <div className={`meet-grid ${(!isActive && state !== STATES.EVALUATING && state !== STATES.GREETING && state !== STATES.CONFIRM_START && state !== STATES.RULES) ? 'solo' : ''}`}>

        {/* === AI TILE === */}
        <div className="meet-tile">
          {/* Loading */}
          {state === STATES.LOADING && (
            <div className="meet-state-center">
              <div className="meet-spinner" />
              <p className="meet-loading-text">Connecting to AI Interviewer…</p>
            </div>
          )}

          {/* Error */}
          {state === STATES.ERROR && (
            <div className="meet-state-center">
              <p className="meet-error-text">{error}</p>
              <button className="meet-btn-no" onClick={goBack}>Close</button>
            </div>
          )}

          {/* Greeting / Confirm */}
          {(state === STATES.GREETING || state === STATES.CONFIRM_START) && (
            <div className="meet-state-center">
              <div className="meet-ai-area">
                <div className="meet-avatar-wrap">
                  <div className={`meet-avatar-ring ${isSpeaking ? 'speaking' : ''}`} />
                  <div className={`meet-avatar-circle ${isSpeaking ? 'speaking' : ''}`}>AI</div>
                </div>
                <div className={`meet-waveform ${isSpeaking ? '' : 'paused'}`}>
                  {[...Array(9)].map((_, i) => <div key={i} className="meet-waveform-bar" />)}
                </div>
              </div>
              <p className="meet-agent-text">{agentText}</p>
              <div className="meet-greeting-btns">
                <button className="meet-btn-yes" onClick={() => handleGreeting('yes')} disabled={isSpeaking}>
                  {state === STATES.GREETING ? "Yes, I'm comfortable" : "Yes, let's start!"}
                </button>
                <button className="meet-btn-no" onClick={() => handleGreeting('no')} disabled={isSpeaking}>
                  {state === STATES.GREETING ? "No, not right now" : "No, schedule later"}
                </button>
              </div>
            </div>
          )}

          {/* Closed */}
          {state === STATES.CLOSED && (
            <div className="meet-state-center">
              <p className="meet-agent-text">{agentText}</p>
              <button className="meet-btn-yes" onClick={goBack}>Return to Dashboard</button>
            </div>
          )}

          {/* Active: AI Avatar + Waveform */}
          {isActive && (
            <div className="meet-state-center">
              <div className="meet-ai-area">
                <div className="meet-avatar-wrap">
                  <div className={`meet-avatar-ring ${isSpeaking ? 'speaking' : ''}`} />
                  <div className={`meet-avatar-circle ${isSpeaking ? 'speaking' : ''}`}>AI</div>
                </div>
                <div className={`meet-waveform ${isSpeaking ? '' : 'paused'}`}>
                  {[...Array(9)].map((_, i) => <div key={i} className="meet-waveform-bar" />)}
                </div>
              </div>
              {state === STATES.EVALUATING && (
                <><div className="meet-spinner" /><p className="meet-loading-text">Analyzing your response…</p></>
              )}
            </div>
          )}

          {/* Early Exit */}
          {state === STATES.EARLY_EXIT && (
            <div className="meet-state-center">
              <div style={{ fontSize: '3rem' }}>🎯</div>
              <p className="meet-agent-text">{agentText}</p>
              <div className="meet-spinner" />
              <p className="meet-loading-text">Generating your report…</p>
            </div>
          )}

          {/* Report */}
          {state === STATES.REPORT && (
            <div className="meet-state-center" style={{ overflowY: 'auto', padding: 20 }}>
              <div className="meet-report">
                <div className="meet-report-header">
                  <h3 className="meet-report-title">Interview Complete</h3>
                  <p className="meet-report-sub">Your detailed performance report</p>
                </div>
                <div className="meet-report-tabs">
                  <button className={`meet-report-tab ${reportTab === 'student' ? 'active' : ''}`} onClick={() => setReportTab('student')}>📚 Your Report</button>
                  <button className={`meet-report-tab ${reportTab === 'summary' ? 'active' : ''}`} onClick={() => setReportTab('summary')}>📊 Score Summary</button>
                </div>
                {reportTab === 'student' && studentReport && <>
                  <div className="meet-report-scores">
                    <div className="meet-report-score-card"><div className="meet-report-score-val">{(studentReport.final_score * 10).toFixed(0)}%</div><div className="meet-report-score-lbl">Overall ({(studentReport.final_score).toFixed(1)}/10)</div></div>
                  </div>
                  {studentReport.weak_areas?.length > 0 && <div className="meet-report-section"><h4>Areas to Improve</h4><ul className="meet-report-list wk">{studentReport.weak_areas.map((w, i) => <li key={i}>{w}</li>)}</ul></div>}
                  {studentReport.missing_skills?.length > 0 && <div className="meet-report-section"><h4>Skills to Learn</h4><ul className="meet-report-list wk">{studentReport.missing_skills.map((s, i) => <li key={i}>{s}</li>)}</ul></div>}
                  {studentReport.improvements?.length > 0 && <div className="meet-report-section"><h4>Improvement Suggestions</h4><ul className="meet-report-list lrn">{studentReport.improvements.map((x, i) => <li key={i}>{x}</li>)}</ul></div>}
                  {studentReport.learning_path?.length > 0 && <div className="meet-report-section"><h4>Learning Path</h4><ul className="meet-report-list lrn">{studentReport.learning_path.map((x, i) => <li key={i}>{x}</li>)}</ul></div>}
                  {studentReport.encouragement && <div className="meet-report-section"><h4>💪 Encouragement</h4><p>{studentReport.encouragement}</p></div>}
                </>}
                {reportTab === 'student' && !studentReport && report && <div className="meet-report-scores"><div className="meet-report-score-card"><div className="meet-report-score-val">{(report.final_score * 10).toFixed(0)}%</div><div className="meet-report-score-lbl">Overall ({(report.final_score).toFixed(1)}/10)</div></div></div>}
                {reportTab === 'summary' && report && <>
                  <div className="meet-report-scores">
                    <div className="meet-report-score-card"><div className="meet-report-score-val">{(report.final_score * 10).toFixed(0)}%</div><div className="meet-report-score-lbl">Technical ({(report.final_score).toFixed(1)}/10)</div></div>
                    <div className="meet-report-score-card"><div className="meet-report-score-val">{report.communication_score !== undefined ? (report.communication_score * 10).toFixed(0) + '%' : '—'}</div><div className="meet-report-score-lbl">Communication</div></div>
                    {report.behavior_score > 0 && <div className="meet-report-score-card"><div className="meet-report-score-val">{(report.behavior_score * 10).toFixed(0)}%</div><div className="meet-report-score-lbl">Behavior</div></div>}
                  </div>
                  {report.strengths?.length > 0 ? (
                    <div className="meet-report-section"><h4>Abilities / Strengths</h4><ul className="meet-report-list str">{report.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul></div>
                  ) : (
                    <div className="meet-report-section"><h4>Abilities / Strengths</h4><p style={{color: '#9ca3af', fontStyle: 'italic', fontSize: '0.9rem', marginBottom: '15px'}}>No specific abilities demonstrated.</p></div>
                  )}
                  {report.weaknesses?.length > 0 && <div className="meet-report-section"><h4>Weaknesses</h4><ul className="meet-report-list wk">{report.weaknesses.map((w, i) => <li key={i}>{w}</li>)}</ul></div>}
                  {report.behavior_summary && <div className="meet-report-section"><h4>Behavior</h4><p>{report.behavior_summary}</p></div>}
                  {report.recommendation && <div className={`meet-recommendation ${(report.recommendation || '').split(':')[0]}`}>{report.recommendation}</div>}
                </>}
                <div style={{ textAlign: 'center', marginTop: 20, display: 'flex', justifyContent: 'center', gap: '12px' }}>
                  <button 
                    className="meet-btn-yes" 
                    onClick={downloadPDF} 
                    disabled={pdfLoading}
                    style={{ background: 'linear-gradient(135deg, #a87ef0 0%, #6366f1 100%)', minWidth: '160px' }}
                  >
                    {pdfLoading ? 'Downloading...' : 'Download Report'}
                  </button>
                  <button className="meet-btn-yes" onClick={goBack}>Return to Dashboard</button>
                </div>
              </div>
            </div>
          )}

          <span className="meet-tile-label">AI Interviewer</span>
        </div>

        {/* === STUDENT TILE (Camera always on) === */}
        {(isActive || state === STATES.GREETING || state === STATES.CONFIRM_START) && (
          <div className="meet-tile">
            {cameraOn ? (
              <>
                <video ref={videoRef} className="meet-student-video" autoPlay playsInline muted />
                <ProctoringDetector
                  videoRef={videoRef}
                  sessionId={sessionId}
                  active={isActive}
                  onWarning={handleProctorWarning}
                  onViolation={handleProctorViolation}
                  onAutoEnd={handleProctorAutoEnd}
                />
              </>
            ) : (
              <div className="meet-student-placeholder">
                <div className="meet-student-avatar">ðŸ“·</div>
                <span className="meet-student-name">Camera required â€” enable to continue</span>
              </div>
            )}
            <span className="meet-tile-label">You</span>
          </div>
        )}
      </div>

      {/* â”€â”€ QUESTION OVERLAY â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      {isActive && currentQuestion && state !== STATES.EVALUATING && (
        <div className="meet-q-overlay">
          <div className="meet-q-card">
            <div className="meet-q-meta">
              <span className="meet-q-topic">{currentQuestion.topic}</span>
              <span className={`meet-badge meet-diff ${currentQuestion.difficulty}`}>{currentQuestion.difficulty}</span>
            </div>
            <p className="meet-q-text">{currentQuestion.question}</p>
          </div>
        </div>
      )}

      {/* ── TRANSCRIPT OVERLAY ── */}
      {isActive && state !== STATES.EVALUATING && (
        <div className={`meet-transcript ${isRecording ? 'active' : ''}`}>
          {(liveTranscript || transcript) || <span className="meet-transcript-ph">Your answer will appear here…</span>}
        </div>
      )}

        </div>

        {/* ── TRANSCRIPT PANEL ── */}
        <TranscriptPanel 
          isOpen={showTranscript} 
          onClose={() => setShowTranscript(false)}
          turns={sessionTurns} 
        />
        
      </div>

      {/* ── FLOATING CONTROL BAR ── */}
      <div className="meet-controls">
        {/* Mic */}
        <button
          className={`meet-ctrl-btn ${isRecording ? 'recording' : 'default'}`}
          onClick={toggleMic}
          disabled={isSpeaking || !isActive || state === STATES.EVALUATING}
          title={isRecording ? 'Stop & Submit' : 'Start Recording'}
        >
          {isRecording ? <StopIcon /> : <MicIcon />}
        </button>

        {/* Camera */}
        <button
          className={`meet-ctrl-btn ${cameraOn ? 'active' : 'default'}`}
          onClick={toggleCamera}
          title={cameraOn ? 'Turn off camera' : 'Turn on camera'}
        >
          {cameraOn ? <CamIcon /> : <CamOffIcon />}
        </button>

        {/* Transcript Toggle (CC) */}
        <button
          className={`meet-ctrl-btn ${showTranscript ? 'cc-active' : 'default'}`}
          onClick={() => setShowTranscript(s => !s)}
          title={showTranscript ? 'Hide Transcript' : 'Show Transcript'}
        >
          <svg className="cc-icon" viewBox="0 0 24 24">
            <rect x="2" y="4" width="20" height="16" rx="2" ry="2" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M10 10a2 2 0 1 0 0 4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M18 10a2 2 0 1 0 0 4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>

        {/* Volume */}
        <button
          className={`meet-ctrl-btn ${volumeOn ? 'active' : 'default'}`}
          onClick={() => { setVolumeOn(v => !v); if (volumeOn) window.speechSynthesis?.cancel(); }}
          title={volumeOn ? 'Mute AI' : 'Unmute AI'}
        >
          <VolumeIcon />
        </button>

        {/* Timer */}
        {isActive && state !== STATES.EVALUATING && (
          <div className={`meet-ctrl-timer ${tCls}`}>
            <div className="meet-ctrl-timer-circle">
              <svg width="44" height="44" viewBox="0 0 44 44">
                <circle className="meet-timer-bg" cx="22" cy="22" r="18" />
                <circle className={`meet-timer-prog ${tCls}`} cx="22" cy="22" r="18" strokeDasharray={circ} strokeDashoffset={off} />
              </svg>
              <span className="meet-ctrl-timer-text">{timeLeft}s</span>
            </div>
          </div>
        )}

        {/* End Call */}
        {(state === STATES.REPORT || state === STATES.CLOSED) ? (
          <button className="meet-ctrl-end" onClick={goBack} title="Close"><PhoneOff /></button>
        ) : (
          <button className="meet-ctrl-end" onClick={handleTerminate} title="End Interview"><PhoneOff /></button>
        )}
      </div>
    </div>
    </DeviceGuard>
  );
}
