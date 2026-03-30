import { useState, useEffect, useRef, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import api from '../utils/api';
import ProctoringDetector from '../components/ProctoringDetector';
import DeviceGuard from '../components/DeviceGuard';
import '../style/interviewLive.css';

/**
 * InterviewLive — Google Meet-Style Full-Screen AI Interview.
 *
 * Layout:
 * ┌─────────────────────────────────────────┐
 * │              TOP BAR                     │
 * ├───────────────────┬──────────────────────┤
 * │  AI INTERVIEWER   │   STUDENT CAMERA     │
 * │  avatar+waveform  │   webcam preview     │
 * ├───────────────────┴──────────────────────┤
 * │  QUESTION OVERLAY (glassmorphism)        │
 * │  TRANSCRIPT OVERLAY                      │
 * ├──────────────────────────────────────────┤
 * │  FLOATING CONTROL BAR                    │
 * │  🎤  📹  🔊  ⏱  ⚙  🔴                  │
 * └──────────────────────────────────────────┘
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

/* ── SVG Icons ────────────────────────────────────────────────────────── */

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

  /* ── state ─────────────────────────────────────────────────────────── */
  const [state, setState]   = useState(STATES.LOADING);
  const [config, setConfig] = useState({ max_questions: 15, min_questions: 5, answer_timeout: 20, silence_timeout: 10 });
  const [sessionId, setSessionId]     = useState(null);
  const [agentText, setAgentText]     = useState('');
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [questionNumber, setQuestionNumber]   = useState(0);
  const [transcript, setTranscript]   = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isSpeaking, setIsSpeaking]   = useState(false);
  const [timeLeft, setTimeLeft]       = useState(0);
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
  const proctorWarningTimer = useRef(null);

  const recognitionRef  = useRef(null);
  const timerRef        = useRef(null);
  const silenceTimerRef = useRef(null);
  const videoRef        = useRef(null);
  const streamRef       = useRef(null);
  const hasStartedRef   = useRef(false);
  const finalTranscriptRef = useRef('');         // accumulates final results across STT segments
  const isListeningRef     = useRef(false);      // tracks if we WANT to keep listening
  const [rulesAccepted, setRulesAccepted] = useState(false);

  /* ── fullscreen is now handled by DashboardLayout.jsx ──────────────── */

  /* ── utils ─────────────────────────────────────────────────────────── */
  const goBack = useCallback(() => navigate('/dashboard/interview'), [navigate]);

  const clearTimers = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
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

  /* ── camera toggle (camera is MANDATORY — cannot be turned off) ────── */
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
      // Camera must stay on during interview — show warning
      setProctorWarning('⚠️ Camera is required for the interview. You cannot turn it off.');
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

  /* ── TTS ────────────────────────────────────────────────────────────── */
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

  /* ── end / recording ───────────────────────────────────────────────── */
  const stopRecording = useCallback(() => {
    isListeningRef.current = false;
    if (recognitionRef.current) {
      try { recognitionRef.current.abort(); } catch {}
      recognitionRef.current = null;
    }
    setIsRecording(false);
  }, []);

  const endInterview = useCallback(async (reason = 'normal') => {
    if (!sessionId) return;
    clearTimers();
    stopRecording();
    window.speechSynthesis?.cancel();
    setIsSpeaking(false);
    
    setState(STATES.EVALUATING);
    setAgentText('Generating report...');
    
    try {
      const r = await api.post('/ai/interview/end', { session_id: sessionId, ended_reason: reason });
      setReport(r.data.report);
      await fetchStudentReport();
      setState(STATES.REPORT);
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed');
      setState(STATES.ERROR);
    }
  }, [sessionId, stopRecording, clearTimers, fetchStudentReport]);

  /* ── proctoring callbacks (must be after endInterview) ──────────────── */
  const handleProctorWarning = useCallback((type, message) => {
    setProctorWarning(message);
    if (proctorWarningTimer.current) clearTimeout(proctorWarningTimer.current);
    proctorWarningTimer.current = setTimeout(() => setProctorWarning(null), 5000);
  }, []);

  const handleProctorViolation = useCallback((type, message) => {
    setProctorWarning('🔴 ' + message);
  }, []);

  const handleProctorAutoEnd = useCallback(async (reason) => {
    setProctorWarning(`🔴 Interview terminated: ${reason.replace(/_/g, ' ')}`);
    setTimeout(async () => {
      await endInterview(reason);
    }, 2000);
  }, [endInterview]);

  const handleTabSwitch = useCallback(async () => {
    if (![STATES.QUESTION, STATES.LISTENING, STATES.EVALUATING].includes(state)) return;
    setShowTabWarning(true);
    await endInterview('TAB_SWITCH');
    navigate('/dashboard/interview');
  }, [state, endInterview, navigate]);

  const handleTerminate = useCallback(async () => {
    clearTimers();
    stopRecording();
    window.speechSynthesis?.cancel();
    setIsSpeaking(false);
    setState(STATES.CLOSED);
    setAgentText('Interview ended.');
    if (sessionId) {
      try {
        await api.post('/ai/interview/end', { session_id: sessionId, ended_reason: 'USER_TERMINATED' });
      } catch (e) {
        console.error('Terminate cleanup error:', e);
      }
    }
  }, [sessionId, stopRecording, clearTimers]);

  /* ── submit answer ─────────────────────────────────────────────────── */
  const submitAnswer = useCallback(async (txt) => {
    if (!currentQuestion || !sessionId) return;
    clearTimers();
    stopRecording();
    setState(STATES.EVALUATING);
    setAgentText('Analyzing your response...');
    try {
      const r = await api.post('/ai/interview/answer', { 
        session_id: sessionId, 
        question_id: currentQuestion.question_id, 
        answer_text: txt 
      });
      const d = r.data;
      setRunningScore(d.running_avg_score || 0);
      setDifficulty(d.next_difficulty || 'medium');
      
      if (d.next_action === 'early_exit') {
        setAgentText(d.early_exit_message || 'Interview concluded.');
        speak(d.early_exit_message || 'Interview concluded.', () => fetchReport());
        setState(STATES.EARLY_EXIT);
      } else if (d.next_action === 'end') {
        setAgentText((d.agent_response || '') + ' Preparing your report...');
        speak(d.agent_response, () => endInterview());
      } else {
        setAgentText(d.agent_response);
        speak(d.agent_response, () => {
          if (d.next_question) {
            setCurrentQuestion(d.next_question);
            setQuestionNumber(p => p + 1);
            setTranscript('');
            setDifficulty(d.next_question.difficulty || 'medium');
            setAgentText(d.next_question.question);
            setState(STATES.QUESTION);
            speak(d.next_question.question, () => startTimer(config.answer_timeout));
          }
        });
      }
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed');
      setState(STATES.ERROR);
    }
  }, [currentQuestion, sessionId, config.answer_timeout, stopRecording, clearTimers, speak, fetchReport, endInterview]);

  const handleTimeout = useCallback(() => {
    if (transcript.trim()) {
      submitAnswer(transcript);
    } else {
      setAgentText("Are you there? Can you respond?");
      speak("Are you there?", () => startTimer(config.answer_timeout));
    }
  }, [transcript, config.answer_timeout, submitAnswer, speak]);

  const startTimer = useCallback((s) => {
    clearTimers();
    setTimeLeft(s);
    timerRef.current = setInterval(() => {
      setTimeLeft(p => {
        if (p <= 1) {
          clearInterval(timerRef.current);
          handleTimeout();
          return 0;
        }
        return p - 1;
      });
    }, 1000);
  }, [clearTimers, handleTimeout]);

  const startRecording = useCallback(() => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      setError('Use Chrome for speech.');
      return;
    }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    finalTranscriptRef.current = '';
    isListeningRef.current = true;

    const createRecognition = () => {
      const r = new SR();
      r.continuous = true;
      r.interimResults = true;
      r.lang = 'en-US';

      r.onresult = e => {
        let segmentFinal = '', interim = '';
        for (let i = 0; i < e.results.length; i++) {
          if (e.results[i].isFinal) segmentFinal += e.results[i][0].transcript + ' ';
          else interim += e.results[i][0].transcript;
        }
        // Accumulate final results across segments
        const fullText = finalTranscriptRef.current + segmentFinal;
        if (segmentFinal) finalTranscriptRef.current = fullText;
        setTranscript(fullText + interim);

        // Silence timeout → auto-submit
        if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
        silenceTimerRef.current = setTimeout(() => {
          const accumulated = finalTranscriptRef.current.trim();
          if (accumulated) {
            isListeningRef.current = false;
            stopRecording();
            submitAnswer(accumulated);
          }
        }, config.silence_timeout * 1000);
      };

      r.onerror = e => {
        if (e.error !== 'no-speech' && e.error !== 'aborted') {
          setIsRecording(false);
          isListeningRef.current = false;
        }
      };

      // Auto-restart when browser stops recognition (60s limit)
      r.onend = () => {
        if (isListeningRef.current) {
          // Browser stopped but we still want to listen — restart
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
    setTranscript('');
  }, [config.silence_timeout, stopRecording, submitAnswer]);

  const toggleMic = useCallback(() => {
    if (isRecording) {
      isListeningRef.current = false;
      stopRecording();
      const accumulated = finalTranscriptRef.current.trim() || transcript.trim();
      if (accumulated) submitAnswer(accumulated);
    } else {
      startRecording();
    }
  }, [isRecording, transcript, startRecording, stopRecording, submitAnswer]);

  /* ── greeting ───────────────────────────────────────────────────────── */
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
        setCurrentQuestion(d.first_question);
        setQuestionNumber(1);
        setDifficulty(d.first_question.difficulty || 'medium');
        speak(d.agent_message, () => {
          setAgentText(d.first_question.question);
          setState(STATES.QUESTION);
          speak(d.first_question.question, () => startTimer(config.answer_timeout));
        });
        return;
      }
    } catch (e) {
      setError(e.response?.data?.detail || 'Error');
      setState(STATES.ERROR);
    }
  }, [sessionId, config.answer_timeout, speak, startTimer]);

  /* ── Effects ────────────────────────────────────────────────────────── */
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
          }
        }
        const c = await api.get('/ai/interview/config');
        setConfig(c.data);
        const r = await api.post('/ai/interview/start', { 
            job_role: jr,
            job_id: jobIdUrl || null,
            interview_type: interviewMode
        });
        setSessionId(r.data.session_id);
        setAgentText(r.data.greeting);
        setState(STATES.RULES);        // Show rules first, then greeting
      } catch (e) { setError(e.response?.data?.detail || 'Failed to start'); setState(STATES.ERROR); }
    })();
    return () => { clearTimers(); stopRecording(); window.speechSynthesis?.cancel(); streamRef.current?.getTracks().forEach(t => t.stop()); };
  }, [jobIdUrl, modeParam, speak, clearTimers, stopRecording, startCamera]);

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

  /* ── helper circle ──────────────────────────────────────────────────── */
  const circ = 2 * Math.PI * 18;
  const off  = circ - (timeLeft / config.answer_timeout) * circ;
  const tCls = timeLeft <= 5 ? 'danger' : timeLeft <= 10 ? 'warn' : '';

  const isActive = [STATES.QUESTION, STATES.LISTENING, STATES.EVALUATING].includes(state);

  /* ═══════════════════════════════════════════════════════════════════════
     RENDER
     ═══════════════════════════════════════════════════════════════════════ */
  /* ── accept rules handler ───────────────────────────────────────────── */
  const handleAcceptRules = useCallback(() => {
    setState(STATES.GREETING);
    speak(agentText);
  }, [agentText, speak]);

  return (
    <DeviceGuard>
    <div className="meet-root">

      {/* ── Proctoring Warning Banner ──────────────────────────────────── */}
      {proctorWarning && (
        <div className="meet-proctor-warning">
          <span>{proctorWarning}</span>
          <button onClick={() => setProctorWarning(null)}>✕</button>
        </div>
      )}

      {/* ── Tab-switch warning ─────────────────────────────────────────── */}
      {showTabWarning && (
        <div className="meet-warn-overlay">
          <div className="meet-warn-icon">⚠️</div>
          <div className="meet-warn-title">TAB SWITCH DETECTED</div>
          <div className="meet-warn-text">Please stay on the interview screen. Switching tabs is monitored and may affect your evaluation.</div>
          <div className="meet-warn-count">Warnings: {tabSwitchCount}</div>
        </div>
      )}

      {/* ── TOP BAR ────────────────────────────────────────────────────── */}
      <div className="meet-topbar">
        <div className="meet-topbar-left">
          <div className={`meet-live-dot ${state === STATES.ERROR ? 'err' : state === STATES.EARLY_EXIT ? 'warn' : ''}`} />
          <span className="meet-brand">AI INTERVIEW</span>
        </div>
        <div className="meet-topbar-center">
          {questionNumber > 0 && <>
            <span className="meet-badge">Q{questionNumber} / {config.max_questions}</span>
            <span className={`meet-badge meet-diff ${difficulty}`}>{difficulty}</span>
          </>}
          {runningScore > 0 && <span className="meet-badge">{(runningScore * 100).toFixed(0)}%</span>}
        </div>
        <div className="meet-topbar-right">
          {tabSwitchCount > 0 && <span className="meet-badge" style={{ color: '#f59e0b' }}>⚠ {tabSwitchCount}</span>}
        </div>
      </div>

      {/* ── VIDEO GRID ─────────────────────────────────────────────────── */}
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

          {/* ── RULES & REGULATIONS ──────────────────────────────────── */}
          {state === STATES.RULES && (
            <div className="meet-state-center" style={{ overflowY: 'auto', padding: 20 }}>
              <div className="meet-rules-card">
                <div className="meet-rules-icon">📋</div>
                <h2 className="meet-rules-title">Interview Rules & Regulations</h2>
                <p className="meet-rules-subtitle">Please read and accept before starting</p>
                <ul className="meet-rules-list">
                  <li className="meet-rules-item meet-rules-ok"><span className="meet-rules-emoji">📹</span> Keep your camera <strong>ON</strong> at all times</li>
                  <li className="meet-rules-item meet-rules-ok"><span className="meet-rules-emoji">🎤</span> Use a clear microphone for voice answers</li>
                  <li className="meet-rules-item meet-rules-ok"><span className="meet-rules-emoji">👤</span> Only <strong>one person</strong> must be visible in the frame</li>
                  <li className="meet-rules-item meet-rules-ok"><span className="meet-rules-emoji">👀</span> Look at the camera — do not look away</li>
                  <li className="meet-rules-item meet-rules-no"><span className="meet-rules-emoji">🚫</span> <strong>No tab switching</strong> — interview will terminate</li>
                  <li className="meet-rules-item meet-rules-no"><span className="meet-rules-emoji">📱</span> <strong>No mobile phones</strong> visible — interview will terminate</li>
                  <li className="meet-rules-item meet-rules-no"><span className="meet-rules-emoji">📖</span> <strong>No books or notes</strong> — they will be detected</li>
                  <li className="meet-rules-item meet-rules-no"><span className="meet-rules-emoji">🖱️</span> <strong>No copy/paste or right-click</strong> — blocked</li>
                  <li className="meet-rules-item meet-rules-no"><span className="meet-rules-emoji">🔌</span> <strong>No external devices</strong> (tablets, remotes) — detected & terminated</li>
                  <li className="meet-rules-item meet-rules-warn"><span className="meet-rules-emoji">🤖</span> AI proctoring is <strong>active throughout</strong> the interview</li>
                  <li className="meet-rules-item meet-rules-warn"><span className="meet-rules-emoji">⏱️</span> Each question has a time limit — answer within the allotted time</li>
                </ul>
                <label className="meet-rules-checkbox">
                  <input type="checkbox" checked={rulesAccepted} onChange={e => setRulesAccepted(e.target.checked)} />
                  <span>I have read and agree to all the rules above</span>
                </label>
                <button className="meet-btn-yes meet-rules-btn" disabled={!rulesAccepted} onClick={handleAcceptRules}>
                  I Understand & Agree — Start Interview
                </button>
              </div>
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
                    <div className="meet-report-score-card"><div className="meet-report-score-val">{(studentReport.final_score * 100).toFixed(0)}%</div><div className="meet-report-score-lbl">Overall</div></div>
                  </div>
                  {studentReport.weak_areas?.length > 0 && <div className="meet-report-section"><h4>Areas to Improve</h4><ul className="meet-report-list wk">{studentReport.weak_areas.map((w, i) => <li key={i}>{w}</li>)}</ul></div>}
                  {studentReport.missing_skills?.length > 0 && <div className="meet-report-section"><h4>Skills to Learn</h4><ul className="meet-report-list wk">{studentReport.missing_skills.map((s, i) => <li key={i}>{s}</li>)}</ul></div>}
                  {studentReport.improvements?.length > 0 && <div className="meet-report-section"><h4>Improvement Suggestions</h4><ul className="meet-report-list lrn">{studentReport.improvements.map((x, i) => <li key={i}>{x}</li>)}</ul></div>}
                  {studentReport.learning_path?.length > 0 && <div className="meet-report-section"><h4>Learning Path</h4><ul className="meet-report-list lrn">{studentReport.learning_path.map((x, i) => <li key={i}>{x}</li>)}</ul></div>}
                  {studentReport.encouragement && <div className="meet-report-section"><h4>💪 Encouragement</h4><p>{studentReport.encouragement}</p></div>}
                </>}
                {reportTab === 'student' && !studentReport && report && <div className="meet-report-scores"><div className="meet-report-score-card"><div className="meet-report-score-val">{report.final_score > 1 ? report.final_score.toFixed(1) : (report.final_score * 100).toFixed(0) + '%'}</div><div className="meet-report-score-lbl">Overall</div></div></div>}
                {reportTab === 'summary' && report && <>
                  <div className="meet-report-scores">
                    <div className="meet-report-score-card"><div className="meet-report-score-val">{report.final_score > 1 ? report.final_score.toFixed(1) : (report.final_score * 100).toFixed(0) + '%'}</div><div className="meet-report-score-lbl">Technical</div></div>
                    <div className="meet-report-score-card"><div className="meet-report-score-val">{report.communication_score !== undefined ? (report.communication_score * 100).toFixed(0) + '%' : '—'}</div><div className="meet-report-score-lbl">Communication</div></div>
                    {report.behavior_score > 0 && <div className="meet-report-score-card"><div className="meet-report-score-val">{(report.behavior_score * 100).toFixed(0)}%</div><div className="meet-report-score-lbl">Behavior</div></div>}
                  </div>
                  {report.strengths?.length > 0 && <div className="meet-report-section"><h4>Strengths</h4><ul className="meet-report-list str">{report.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul></div>}
                  {report.weaknesses?.length > 0 && <div className="meet-report-section"><h4>Weaknesses</h4><ul className="meet-report-list wk">{report.weaknesses.map((w, i) => <li key={i}>{w}</li>)}</ul></div>}
                  {report.behavior_summary && <div className="meet-report-section"><h4>Behavior</h4><p>{report.behavior_summary}</p></div>}
                  {report.recommendation && <div className={`meet-recommendation ${(report.recommendation || '').split(':')[0]}`}>{report.recommendation}</div>}
                </>}
                <div style={{ textAlign: 'center', marginTop: 20 }}><button className="meet-btn-yes" onClick={goBack}>Return to Dashboard</button></div>
              </div>
            </div>
          )}

          <span className="meet-tile-label">AI Interviewer</span>
        </div>

        {/* === STUDENT TILE (Camera always on) === */}
        {(isActive || state === STATES.GREETING || state === STATES.CONFIRM_START || state === STATES.RULES) && (
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
                <div className="meet-student-avatar">📷</div>
                <span className="meet-student-name">Camera required — enable to continue</span>
              </div>
            )}
            <span className="meet-tile-label">You</span>
          </div>
        )}
      </div>

      {/* ── QUESTION OVERLAY ──────────────────────────────────────────── */}
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

      {/* ── TRANSCRIPT OVERLAY ────────────────────────────────────────── */}
      {isActive && state !== STATES.EVALUATING && (
        <div className={`meet-transcript ${isRecording ? 'active' : ''}`}>
          {transcript || <span className="meet-transcript-ph">Your answer will appear here…</span>}
        </div>
      )}

      {/* ── FLOATING CONTROL BAR ──────────────────────────────────────── */}
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
