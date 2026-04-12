import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../../context/AuthContext';
import { FiMic, FiCpu, FiActivity, FiZap, FiShield, FiMessageCircle, FiClock, FiCheckCircle, FiXCircle, FiTrash2 } from 'react-icons/fi';
import api from '../../../../utils/api';
import '../../../../style/interview.css';

const FEATURES = [
    { icon: FiMic, title: 'Voice-Enabled', desc: 'Speak naturally â€” our AI listens and responds in real-time.' },
    { icon: FiCpu, title: 'AI-Powered', desc: 'Powered by advanced LLMs tuned for technical interviews.' },
    { icon: FiActivity, title: 'Adaptive', desc: 'Difficulty adjusts based on your performance dynamically.' },
    { icon: FiZap, title: 'Instant Feedback', desc: 'Get scored on clarity, depth, confidence & technical accuracy.' },
    { icon: FiShield, title: 'Behavior-Aware', desc: 'Detects communication style & provides soft-skill feedback.' },
    { icon: FiMessageCircle, title: 'Conversational', desc: 'Feels like a real interview â€” not a quiz.' },
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
    const [showRulesModal, setShowRulesModal] = useState(false);
    const [rulesAccepted, setRulesAccepted] = useState(false);

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
        if (!dateStr) return 'â€”';
        return new Date(dateStr).toLocaleDateString('en-IN', {
            day: 'numeric', month: 'short', year: 'numeric',
            hour: '2-digit', minute: '2-digit',
        });
    };

    const handleDelete = async (sessionId, e) => {
        e.stopPropagation();
        if (!window.confirm("Are you sure you want to delete this interview record? This action cannot be undone.")) return;

        try {
            await api.delete(`/ai/interview/session/${sessionId}`);
            setHistory(prev => prev.filter(s => s.session_id !== sessionId));
        } catch (err) {
            console.error('Failed to delete session:', err);
            alert(err.response?.data?.detail || "Failed to delete from history.");
        }
    };

    const handleDeleteAll = async () => {
        if (!window.confirm("Delete ALL interview history? This cannot be undone.")) return;
        try {
            await api.delete('/ai/interview/history/all');
            setHistory([]);
        } catch (err) {
            console.error('Failed to delete all:', err);
            alert(err.response?.data?.detail || "Failed to delete history.");
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
                        Practice with our AI interviewer â€” voice-enabled, behavior-reactive, fully dynamic.
                        Tailored to your skills profile and designed to simulate real-world technical interviews.
                    </p>
                    <button
                        className="iv-hero-btn"
                        onClick={() => setShowRulesModal(true)}
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
                <div className="iv-history-header">
                    <h3 className="iv-section-title">My Interview History</h3>
                    {history.length > 0 && (
                        <button className="iv-delete-all-btn" onClick={handleDeleteAll}>
                            <FiTrash2 size={13} /> Delete All
                        </button>
                    )}
                </div>
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
            {/* Rules Modal */}
            {showRulesModal && (
                <div style={{
                    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999,
                    backdropFilter: 'blur(4px)'
                }}>
                    <div style={{
                        backgroundColor: 'var(--color-bg-card)', borderRadius: '12px', padding: '32px', maxWidth: '600px', width: '90%',
                        boxShadow: '0 8px 32px rgba(0,0,0,0.2), inset 0 1px 1px rgba(255,255,255,0.05)',
                        border: '1px solid var(--color-border)', animation: 'slideUp 0.3s ease-out', maxHeight: '90vh', overflowY: 'auto'
                    }}>
                        <h2 style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: 0, color: 'var(--color-text-primary)' }}>
                            <FiShield style={{ color: 'var(--color-primary)' }} /> Interview Rules & Regulations
                        </h2>
                        <p style={{ color: 'var(--color-text-secondary)', marginBottom: '24px' }}>
                            Please review the strict AI proctoring policies before starting your session.
                        </p>
                        <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 24px 0', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                            <li style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                                <span style={{ fontSize: '1.2rem' }}>ðŸ“¹</span>
                                <div><strong style={{ display: 'block' }}>Camera Required</strong><span style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>You must keep your webcam enabled. If your face is out of view, the interview will terminate instantly.</span></div>
                            </li>
                            <li style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                                <span style={{ fontSize: '1.2rem' }}>ðŸ“±</span>
                                <div><strong style={{ display: 'block', color: 'var(--color-error)' }}>No Mobile Phones or Tablets</strong><span style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>If a phone, tablet, or external remote is detected in your frame, the session will be immediately flagged and terminated.</span></div>
                            </li>
                            <li style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                                <span style={{ fontSize: '1.2rem' }}>ðŸ–¥ï¸</span>
                                <div><strong style={{ display: 'block', color: 'var(--color-error)' }}>No Tab Switching</strong><span style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>Any attempt to switch tabs, copy-paste, or minimize the browser window will terminate the test instantly.</span></div>
                            </li>
                            <li style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                                <span style={{ fontSize: '1.2rem' }}>ðŸ‘¥</span>
                                <div><strong style={{ display: 'block' }}>Solo Interview</strong><span style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>Only ONE person must be in the frame. The presence of multiple faces will trigger termination.</span></div>
                            </li>
                        </ul>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer', marginBottom: '24px', padding: '12px', backgroundColor: 'var(--color-bg-alt)', borderRadius: '8px' }}>
                            <input type="checkbox" checked={rulesAccepted} onChange={e => setRulesAccepted(e.target.checked)} style={{ transform: 'scale(1.2)' }} />
                            <span style={{ fontSize: '0.9rem', color: 'var(--color-text-primary)', fontWeight: 600 }}>I understand and agree to follow all proctoring rules.</span>
                        </label>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                            <button className="btn btn-secondary" onClick={() => { setShowRulesModal(false); setRulesAccepted(false); }}>Cancel</button>
                            <button 
                                className="btn btn-primary" 
                                disabled={!rulesAccepted}
                                onClick={() => {
                                    setShowRulesModal(false);
                                    navigate('/dashboard/interview/live?mode=practice');
                                }}
                            >
                                Start Interview
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
