import { useState, useEffect, useRef, useCallback } from 'react';
import api from '../utils/api';
import '../style/interview.css';

/**
 * InterviewModal — Full-screen AI interview experience.
 *
 * Features:
 * - Controlled Yes/No greeting handshake
 * - Animated waveform while agent speaks
 * - Timer countdown for answers
 * - Web Speech API for STT (no server upload)
 * - Browser SpeechSynthesis for TTS (free, offline)
 * - Real-time transcript preview
 * - Behavior-reactive agent responses
 * - Final report view
 */

const STATES = {
    LOADING: 'loading',
    GREETING: 'greeting',        // "Are you comfortable?"
    CONFIRM_START: 'confirm_start', // "Can we start?"
    QUESTION: 'question',
    LISTENING: 'listening',
    EVALUATING: 'evaluating',
    REPORT: 'report',
    CLOSED: 'closed',
    ERROR: 'error',
};

// ── SVG Icons ───────────────────────────────────────────────────────────
const MicIcon = () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
        <line x1="12" y1="19" x2="12" y2="23" />
        <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
);

const StopIcon = () => (
    <svg viewBox="0 0 24 24" fill="currentColor">
        <rect x="6" y="6" width="12" height="12" rx="2" />
    </svg>
);

export default function InterviewModal({ onClose, pipeline = null }) {
    const [state, setState] = useState(STATES.LOADING);
    const [config, setConfig] = useState({ max_questions: 15, answer_timeout: 20, silence_timeout: 10 });
    const [sessionId, setSessionId] = useState(null);
    const [agentText, setAgentText] = useState('');
    const [currentQuestion, setCurrentQuestion] = useState(null);
    const [questionNumber, setQuestionNumber] = useState(0);
    const [transcript, setTranscript] = useState('');
    const [isRecording, setIsRecording] = useState(false);
    const [isSpeaking, setIsSpeaking] = useState(false);
    const [timeLeft, setTimeLeft] = useState(0);
    const [report, setReport] = useState(null);
    const [error, setError] = useState('');

    const recognitionRef = useRef(null);
    const silenceTimerRef = useRef(null);
    const userHasSpokenRef = useRef(false);
    const lastSpeechTsRef = useRef(null);

    const SILENCE_SECONDS = 15;
    const SKIP_PATTERNS = [
        'skip',
        "i don't know",
        'i dont know',
        'no idea',
        'not sure',
        'pass',
    ];

    // ── Text-to-Speech (Browser native, free) ────────────────────────
    const speak = useCallback((text, onEnd) => {
        if (!window.speechSynthesis) {
            onEnd?.();
            return;
        }
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 0.95;
        utterance.pitch = 1;
        utterance.volume = 1;
        setIsSpeaking(true);
        utterance.onend = () => {
            setIsSpeaking(false);
            onEnd?.();
        };
        utterance.onerror = () => {
            setIsSpeaking(false);
            onEnd?.();
        };
        window.speechSynthesis.speak(utterance);
    }, []);

    // ── Fetch config and start interview ─────────────────────────────
    useEffect(() => {
        const init = async () => {
            try {
                // If this modal is opened for an assigned job, block only if THAT pipeline/job is already completed.
                if (pipeline?.job_id) {
                    const pipelineRes = await api.get('/pipeline/student');
                    const sameJob = pipelineRes.data?.find(p => p.job_id === pipeline.job_id);
                    if (sameJob?.status === 'AI_COMPLETED') {
                        setError('You have already completed Round 1 (AI interview) for this job. No retakes are allowed.');
                        setState(STATES.ERROR);
                        return;
                    }
                }

                // Fetch config
                const cfgRes = await api.get('/ai/interview/config');
                setConfig(cfgRes.data);

                // Start interview — returns ONLY the greeting
                const jobRole = pipeline?.job_title || pipeline?.job_role || 'Software Developer';
                const res = await api.post('/ai/interview/start', { job_role: jobRole, mode: 'basic' });
                const data = res.data;
                setSessionId(data.session_id);
                setAgentText(data.greeting);
                setState(STATES.GREETING);

                // Speak the greeting
                speak(data.greeting);
            } catch (err) {
                console.error('Interview start error:', err);
                setError(err.response?.data?.detail || 'Failed to start interview');
                setState(STATES.ERROR);
            }
        };
        init();

        return () => {
            clearTimers();
            stopRecording();
            window.speechSynthesis?.cancel();
        };
    }, [pipeline, speak]);

    // ── Handle Yes/No greeting responses ─────────────────────────────
    const handleGreetingResponse = useCallback(async (answer) => {
        if (!sessionId) return;

        try {
            const res = await api.post('/ai/interview/greet', {
                session_id: sessionId,
                answer: answer,
            });
            const data = res.data;
            setAgentText(data.agent_message);
            speak(data.agent_message);

            switch (data.next_step) {
                case 'confirm_start':
                    setState(STATES.CONFIRM_START);
                    break;
                case 'session_closed':
                    setState(STATES.CLOSED);
                    break;
                case 'first_question':
                    if (data.first_question) {
                        setCurrentQuestion(data.first_question);
                        setQuestionNumber(1);
                        // After the agent message is spoken, show the question
                        speak(data.agent_message, () => {
                            setAgentText(data.first_question.question);
                            setState(STATES.QUESTION);
                            speak(data.first_question.question);
                        });
                        return; // Don't speak again below
                    }
                    break;
                default:
                    break;
            }
        } catch (err) {
            console.error('Greeting response error:', err);
            setError(err.response?.data?.detail || 'Failed to process response');
            setState(STATES.ERROR);
        }
    }, [sessionId, speak]);

    const clearTimers = () => {
        if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
    };

    // ── Speech Recognition (Web Speech API, free) ────────────────────
    const startRecording = useCallback(() => {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            setError('Speech recognition is not supported in this browser. Please use Chrome.');
            return;
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onresult = (event) => {
            let finalDelta = '';
            for (let i = 0; i < event.results.length; i++) {
                const result = event.results[i];
                if (result.isFinal) {
                    finalDelta += result[0].transcript + ' ';
                }
            }

            const delta = finalDelta.trim();
            if (delta) {
                setTranscript(prev => (`${(prev || '').trim()} ${delta}`).trim());
                userHasSpokenRef.current = true;
                lastSpeechTsRef.current = Date.now();
            }

            const current = (transcript || '').trim();
            const lower = current.toLowerCase();
            if (SKIP_PATTERNS.some(p => lower.includes(p))) {
                stopRecording();
                submitAnswer(current);
                return;
            }

            // Reset silence timer on speech
            if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
            silenceTimerRef.current = setTimeout(() => {
                // End only if user has started speaking, then we got SILENCE_SECONDS of silence
                if (!userHasSpokenRef.current) return;
                stopRecording();
                const finalText = (transcript || '').trim();
                submitAnswer(finalText);
            }, SILENCE_SECONDS * 1000);
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            if (event.error !== 'no-speech') {
                setIsRecording(false);
            }
        };

        recognition.onend = () => {
            setIsRecording(false);
        };

        recognitionRef.current = recognition;
        recognition.start();
        setIsRecording(true);
        setTranscript('');
        userHasSpokenRef.current = false;
        lastSpeechTsRef.current = null;
    }, []);

    const stopRecording = useCallback(() => {
        if (recognitionRef.current) {
            recognitionRef.current.stop();
            recognitionRef.current = null;
        }
        setIsRecording(false);
    }, []);

    const toggleRecording = useCallback(() => {
        if (isRecording) {
            stopRecording();
            if (transcript.trim()) {
                submitAnswer(transcript.trim());
            }
        } else {
            startRecording();
        }
    }, [isRecording, transcript, startRecording, stopRecording]);

    // ── End Interview ────────────────────────────────────────────────
    const endInterview = useCallback(async () => {
        if (!sessionId) return;
        setState(STATES.EVALUATING);
        setAgentText('Generating your final report...');

        try {
            const res = await api.post('/ai/interview/end', {
                session_id: sessionId,
            });
            setReport(res.data.report);
            setState(STATES.REPORT);
        } catch (err) {
            console.error('End interview error:', err);
            setError(err.response?.data?.detail || 'Failed to end interview');
            setState(STATES.ERROR);
        }
    }, [sessionId]);

    // ── Submit Answer ────────────────────────────────────────────────
    const submitAnswer = useCallback(async (answerText) => {
        if (!currentQuestion || !sessionId) return;

        clearTimers();
        stopRecording();
        setState(STATES.EVALUATING);
        setAgentText('Evaluating your answer...');

        try {
            const res = await api.post('/ai/interview/answer', {
                session_id: sessionId,
                question_id: currentQuestion.question_id,
                answer_text: answerText,
            });

            const data = res.data;
            const agentResponse = data.agent_response || '';

            if (data.next_action === 'end') {
                setAgentText(agentResponse + ' Let me prepare your final report...');
                speak(agentResponse, async () => {
                    await endInterview();
                });
            } else {
                setAgentText(agentResponse);
                speak(agentResponse, () => {
                    if (data.next_question) {
                        setCurrentQuestion(data.next_question);
                        setQuestionNumber(prev => prev + 1);
                        setTranscript('');
                        setAgentText(data.next_question.question);
                        setState(STATES.QUESTION);
                        speak(data.next_question.question);
                    }
                });
            }
        } catch (err) {
            console.error('Submit answer error:', err);
            setError(err.response?.data?.detail || 'Failed to submit answer');
            setState(STATES.ERROR);
        }
    }, [currentQuestion, sessionId, clearTimers, stopRecording, speak, endInterview]);

    // ── Terminate Interview Manually ─────────────────────────────────
    const handleTerminate = useCallback(async () => {
        clearTimers();
        stopRecording();
        window.speechSynthesis.cancel();
        setIsSpeaking(false);
        setState(STATES.CLOSED);
        setAgentText("Interview is terminated.");

        // Ensure backend session is properly closed
        if (sessionId) {
            try {
                await api.post('/ai/interview/end', { session_id: sessionId });
            } catch (e) {
                console.error('Terminate cleanup error:', e);
            }
        }
    }, [sessionId, clearTimers, stopRecording]);

    // ── Timer circle ─────────────────────────────────────────────────
    const circumference = 2 * Math.PI * 24;
    const timerOffset = circumference;
    const timerClass = '';

    // ── Render ───────────────────────────────────────────────────────
    return (
        <div className="interview-modal-overlay" onClick={(e) => e.target === e.currentTarget && (state === STATES.REPORT || state === STATES.CLOSED) && onClose()}>
            <div className="interview-modal">
                {/* Header */}
                <div className="interview-header">
                    <div className="interview-header-left">
                        <div className="interview-status-dot" />
                        <span className="interview-header-title">AI Interview</span>
                    </div>
                    <div className="interview-header-right">
                        {questionNumber > 0 && (
                            <span className="interview-q-counter">
                                Q{questionNumber} / {config.max_questions}
                            </span>
                        )}
                        <button
                            className="interview-end-btn"
                            onClick={() => (state === STATES.REPORT || state === STATES.CLOSED) ? onClose() : handleTerminate()}
                        >
                            {(state === STATES.REPORT || state === STATES.CLOSED) ? 'Close' : 'End Interview'}
                        </button>
                    </div>
                </div>

                {/* Body */}
                <div className="interview-body">
                    {/* Loading */}
                    {state === STATES.LOADING && (
                        <div className="interview-loading">
                            <div className="interview-loading-spinner" />
                            <p className="interview-loading-text">Starting your interview session...</p>
                        </div>
                    )}

                    {/* Error */}
                    {state === STATES.ERROR && (
                        <div className="interview-loading">
                            <p style={{ color: 'var(--color-error)', fontSize: '1rem' }}>{error}</p>
                            <button className="btn btn-secondary" onClick={onClose}>Close</button>
                        </div>
                    )}

                    {/* Greeting: "Are you comfortable?" */}
                    {state === STATES.GREETING && (
                        <div className="interview-greeting-area">
                            <div className={`interview-waveform ${isSpeaking ? '' : 'paused'}`}>
                                {[...Array(7)].map((_, i) => (
                                    <div key={i} className="interview-waveform-bar" />
                                ))}
                            </div>
                            <p className="interview-agent-text">{agentText}</p>
                            <div className="interview-greeting-buttons">
                                <button
                                    className="interview-yes-btn"
                                    onClick={() => handleGreetingResponse('yes')}
                                    disabled={isSpeaking}
                                >
                                    Yes, I'm comfortable
                                </button>
                                <button
                                    className="interview-no-btn"
                                    onClick={() => handleGreetingResponse('no')}
                                    disabled={isSpeaking}
                                >
                                    No, not right now
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Confirm Start: "Can we start?" */}
                    {state === STATES.CONFIRM_START && (
                        <div className="interview-greeting-area">
                            <div className={`interview-waveform ${isSpeaking ? '' : 'paused'}`}>
                                {[...Array(7)].map((_, i) => (
                                    <div key={i} className="interview-waveform-bar" />
                                ))}
                            </div>
                            <p className="interview-agent-text">{agentText}</p>
                            <div className="interview-greeting-buttons">
                                <button
                                    className="interview-yes-btn"
                                    onClick={() => handleGreetingResponse('yes')}
                                    disabled={isSpeaking}
                                >
                                    Yes, let's start!
                                </button>
                                <button
                                    className="interview-no-btn"
                                    onClick={() => handleGreetingResponse('no')}
                                    disabled={isSpeaking}
                                >
                                    No, schedule later
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Session Closed */}
                    {state === STATES.CLOSED && (
                        <div className="interview-greeting-area">
                            <p className="interview-agent-text">{agentText}</p>
                            <button className="interview-yes-btn" onClick={onClose} style={{ marginTop: '20px' }}>
                                Close
                            </button>
                        </div>
                    )}

                    {/* Active Interview States */}
                    {[STATES.QUESTION, STATES.LISTENING, STATES.EVALUATING].includes(state) && (
                        <>
                            {/* Agent Speech */}
                            <div className="interview-agent-area">
                                <div className={`interview-waveform ${isSpeaking ? '' : 'paused'}`}>
                                    {[...Array(7)].map((_, i) => (
                                        <div key={i} className="interview-waveform-bar" />
                                    ))}
                                </div>
                                <p className="interview-agent-text">{agentText}</p>
                            </div>

                            {/* Question Card */}
                            {currentQuestion && state !== STATES.EVALUATING && (
                                <div className="interview-question-card">
                                    <div className="interview-question-label">
                                        Question {questionNumber} • {currentQuestion.topic} • {currentQuestion.difficulty}
                                    </div>
                                    <p className="interview-question-text">{currentQuestion.question}</p>
                                </div>
                            )}

                            {/* Timer + Mic */}
                            {state !== STATES.EVALUATING && (
                                <div className="interview-mic-area">
                                    {/* Timer */}
                                    <div className="interview-timer">
                                        <div className="interview-timer-circle">
                                            <svg width="56" height="56" viewBox="0 0 56 56">
                                                <circle className="interview-timer-circle-bg" cx="28" cy="28" r="24" />
                                                <circle
                                                    className={`interview-timer-circle-progress ${timerClass}`}
                                                    cx="28" cy="28" r="24"
                                                    strokeDasharray={circumference}
                                                    strokeDashoffset={timerOffset}
                                                />
                                            </svg>
                                            <span className="interview-timer-text">{timeLeft}s</span>
                                        </div>
                                    </div>

                                    {/* Mic Button */}
                                    <button
                                        className={`interview-mic-btn ${isRecording ? 'recording' : ''}`}
                                        onClick={toggleRecording}
                                        disabled={isSpeaking || state === STATES.EVALUATING}
                                    >
                                        {isRecording ? <StopIcon /> : <MicIcon />}
                                    </button>
                                    <span className="interview-mic-label">
                                        {isRecording ? 'Tap to stop & submit' : 'Tap to start answering'}
                                    </span>

                                    {/* Transcript */}
                                    <div className={`interview-transcript ${isRecording ? 'active' : ''}`}>
                                        {transcript || (
                                            <span className="interview-transcript-placeholder">
                                                Your answer will appear here...
                                            </span>
                                        )}
                                    </div>
                                </div>
                            )}

                            {/* Evaluating spinner */}
                            {state === STATES.EVALUATING && (
                                <div className="interview-loading">
                                    <div className="interview-loading-spinner" />
                                    <p className="interview-loading-text">Analyzing your response...</p>
                                </div>
                            )}
                        </>
                    )}

                    {/* Report */}
                    {state === STATES.REPORT && report && (
                        <div className="interview-report">
                            <h3>Interview Report</h3>

                            <div className="interview-report-scores">
                                <div className="interview-report-score">
                                    <div className="interview-report-score-value">
                                        {report.final_score?.toFixed(1)}
                                    </div>
                                    <div className="interview-report-score-label">Technical</div>
                                </div>
                                <div className="interview-report-score">
                                    <div className="interview-report-score-value">
                                        {report.communication_score?.toFixed(1) || '—'}
                                    </div>
                                    <div className="interview-report-score-label">Communication</div>
                                </div>
                            </div>

                            {report.strengths?.length > 0 && (
                                <div className="interview-report-section">
                                    <h4>Strengths</h4>
                                    <ul className="interview-report-list strengths">
                                        {report.strengths.map((s, i) => <li key={i}>{s}</li>)}
                                    </ul>
                                </div>
                            )}

                            {report.weaknesses?.length > 0 && (
                                <div className="interview-report-section">
                                    <h4>Areas for Improvement</h4>
                                    <ul className="interview-report-list weaknesses">
                                        {report.weaknesses.map((w, i) => <li key={i}>{w}</li>)}
                                    </ul>
                                </div>
                            )}

                            {report.behavior_summary && (
                                <div className="interview-report-section">
                                    <h4>Behavior Analysis</h4>
                                    <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>
                                        {report.behavior_summary}
                                    </p>
                                </div>
                            )}

                            <div className="interview-report-recommendation">
                                {report.recommendation}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
