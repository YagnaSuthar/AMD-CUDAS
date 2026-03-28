import { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';

export default function Interviews() {
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
                                    <th>Student Name</th>
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
                                                    {p.student_name?.charAt(0)?.toUpperCase() || '?'}
                                                </div>
                                                <div>
                                                    <div>{p.student_name || 'Student'}</div>
                                                    <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                                                        {p.student_email || ''}
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
        </div>
    );
}
