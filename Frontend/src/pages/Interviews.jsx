import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiShield } from 'react-icons/fi';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';

export default function Interviews() {
    const navigate = useNavigate();
    const { user } = useAuth();
    const isRecruiter = user?.role === 'RECRUITER';
    const isStudent = user?.role === 'STUDENT';

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const [pipelines, setPipelines] = useState([]);
    const [jobs, setJobs] = useState([]);

    const [jobId, setJobId] = useState('');
    const [studentId, setStudentId] = useState('');

    const [round2PipelineId, setRound2PipelineId] = useState('');
    const [round2Link, setRound2Link] = useState('');

    const [feedbackModal, setFeedbackModal] = useState(false);
    const [selectedPipeline, setSelectedPipeline] = useState(null);
    const [feedbackText, setFeedbackText] = useState('');
    const [profile, setProfile] = useState(null);
    const [profileLoading, setProfileLoading] = useState(false);
    const [showProfile, setShowProfile] = useState(false);

    // Report modal state
    const [reportModal, setReportModal] = useState(false);
    const [reportData, setReportData] = useState(null);
    const [reportLoading, setReportLoading] = useState(false);

    const [showRulesModal, setShowRulesModal] = useState({ show: false, jobId: null });
    const [rulesAccepted, setRulesAccepted] = useState(false);

    const fetchData = async () => {
        try {
            setError('');
            setLoading(true);

            if (isRecruiter) {
                const [pipeRes, jobsRes] = await Promise.all([
                    api.get('/pipeline/my'),
                    api.get('/jobs/my'),
                ]);
                setPipelines(pipeRes.data || []);
                setJobs(jobsRes.data || []);
            } else if (isStudent) {
                const pipeRes = await api.get('/pipeline/student');
                setPipelines(pipeRes.data || []);
            } else {
                setPipelines([]);
            }
        } catch (err) {
            setError(err?.response?.data?.detail || 'Failed to load interviews');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [user?.role]);

    const onAssignAi = async (e) => {
        e.preventDefault();
        try {
            setError('');
            await api.post('/pipeline/assign-ai', {
                job_id: jobId,
                student_id: studentId,
            });
            setStudentId('');
            await fetchData();
        } catch (err) {
            setError(err?.response?.data?.detail || 'Failed to assign AI interview');
        }
    };

    const onInviteRound2 = async (e) => {
        e.preventDefault();
        try {
            setError('');
            await api.put('/pipeline/invite-round2', {
                pipeline_id: round2PipelineId,
                round2_link: round2Link,
            });
            setRound2PipelineId('');
            setRound2Link('');
            await fetchData();
        } catch (err) {
            setError(err?.response?.data?.detail || 'Failed to invite round 2');
        }
    };

    const onHireReject = async (pipelineId, action, feedback = '') => {
        try {
            setError('');
            if (action === 'hire') {
                await api.put('/pipeline/mark-hired', {
                    pipeline_id: pipelineId,
                    hired_company_name: user.company_name || 'Company',
                });
            } else {
                await api.put('/pipeline/reject', {
                    pipeline_id: pipelineId,
                    feedback: feedback,
                });
            }
            setFeedbackModal(false);
            setSelectedPipeline(null);
            setFeedbackText('');
            await fetchData();
        } catch (err) {
            setError(err?.response?.data?.detail || `Failed to ${action} candidate`);
        }
    };

    const openProfile = async (studentId) => {
        setProfileLoading(true);
        setShowProfile(true);
        try {
            const res = await api.get(`/recruiter/student/${studentId}`);
            setProfile(res.data);
        } catch (err) {
            setError(err?.response?.data?.detail || 'Failed to load profile');
        } finally {
            setProfileLoading(false);
        }
    };

    const openReport = async (sessionId) => {
        setReportLoading(true);
        setReportModal(true);
        setReportData(null);
        try {
            const res = await api.get(`/ai/interview/report/${sessionId}/recruiter`);
            setReportData(res.data);
        } catch (err) {
            setError(err?.response?.data?.detail || 'Failed to load report');
            setReportModal(false);
        } finally {
            setReportLoading(false);
        }
    };

    const rows = useMemo(() => {
        const arr = Array.isArray(pipelines) ? [...pipelines] : [];
        arr.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
        return arr;
    }, [pipelines]);

    if (loading) return <div className="spinner" style={{ margin: '40px auto' }}></div>;

    return (
        <div className="dashboard-content">
            <div className="page-header slide-in-left">
                <h1 className="gradient-text">Interviews</h1>
                <p style={{ color: 'var(--color-text-secondary)' }}>
                    {isRecruiter
                        ? 'Assign AI interviews to students and track their status.'
                        : isStudent
                            ? 'See your assigned interviews and their current status.'
                            : 'Interviews'}
                </p>
            </div>

            {error && (
                <div className="alert alert-error" style={{ marginBottom: '16px' }}>
                    {error}
                </div>
            )}

            {isRecruiter && (
                <div style={{ display: 'grid', gap: '16px', marginBottom: '20px' }}>
                    {/* Pipeline management moved to CLGs and Applications pages */}
                </div>
            )}

            <div className="data-table-container fade-in-up">
                <div className="data-table-header">
                    <h3>
                        Pipeline <span className="table-count">({rows.length})</span>
                    </h3>
                </div>

                {rows.length === 0 ? (
                    <div className="empty-state">
                        <h3>No Interview Pipeline</h3>
                        <p style={{ color: 'var(--color-text-muted)' }}>
                            {isRecruiter ? 'Assign an AI interview to start tracking.' : 'No interviews have been assigned yet.'}
                        </p>
                    </div>
                ) : (
                    <div className="table-scroll-wrapper">
                        <table className="data-table enhanced-table">
                            <thead>
                                <tr>
                                    <th>{isRecruiter ? 'Student Name' : 'Job / Role'}</th>
                                    <th>Status</th>
                                    <th>Report</th>
                                    <th>Profile</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {rows.map((p, idx) => (
                                    <tr key={p.id} className={idx % 2 === 0 ? 'row-even' : 'row-odd'}>
                                        <td style={{ fontWeight: 600 }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                <div
                                                    style={{
                                                        width: '32px',
                                                        height: '32px',
                                                        borderRadius: '50%',
                                                        background: 'var(--gradient-primary)',
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        justifyContent: 'center',
                                                        color: '#fff',
                                                        fontWeight: '700',
                                                        fontSize: '0.8rem',
                                                    }}
                                                >
                                                    {(isRecruiter ? p.student_name : (p.job_title || 'M'))?.charAt(0)?.toUpperCase() || '?'}
                                                </div>
                                                <div>
                                                    <div>{isRecruiter ? (p.student_name || 'Student') : (p.job_title || 'MNC Role')}</div>
                                                    <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                                                        {isRecruiter ? (p.student_email || '') : (p.company_name || '')}
                                                    </div>
                                                </div>
                                            </div>
                                        </td>
                                        <td>
                                            <span style={{
                                                padding: '4px 8px',
                                                borderRadius: '12px',
                                                fontSize: '0.8rem',
                                                fontWeight: '600',
                                                backgroundColor: p.status === 'AI_COMPLETED' ? 'var(--color-success)' : 
                                                                 p.status === 'ROUND2_INVITED' ? 'var(--color-warning)' : 
                                                                 p.status === 'HIRED' ? 'var(--color-success)' : 'var(--color-secondary)',
                                                color: '#fff'
                                            }}>
                                                {p.status.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, l => l.toUpperCase())}
                                            </span>
                                        </td>
                                        <td>
                                            {p.status === 'AI_COMPLETED' && p.ai_session_id ? (
                                                <button 
                                                    className="btn btn-sm btn-secondary" 
                                                    onClick={() => openReport(p.ai_session_id)}
                                                >
                                                    View Report
                                                </button>
                                            ) : (
                                                <span style={{ color: 'var(--color-text-muted)' }}>-</span>
                                            )}
                                        </td>
                                        <td>
                                            <button 
                                                className="btn btn-sm btn-primary"
                                                onClick={() => openProfile(p.student_id)}
                                            >
                                                Profile
                                            </button>
                                        </td>
                                        <td>
                                            {isRecruiter ? (
                                                <div style={{ display: 'flex', gap: '8px' }}>
                                                    <button 
                                                        className="btn btn-sm btn-success"
                                                        onClick={() => onHireReject(p.id, 'hire')}
                                                        title="Hire Candidate"
                                                    >
                                                        ✓
                                                    </button>
                                                    <button 
                                                        className="btn btn-sm btn-error"
                                                        onClick={() => {
                                                            setSelectedPipeline(p);
                                                            setFeedbackModal(true);
                                                        }}
                                                        title="Reject Candidate"
                                                    >
                                                        ✗
                                                    </button>
                                                </div>
                                            ) : (
                                                (p.status === 'AI_ASSIGNED') ? (
                                                    <button 
                                                        className="btn btn-sm btn-primary"
                                                        onClick={() => setShowRulesModal({ show: true, jobId: p.job_id })}
                                                    >
                                                        Start AI Interview
                                                    </button>
                                                ) : <span style={{ color: 'var(--color-text-muted)' }}>-</span>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Feedback Modal */}
            {feedbackModal && (
                <div className="modal-overlay" onClick={() => setFeedbackModal(false)}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h4>Rejection Feedback</h4>
                            <button className="modal-close" onClick={() => setFeedbackModal(false)}>
                                ×
                            </button>
                        </div>
                        <div className="modal-body">
                            <div className="form-group">
                                <label className="form-label">Why is this candidate not selected?</label>
                                <textarea
                                    className="form-input"
                                    rows={5}
                                    value={feedbackText}
                                    onChange={(e) => setFeedbackText(e.target.value)}
                                    placeholder="Please provide feedback for the student..."
                                    required
                                />
                            </div>
                        </div>
                        <div className="modal-footer">
                            <button className="btn btn-secondary" onClick={() => setFeedbackModal(false)}>Cancel</button>
                            <button 
                                className="btn btn-primary" 
                                onClick={() => onHireReject(selectedPipeline.id, 'reject', feedbackText)}
                                disabled={!feedbackText.trim()}
                            >
                                Send Feedback & Reject
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Profile Modal */}
            {showProfile && profile && (
                <div className="modal-overlay" onClick={() => setShowProfile(false)}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '600px' }}>
                        <div className="modal-header">
                            <h4>Student Profile</h4>
                            <button className="modal-close" onClick={() => setShowProfile(false)}>
                                ×
                            </button>
                        </div>
                        <div className="modal-body">
                            {profileLoading ? (
                                <div>Loading profile...</div>
                            ) : (
                                <div style={{ display: 'grid', gap: '1rem' }}>
                                    <div>
                                        <div style={{ fontWeight: 700, marginBottom: '4px' }}>Name</div>
                                        <div style={{ color: 'var(--color-text-muted)' }}>{profile.name}</div>
                                    </div>
                                    <div>
                                        <div style={{ fontWeight: 700, marginBottom: '4px' }}>Email</div>
                                        <div style={{ color: 'var(--color-text-muted)' }}>{profile.email}</div>
                                    </div>
                                    <div>
                                        <div style={{ fontWeight: 700, marginBottom: '4px' }}>Skills</div>
                                        <div style={{ color: 'var(--color-text-muted)' }}>
                                            {Array.isArray(profile.skills) && profile.skills.length ? profile.skills.join(', ') : '-'}
                                        </div>
                                    </div>
                                    <div>
                                        <div style={{ fontWeight: 700, marginBottom: '4px' }}>Resume</div>
                                        <div>
                                            {profile.resume_url ? (
                                                <a href={profile.resume_url} target="_blank" rel="noreferrer" className="btn btn-sm btn-secondary">
                                                    View Resume
                                                </a>
                                            ) : (
                                                <span style={{ color: 'var(--color-text-muted)' }}>-</span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                        <div className="modal-footer">
                            <button className="btn btn-secondary" onClick={() => setShowProfile(false)}>Close</button>
                        </div>
                    </div>
                </div>
            )}

            {/* Recruiter Report Modal */}
            {reportModal && (
                <div className="job-modal-overlay" onClick={() => setReportModal(false)}>
                    <div className="job-modal-content slide-in-up" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '680px', maxHeight: '90vh' }}>
                        <button className="job-modal-close" onClick={() => setReportModal(false)}>×</button>

                        {reportLoading ? (
                            <div style={{ padding: '60px', textAlign: 'center' }}>
                                <div className="spinner" style={{ margin: '0 auto 16px' }}></div>
                                <p style={{ color: 'var(--color-text-muted)' }}>Loading report...</p>
                            </div>
                        ) : reportData ? (
                            <>
                                <div className="job-modal-header">
                                    <h2 style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--color-text-primary)', margin: 0 }}>AI Interview Report</h2>
                                    <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem', marginTop: '4px' }}>Recruiter Assessment Summary</p>
                                </div>

                                <div className="job-modal-body" style={{ padding: '24px 32px' }}>
                                    {/* Score Cards */}
                                    <div className="report-scores-grid">
                                        <div className="report-score-card">
                                            <div className="report-score-value">{((reportData.technical_score || 0) * 100).toFixed(0)}%</div>
                                            <div className="report-score-label">Technical</div>
                                        </div>
                                        <div className="report-score-card">
                                            <div className="report-score-value">{((reportData.communication_score || 0) * 100).toFixed(0)}%</div>
                                            <div className="report-score-label">Communication</div>
                                        </div>
                                        <div className="report-score-card">
                                            <div className="report-score-value">{((reportData.behavior_score || 0) * 100).toFixed(0)}%</div>
                                            <div className="report-score-label">Behavior</div>
                                        </div>
                                        <div className="report-score-card report-score-final">
                                            <div className="report-score-value">{((reportData.final_score || 0) * 100).toFixed(0)}%</div>
                                            <div className="report-score-label">Final Score</div>
                                        </div>
                                    </div>

                                    {/* Recommendation Badge */}
                                    <div style={{ textAlign: 'center', margin: '20px 0' }}>
                                        <span className={`report-recommendation-badge report-rec-${(reportData.recommendation || '').toLowerCase().replace(/ /g, '_')}`}>
                                            {reportData.recommendation || 'N/A'}
                                        </span>
                                    </div>

                                    {/* Justification */}
                                    {reportData.justification && (
                                        <div className="report-section">
                                            <h4 className="report-section-title">Justification</h4>
                                            <p style={{ color: 'var(--color-text-secondary)', lineHeight: '1.6', fontSize: '0.9rem' }}>{reportData.justification}</p>
                                        </div>
                                    )}

                                    {/* Strengths & Weaknesses */}
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '16px' }}>
                                        <div className="report-section">
                                            <h4 className="report-section-title" style={{ color: 'var(--color-success)' }}>✓ Strengths</h4>
                                            <ul className="report-list">
                                                {(reportData.strengths || []).map((s, i) => <li key={i}>{s}</li>)}
                                                {(!reportData.strengths || !reportData.strengths.length) && <li style={{ color: 'var(--color-text-muted)' }}>None identified</li>}
                                            </ul>
                                        </div>
                                        <div className="report-section">
                                            <h4 className="report-section-title" style={{ color: 'var(--color-error)' }}>✗ Weaknesses</h4>
                                            <ul className="report-list">
                                                {(reportData.weaknesses || []).map((w, i) => <li key={i}>{w}</li>)}
                                                {(!reportData.weaknesses || !reportData.weaknesses.length) && <li style={{ color: 'var(--color-text-muted)' }}>None identified</li>}
                                            </ul>
                                        </div>
                                    </div>

                                    {/* Assessments */}
                                    {reportData.technical_assessment && (
                                        <div className="report-section">
                                            <h4 className="report-section-title">Technical Assessment</h4>
                                            <p style={{ color: 'var(--color-text-secondary)', lineHeight: '1.6', fontSize: '0.9rem' }}>{reportData.technical_assessment}</p>
                                        </div>
                                    )}
                                    {reportData.communication_assessment && (
                                        <div className="report-section">
                                            <h4 className="report-section-title">Communication Assessment</h4>
                                            <p style={{ color: 'var(--color-text-secondary)', lineHeight: '1.6', fontSize: '0.9rem' }}>{reportData.communication_assessment}</p>
                                        </div>
                                    )}
                                    {reportData.behavior_analysis && (
                                        <div className="report-section">
                                            <h4 className="report-section-title">Behavior Analysis</h4>
                                            <p style={{ color: 'var(--color-text-secondary)', lineHeight: '1.6', fontSize: '0.9rem' }}>{reportData.behavior_analysis}</p>
                                        </div>
                                    )}
                                </div>
                            </>
                        ) : null}
                    </div>
                </div>
            )}

            {/* Rules Modal */}
            {showRulesModal.show && (
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
                                <span style={{ fontSize: '1.2rem' }}>📹</span>
                                <div><strong style={{ display: 'block' }}>Camera Required</strong><span style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>You must keep your webcam enabled. If your face is out of view, the interview will terminate instantly.</span></div>
                            </li>
                            <li style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                                <span style={{ fontSize: '1.2rem' }}>📱</span>
                                <div><strong style={{ display: 'block', color: 'var(--color-error)' }}>No Mobile Phones or Tablets</strong><span style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>If a phone, tablet, or external remote is detected in your frame, the session will be immediately flagged and terminated.</span></div>
                            </li>
                            <li style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                                <span style={{ fontSize: '1.2rem' }}>🖥️</span>
                                <div><strong style={{ display: 'block', color: 'var(--color-error)' }}>No Tab Switching</strong><span style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>Any attempt to switch tabs, copy-paste, or minimize the browser window will terminate the test instantly.</span></div>
                            </li>
                            <li style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                                <span style={{ fontSize: '1.2rem' }}>👥</span>
                                <div><strong style={{ display: 'block' }}>Solo Interview</strong><span style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>Only ONE person must be in the frame. The presence of multiple faces will trigger termination.</span></div>
                            </li>
                        </ul>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer', marginBottom: '24px', padding: '12px', backgroundColor: 'var(--color-bg-alt)', borderRadius: '8px' }}>
                            <input type="checkbox" checked={rulesAccepted} onChange={e => setRulesAccepted(e.target.checked)} style={{ transform: 'scale(1.2)' }} />
                            <span style={{ fontSize: '0.9rem', color: 'var(--color-text-primary)', fontWeight: 600 }}>I understand and agree to follow all proctoring rules.</span>
                        </label>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                            <button className="btn btn-secondary" onClick={() => { setShowRulesModal({ show: false, jobId: null }); setRulesAccepted(false); }}>Cancel</button>
                            <button 
                                className="btn btn-primary" 
                                disabled={!rulesAccepted}
                                onClick={() => {
                                    const path = showRulesModal.jobId 
                                        ? `/dashboard/interview/live?mode=recruiter&job_id=${showRulesModal.jobId}` 
                                        : '/dashboard/interview/live?mode=practice';
                                    setShowRulesModal({ show: false, jobId: null });
                                    navigate(path);
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
