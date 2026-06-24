import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../../../context/AuthContext';
import { FiMic, FiCpu, FiActivity, FiZap, FiShield, FiMessageCircle, FiClock, FiCheckCircle, FiXCircle, FiTrash2, FiEye, FiDownload, FiCamera, FiSmartphone, FiMonitor, FiUsers } from 'react-icons/fi';
import api from '../../../../utils/api';
import '../../../../style/interview.css';

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
    const location = useLocation();
    const [history, setHistory] = useState([]);
    const [loadingHistory, setLoadingHistory] = useState(true);
    const [showRulesModal, setShowRulesModal] = useState(false);
    const [rulesAccepted, setRulesAccepted] = useState(false);
    const [showReportModal, setShowReportModal] = useState(false);
    const [reportData, setReportData] = useState(null);
    const [reportLoading, setReportLoading] = useState(false);
    const [historyExpanded, setHistoryExpanded] = useState(false);
    const [selectedMode, setSelectedMode] = useState('basic');

    const interviewCategories = [
        {
            title: 'Software Development',
            options: [
                { label: 'Frontend Developer', value: 'frontend' },
                { label: 'Backend Developer', value: 'backend' },
                { label: 'MERN Stack Developer', value: 'mern' },
                { label: 'Java Developer', value: 'java' },
                { label: 'Python Developer', value: 'python' },
            ],
        },
        {
            title: 'Data & AI',
            options: [
                { label: 'Data Analyst', value: 'data_analyst' },
                { label: 'Data Science', value: 'data_science' },
                { label: 'ML / AI Engineer', value: 'ml_ai' },
            ],
        },
        {
            title: 'Systems & Infrastructure',
            options: [
                { label: 'DevOps Engineer', value: 'devops' },
                { label: 'Cloud Engineer', value: 'cloud' },
            ],
        },
        {
            title: 'Security',
            options: [{ label: 'Cybersecurity', value: 'cybersecurity' }],
        },
        {
            title: 'Practice',
            options: [{ label: 'Basic Practice', value: 'basic' }],
        },
    ];

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

    useEffect(() => {
        if (location?.state?.openRules) {
            setShowRulesModal(true);
        }
    }, [location?.state?.openRules]);

    const formatDate = (dateStr) => {
        if (!dateStr) return '—';
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

    const handleViewReport = async (sessionId, e) => {
        e.stopPropagation();
        setReportLoading(true);
        setShowReportModal(true);
        try {
            const res = await api.get(`/ai/interview/${sessionId}/report`);
            setReportData(res.data);
        } catch (err) {
            console.error('Failed to load report:', err);
            setReportData({ error: err.response?.data?.detail || 'Failed to load report.' });
        } finally {
            setReportLoading(false);
        }
    };

    const handleDownloadPDF = async (sessionId, e) => {
        e.stopPropagation();
        try {
            const response = await api.get(`/ai/interview/${sessionId}/download`, {
                responseType: 'blob',
            });
            const blob = new Blob([response.data], { type: 'application/pdf' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Interview_Report_${sessionId.slice(0,8)}.pdf`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
        } catch (err) {
            console.error('Failed to download PDF:', err);
            alert(err.response?.data?.detail || 'Failed to download PDF.');
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

            {/* Compact Features & Steps */}
            <div className="iv-compact-sections">
                {/* Features Grid */}
                <div className="iv-features-compact">
                    {FEATURES.slice(0, 3).map((feat, i) => (
                        <div key={i} className="iv-feature-card-compact" style={{ animationDelay: `${i * 0.08}s` }}>
                            <div className="iv-feature-icon-compact">
                                <feat.icon />
                            </div>
                            <div>
                                <h4>{feat.title}</h4>
                                <p>{feat.desc}</p>
                            </div>
                        </div>
                    ))}
                </div>

                {/* How It Works (compact) */}
                <div className="iv-steps-compact">
                    <h4 className="iv-section-title-compact">How It Works</h4>
                    <div className="iv-steps-track-compact">
                        <div className="iv-step-compact">
                            <div className="iv-step-number-compact">1</div>
                            <div>
                                <h5>Start Session</h5>
                                <p>Click to begin your AI interview</p>
                            </div>
                        </div>
                        <div className="iv-step-compact">
                            <div className="iv-step-number-compact">2</div>
                            <div>
                                <h5>Answer Questions</h5>
                                <p>Speak naturally; AI evaluates</p>
                            </div>
                        </div>
                        <div className="iv-step-compact">
                            <div className="iv-step-number-compact">3</div>
                            <div>
                                <h5>Get Report</h5>
                                <p>Detailed scores & insights</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Interview History (collapsible, scrollable) */}
            <div className={`iv-history-wrapper ${historyExpanded ? 'expanded' : ''}`}>
                <div className="iv-history-toggle">
                    <h3 className="iv-section-title">My Interview History</h3>
                    <div className="iv-history-toggle-actions">
                        {history.length > 0 && (
                            <button
                                className="iv-history-expand-btn"
                                onClick={() => setHistoryExpanded(!historyExpanded)}
                                title={historyExpanded ? 'Collapse history' : 'Expand history'}
                            >
                                {historyExpanded ? <FiXCircle size={15} /> : <FiActivity size={15} />}
                                <span>{historyExpanded ? 'Collapse' : 'Expand'}</span>
                            </button>
                        )}
                        {history.length > 0 && (
                            <button className="iv-delete-all-btn" onClick={handleDeleteAll}>
                                <FiTrash2 size={13} /> Delete All
                            </button>
                        )}
                    </div>
                </div>
                <div className="iv-history-scroll">
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
                                                    className="iv-history-action-btn"
                                                    onClick={(e) => handleViewReport(session.session_id, e)}
                                                    title="View detailed report"
                                                >
                                                    <FiEye size={15} />
                                                </button>
                                                <button
                                                    className="iv-history-action-btn"
                                                    onClick={(e) => handleDownloadPDF(session.session_id, e)}
                                                    title="Download PDF"
                                                >
                                                    <FiDownload size={15} />
                                                </button>
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
            {/* Report Modal */}
            {showReportModal && (
                <div style={{
                    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999,
                    backdropFilter: 'blur(4px)'
                }}>
                    <div style={{
                        backgroundColor: 'var(--color-bg-card)', borderRadius: '12px', padding: '32px', maxWidth: '700px', width: '90%',
                        boxShadow: '0 8px 32px rgba(0,0,0,0.2), inset 0 1px 1px rgba(255,255,255,0.05)',
                        border: '1px solid var(--color-border)', animation: 'slideUp 0.3s ease-out', maxHeight: '90vh', overflowY: 'auto'
                    }}>
                        <h2 style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: 0, color: 'var(--color-text-primary)' }}>
                            <FiEye style={{ color: 'var(--color-primary)' }} /> Interview Report
                        </h2>
                        {reportLoading ? (
                            <p style={{ color: 'var(--color-text-secondary)' }}>Loading report...</p>
                        ) : reportData?.error ? (
                            <div style={{ color: 'var(--color-error)', marginBottom: '20px' }}>{reportData.error}</div>
                        ) : reportData ? (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--color-border)', paddingBottom: '12px' }}>
                                    <div>
                                        <div style={{ fontSize: '0.9rem', color: 'var(--color-text-muted)' }}>Status</div>
                                        <div style={{ fontWeight: 600, color: 'var(--color-text-primary)', textTransform: 'capitalize' }}>{reportData.status}</div>
                                    </div>
                                    <div style={{ textAlign: 'center' }}>
                                        <div style={{ fontSize: '0.9rem', color: 'var(--color-text-muted)' }}>Overall Score</div>
                                        <div style={{ fontSize: '1.8rem', fontWeight: 700, color: reportData.final_score >= 70 ? 'var(--color-success)' : reportData.final_score >= 40 ? 'var(--color-warning)' : 'var(--color-error)' }}>
                                            {reportData.final_score.toFixed(1)}%
                                        </div>
                                    </div>
                                </div>
                                <div>
                                    <div style={{ fontWeight: 600, marginBottom: '8px', color: 'var(--color-text-primary)' }}>Score Breakdown</div>
                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: '12px' }}>
                                        <div style={{ textAlign: 'center', padding: '12px', backgroundColor: 'var(--color-bg-alt)', borderRadius: '8px' }}>
                                            <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>Technical</div>
                                            <div style={{ fontSize: '1.2rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>{reportData.scores.technical.toFixed(1)}</div>
                                        </div>
                                        <div style={{ textAlign: 'center', padding: '12px', backgroundColor: 'var(--color-bg-alt)', borderRadius: '8px' }}>
                                            <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>Communication</div>
                                            <div style={{ fontSize: '1.2rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>{reportData.scores.communication.toFixed(1)}</div>
                                        </div>
                                        <div style={{ textAlign: 'center', padding: '12px', backgroundColor: 'var(--color-bg-alt)', borderRadius: '8px' }}>
                                            <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>Behavior</div>
                                            <div style={{ fontSize: '1.2rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>{reportData.scores.behavior.toFixed(1)}</div>
                                        </div>
                                    </div>
                                </div>
                                {reportData.summary && (
                                    <div>
                                        <div style={{ fontWeight: 600, marginBottom: '8px', color: 'var(--color-text-primary)' }}>Summary</div>
                                        <div style={{ color: 'var(--color-text-secondary)', whiteSpace: 'pre-wrap' }}>{reportData.summary}</div>
                                    </div>
                                )}
                                {reportData.strengths && reportData.strengths.length > 0 && (
                                    <div>
                                        <div style={{ fontWeight: 600, marginBottom: '8px', color: 'var(--color-text-primary)' }}>Strengths</div>
                                        <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                            {reportData.strengths.map((s, i) => (
                                                <li key={i} style={{ color: 'var(--color-success)', display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
                                                    <span style={{ marginTop: '4px' }}>•</span>
                                                    <span>{s}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                                {reportData.weaknesses && reportData.weaknesses.length > 0 && (
                                    <div>
                                        <div style={{ fontWeight: 600, marginBottom: '8px', color: 'var(--color-text-primary)' }}>Areas to Improve</div>
                                        <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                            {reportData.weaknesses.map((w, i) => (
                                                <li key={i} style={{ color: 'var(--color-warning)', display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
                                                    <span style={{ marginTop: '4px' }}>•</span>
                                                    <span>{w}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                                {reportData.questions && reportData.questions.length > 0 && (
                                    <div>
                                        <div style={{ fontWeight: 600, marginBottom: '12px', color: 'var(--color-text-primary)' }}>Question-by-Question</div>
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                                            {reportData.questions.map((q, idx) => (
                                                <div key={idx} style={{ border: '1px solid var(--color-border)', borderRadius: '8px', padding: '12px', backgroundColor: 'var(--color-bg-alt)' }}>
                                                    <div style={{ fontWeight: 600, marginBottom: '8px', color: 'var(--color-text-primary)' }}>Q{idx + 1}. {q.question}</div>
                                                    {q.answer && (
                                                        <div style={{ marginBottom: '8px', color: 'var(--color-text-secondary)' }}>
                                                            <strong>Your answer:</strong> {q.answer}
                                                        </div>
                                                    )}
                                                    {q.evaluation && typeof q.evaluation === 'object' && (
                                                        <div style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
                                                            <strong>Feedback:</strong> {q.evaluation.feedback || 'No feedback available.'}
                                                        </div>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        ) : null}
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px' }}>
                            <button className="btn btn-secondary" onClick={() => setShowReportModal(false)}>Close</button>
                        </div>
                    </div>
                </div>
            )}
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
                        <div style={{ marginBottom: '24px' }}>
                            <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', color: 'var(--color-text-primary)', fontWeight: 600 }}>
                                Choose Interview Type
                            </label>
                            <div className="category-container">
                                {interviewCategories.map((category) => (
                                    <div key={category.title} className="category-block">
                                        <h3 style={{ margin: '0 0 10px 0', color: 'var(--color-text-primary)' }}>{category.title}</h3>
                                        <div className="options-grid">
                                            {category.options.map((opt) => (
                                                <button
                                                    type="button"
                                                    key={opt.value}
                                                    className={`option-card ${selectedMode === opt.value ? 'active' : ''}`}
                                                    onClick={() => setSelectedMode(opt.value)}
                                                >
                                                    {opt.label}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                        <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 24px 0', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                            <li style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                                <FiCamera size={20} />
                                <div><strong style={{ display: 'block' }}>Camera Required</strong><span style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>You must keep your webcam enabled. If your face is out of view, the interview will terminate instantly.</span></div>
                            </li>
                            <li style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                                <FiSmartphone size={20} />
                                <div><strong style={{ display: 'block', color: 'var(--color-error)' }}>No Mobile Phones or Tablets</strong><span style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>If a phone, tablet, or external remote is detected in your frame, the session will be immediately flagged and terminated.</span></div>
                            </li>
                            <li style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                                <FiMonitor size={20} />
                                <div><strong style={{ display: 'block', color: 'var(--color-error)' }}>No Tab Switching</strong><span style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>Any attempt to switch tabs, copy-paste, or minimize the browser window will terminate the test instantly.</span></div>
                            </li>
                            <li style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                                <FiUsers size={20} />
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
                                    navigate(`/dashboard/interview/live?mode=practice&role=${selectedMode}`);
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
