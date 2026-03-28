import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { FiMic, FiCpu, FiActivity, FiZap, FiShield, FiMessageCircle, FiClock, FiCheckCircle, FiXCircle } from 'react-icons/fi';
import api from '../utils/api';
import '../style/interview.css';

const FEATURES = [
    { icon: FiMic, title: 'Voice-Enabled', desc: 'Speak naturally — our AI listens and responds in real-time.' },
    { icon: FiCpu, title: 'AI-Powered', desc: 'Powered by advanced LLMs tuned for technical interviews.' },
    { icon: FiActivity, title: 'Adaptive', desc: 'Difficulty adjusts based on your performance dynamically.' },
    { icon: FiZap, title: 'Instant Feedback', desc: 'Get scored on clarity, depth, confidence & technical accuracy.' },
    { icon: FiShield, title: 'Behavior-Aware', desc: 'Detects communication style & provides soft-skill feedback.' },
    { icon: FiMessageCircle, title: 'Conversational', desc: 'Feels like a real interview — not a quiz.' },
];

const STATUS_CONFIG = {
    completed: { label: 'Completed', color: 'var(--color-success)', icon: FiCheckCircle },
    active: { label: 'Active', color: 'var(--color-secondary)', icon: FiClock },
    cancelled: { label: 'Cancelled', color: 'var(--color-text-muted)', icon: FiXCircle },
    early_exit: { label: 'Early Exit', color: 'var(--color-warning)', icon: FiActivity },
    tab_switch: { label: 'Tab Switch', color: 'var(--color-danger)', icon: FiXCircle },
    paused: { label: 'Paused', color: 'var(--color-warning)', icon: FiClock },
};

export default function AIInterview() {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [history, setHistory] = useState([]);
    const [loadingHistory, setLoadingHistory] = useState(true);

    // Fetch interview history
    useEffect(() => {
        const fetchHistory = async () => {
            try {
                const res = await api.get('/ai/interview/history');
                setHistory(res.data.sessions || []);
            } catch (err) {
                console.error('Failed to fetch interview history:', err);
            } finally {
                setLoadingHistory(false);
            }
        };
        fetchHistory();
    }, []);

    const formatDate = (dateStr) => {
        if (!dateStr) return '—';
        return new Date(dateStr).toLocaleDateString('en-IN', {
            day: 'numeric', month: 'short', year: 'numeric',
            hour: '2-digit', minute: '2-digit',
        });
    };

    const handleDelete = async (sessionId, e) => {
        e.stopPropagation(); // prevent card click if any
        if (!window.confirm("Are you sure you want to delete this interview record? This action cannot be undone.")) return;

        try {
            await api.delete(`/ai/interview/session/${sessionId}`);
            setHistory(prev => prev.filter(s => s.session_id !== sessionId));
        } catch (err) {
            console.error('Failed to delete session:', err);
            alert(err.response?.data?.detail || "Failed to delete from history.");
        }
    };

    return (
        <div className="dashboard-content fade-in-up">
            {/* Hero Section */}
            <div className="iv-hero">
                <div className="iv-hero-glow" />
                <div className="iv-hero-content">
                    <div className="iv-hero-badge">AI-Powered Practice</div>
                    <h1 className="iv-hero-title">
                        Ace Your Next <span className="gradient-text">Interview</span>
                    </h1>
                    <p className="iv-hero-subtitle">
                        Practice with our AI interviewer — voice-enabled, behavior-reactive, fully dynamic.
                        Tailored to your skills profile and designed to simulate real-world technical interviews.
                    </p>
                    <button
                        className="iv-hero-btn"
                        onClick={() => navigate('/dashboard/interview/live?mode=practice')}
                    >
                        <span className="iv-hero-btn-pulse" />
                        <FiMic className="iv-hero-btn-icon" />
                        <span>Start Interview</span>
                    </button>
                </div>

                {/* Floating Orb */}
                <div className="iv-hero-orb">
                    <div className="iv-orb-ring iv-orb-ring-1" />
                    <div className="iv-orb-ring iv-orb-ring-2" />
                    <div className="iv-orb-ring iv-orb-ring-3" />
                    <div className="iv-orb-core">
                        <FiMic />
                    </div>
                </div>
            </div>

            {/* Features Grid */}
            <div className="iv-features">
                {FEATURES.map((feat, i) => (
                    <div key={i} className="iv-feature-card" style={{ animationDelay: `${i * 0.08}s` }}>
                        <div className="iv-feature-icon">
                            <feat.icon />
                        </div>
                        <h4>{feat.title}</h4>
                        <p>{feat.desc}</p>
                    </div>
                ))}
            </div>

            {/* How It Works */}
            <div className="iv-steps">
                <h3 className="iv-section-title">How It Works</h3>
                <div className="iv-steps-track">
                    <div className="iv-step">
                        <div className="iv-step-number">1</div>
                        <h4>Start Session</h4>
                        <p>Click the button above to begin your AI interview session.</p>
                    </div>
                    <div className="iv-step-connector" />
                    <div className="iv-step">
                        <div className="iv-step-number">2</div>
                        <h4>Answer Questions</h4>
                        <p>Speak your answers naturally. The AI evaluates in real-time.</p>
                    </div>
                    <div className="iv-step-connector" />
                    <div className="iv-step">
                        <div className="iv-step-number">3</div>
                        <h4>Get Your Report</h4>
                        <p>Receive detailed scores, strengths, and areas to improve.</p>
                    </div>
                </div>
            </div>

            {/* Interview History */}
            <div className="iv-history">
                <h3 className="iv-section-title">My Interview History</h3>
                {loadingHistory ? (
                    <p className="iv-history-empty">Loading...</p>
                ) : history.length === 0 ? (
                    <p className="iv-history-empty">No interviews yet. Start your first one above!</p>
                ) : (
                    <div className="iv-history-list">
                        {history.map((session) => {
                            let statusKey = session.status?.toLowerCase() || 'active';
                            if (session.ended_reason === 'early_exit') statusKey = 'early_exit';
                            if (session.ended_reason === 'TAB_SWITCH') statusKey = 'tab_switch';

                            const statusCfg = STATUS_CONFIG[statusKey] || STATUS_CONFIG.active;
                            const StatusIcon = statusCfg.icon;
                            return (
                                <div key={session.session_id} className="iv-history-card">
                                    <div className="iv-history-card-header">
                                        <div className="iv-history-role">{session.job_role}</div>
                                        <div className="iv-history-actions">
                                            <div className="iv-history-status" style={{ color: statusCfg.color }}>
                                                <StatusIcon size={14} />
                                                <span>{statusCfg.label}</span>
                                            </div>
                                            <button
                                                className="iv-history-delete-btn"
                                                onClick={(e) => handleDelete(session.session_id, e)}
                                                title="Delete interview record"
                                            >
                                                <FiXCircle size={15} />
                                            </button>
                                        </div>
                                    </div>
                                    <div className="iv-history-card-body">
                                        <div className="iv-history-meta">
                                            <span>{formatDate(session.started_at)}</span>
                                            <span>{session.total_questions} questions</span>
                                            {session.overall_score != null && (
                                                <span>Score: {session.overall_score.toFixed(1)}</span>
                                            )}
                                        </div>
                                        {session.recommendation && (
                                            <div className="iv-history-rec">{session.recommendation}</div>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
}
