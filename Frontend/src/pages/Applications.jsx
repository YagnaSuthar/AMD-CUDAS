import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { FiInbox, FiCheckCircle, FiXCircle, FiClock, FiBriefcase, FiUser, FiMail, FiAward, FiInfo, FiTrash2 } from 'react-icons/fi';

export default function Applications() {
    const { user } = useAuth();
    const [applications, setApplications] = useState([]);
    const [jobs, setJobs] = useState([]);
    const [selectedJobId, setSelectedJobId] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [actionLoading, setActionLoading] = useState({});
    const [round2Schedule, setRound2Schedule] = useState({});
    const [reportModal, setReportModal] = useState({ show: false, report: null });
    const [deleteModal, setDeleteModal] = useState({ show: false, appId: null, studentName: '' });
    const [confirmAiModal, setConfirmAiModal] = useState({ show: false, appId: null, studentId: null, jobId: null });

    const handleDeleteApplication = async () => {
        try {
            setActionLoading({ ...actionLoading, [deleteModal.appId]: 'delete' });
            await api.delete(`/applications/${deleteModal.appId}`);
            setDeleteModal({ show: false, appId: null, studentName: '' });
            await fetchApplications();
        } catch (e) {
            setError(e?.response?.data?.detail || 'Failed to delete application');
            setDeleteModal({ show: false, appId: null, studentName: '' });
        } finally {
            setActionLoading({ ...actionLoading, [deleteModal.appId]: null });
        }
    };

    const fetchReport = async (sessionId) => {
        try {
            const res = await api.get(`/ai/interview/report/${sessionId}`);
            setReportModal({ show: true, report: res.data });
        } catch (e) {
            console.error('Failed to fetch report:', e);
            alert('Failed to load report. The interview may not be completed yet.');
        }
    };

    const fetchJobs = async () => {
        try {
            const res = await api.get('/jobs/my');
            setJobs(res.data || []);
        } catch (e) {
            console.error('Failed to fetch jobs:', e);
        }
    };

    const inviteToRound2 = async (applicationId, pipelineId) => {
        if (!pipelineId) {
            setError('Pipeline not found for this application. Assign AI interview first.');
            return;
        }

        const scheduledLocal = round2Schedule[applicationId];
        if (!scheduledLocal) {
            setError('Please select Round 2 date/time first.');
            return;
        }

        setActionLoading({ ...actionLoading, [applicationId]: 'round2' });
        try {
            const scheduledAtIso = new Date(scheduledLocal).toISOString();
            await api.put('/pipeline/invite-round2', {
                pipeline_id: pipelineId,
                round2_link: `/dashboard/round2/${pipelineId}`,
                scheduled_at: scheduledAtIso,
            });
            await fetchApplications();
        } catch (e) {
            setError(e?.response?.data?.detail || 'Failed to invite to Round 2');
        } finally {
            setActionLoading({ ...actionLoading, [applicationId]: null });
        }
    };

    const fetchApplications = async () => {
        setLoading(true);
        try {
            const params = selectedJobId ? { job_id: selectedJobId } : {};
            const res = await api.get('/applications/recruiter', { params });
            setApplications(res.data || []);
            setError('');
        } catch (e) {
            console.error('Fetch applications error:', e);
            console.error('Error response:', e?.response);
            console.error('Error data:', e?.response?.data);
            setError(e?.response?.data?.detail || e?.message || 'Failed to fetch applications');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchJobs();
        fetchApplications();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    useEffect(() => {
        fetchApplications();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedJobId]);

    const inviteToAiInterview = async (applicationId, studentId, jobId) => {
        setActionLoading({ ...actionLoading, [applicationId]: 'ai' });
        try {
            await api.post('/pipeline/assign-ai', {
                student_id: studentId,
                job_id: jobId,
            });
            setConfirmAiModal({ show: false, appId: null, studentId: null, jobId: null });
            // Refresh applications to show updated status
            await fetchApplications();
        } catch (e) {
            setError(e?.response?.data?.detail || 'Failed to assign AI interview');
        } finally {
            setActionLoading({ ...actionLoading, [applicationId]: null });
        }
    };

    const getStatusBadge = (status) => {
        const statusConfig = {
            PENDING: { icon: FiClock, className: 'status-badge-pending', label: 'Pending' },
            AI_ASSIGNED: { icon: FiCheckCircle, className: 'status-badge-approved', label: 'AI Assigned' },
            AI_COMPLETED: { icon: FiAward, className: 'status-badge-approved', label: 'Completed' },
            ROUND2_INVITED: { icon: FiCheckCircle, className: 'status-badge-approved', label: 'Round 2 Invited' },
            HIRED: { icon: FiCheckCircle, className: 'status-badge-approved', label: 'Hired' },
            REJECTED: { icon: FiXCircle, className: 'status-badge-rejected', label: 'Rejected' },
        };
        const config = statusConfig[status] || statusConfig.PENDING;
        const Icon = config.icon;
        return (
            <span className={`status-badge ${config.className}`}>
                <Icon style={{ marginRight: '4px', verticalAlign: 'middle' }} />
                {config.label}
            </span>
        );
    };

    if (loading && applications.length === 0) {
        return (
            <div className="dashboard-page">
                <div className="page-header">
                    <h2>Applications</h2>
                    <p>Manage student job applications</p>
                </div>
                <div className="card">
                    <div className="card-body" style={{ textAlign: 'center', padding: '3rem' }}>
                        Loading applications...
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="dashboard-page">
            <div className="page-header">
                <h2><FiInbox style={{ marginRight: '8px' }} /> Applications</h2>
                <p>Review and manage student job applications</p>
            </div>

            {error && (
                <div className="card" style={{ marginBottom: '20px', borderLeft: '4px solid var(--color-error)' }}>
                    <div className="card-body" style={{ color: 'var(--color-error)' }}>
                        {error}
                    </div>
                </div>
            )}

            <div className="card" style={{ marginBottom: '24px' }}>
                <div className="card-header">
                    <h4><FiBriefcase style={{ marginRight: '8px' }} /> Filter by Job</h4>
                </div>
                <div className="card-body">
                    <select
                        className="input"
                        value={selectedJobId}
                        onChange={(e) => setSelectedJobId(e.target.value)}
                        style={{ maxWidth: '400px' }}
                    >
                        <option value="">All Jobs</option>
                        {jobs.map((job) => (
                            <option key={job.id} value={job.id}>
                                {job.title} - {job.location}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            <div className="card">
                <div className="card-header">
                    <h4><FiInbox style={{ marginRight: '8px' }} /> Applications ({applications.length})</h4>
                </div>
                <div className="card-body" style={{ padding: 0 }}>
                    {applications.length === 0 ? (
                        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--color-text-muted)' }}>
                            <FiInbox size={48} style={{ marginBottom: '16px', opacity: 0.5 }} />
                            <p>No applications found.</p>
                            <p style={{ fontSize: '0.85rem' }}>
                                {selectedJobId ? 'Try selecting a different job or clear the filter.' : 'Students will appear here when they apply to your jobs.'}
                            </p>
                        </div>
                    ) : (
                        <div className="table-responsive">
                            <table className="table">
                                <thead>
                                    <tr>
                                        <th>Student</th>
                                        <th>Job</th>
                                        <th>Applied Date</th>
                                        <th>Status</th>
                                        <th>AI Score</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {applications.map((app) => (
                                        <tr key={app.id}>
                                            <td>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                                    <div
                                                        style={{
                                                            width: '40px',
                                                            height: '40px',
                                                            borderRadius: '50%',
                                                            background: 'var(--gradient-primary)',
                                                            display: 'flex',
                                                            alignItems: 'center',
                                                            justifyContent: 'center',
                                                            color: '#fff',
                                                            fontWeight: '700',
                                                            fontSize: '0.9rem',
                                                        }}
                                                    >
                                                        {app.student_name?.charAt(0)?.toUpperCase() || '?'}
                                                    </div>
                                                    <div>
                                                        <div style={{ fontWeight: 600 }}>{app.student_name}</div>
                                                        <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                                            <FiMail size={12} />
                                                            {app.student_email}
                                                        </div>
                                                    </div>
                                                </div>
                                            </td>
                                            <td>
                                                <div style={{ fontWeight: 600 }}>{app.job_title}</div>
                                                <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>{app.job_location}</div>
                                            </td>
                                            <td>
                                                {new Date(app.applied_at).toLocaleDateString()}
                                            </td>
                                            <td>{getStatusBadge(app.status)}</td>
                                            <td>
                                                {app.ai_score !== null && app.ai_score !== undefined ? (() => {
                                                    const raw = Number(app.ai_score);
                                                    const isTenScale = Number.isFinite(raw) && raw <= 10;
                                                    const display = isTenScale ? `${raw.toFixed(1)}/10` : `${raw}%`;
                                                    const color = isTenScale
                                                        ? (raw >= 8 ? 'var(--color-success)' : raw >= 5 ? 'var(--color-warning)' : 'var(--color-error)')
                                                        : (raw >= 70 ? 'var(--color-success)' : raw >= 50 ? 'var(--color-warning)' : 'var(--color-error)');
                                                    return (
                                                        <span style={{ fontWeight: 700, color }}>
                                                            {display}
                                                        </span>
                                                    );
                                                })() : (
                                                    <span style={{ color: 'var(--color-text-muted)' }}>-</span>
                                                )}
                                            </td>
                                            <td>
                                                {(app.status === 'PENDING' || app.status === 'AI_ASSIGNED') && (
                                                    <div style={{ display: 'flex', gap: '8px' }}>
                                                        <button
                                                            className="btn btn-sm btn-primary"
                                                            onClick={() => setConfirmAiModal({ show: true, appId: app.id, studentId: app.student_id, jobId: app.job_id })}
                                                            disabled={actionLoading[app.id] === 'ai' || actionLoading[app.id] === 'delete'}
                                                            style={{
                                                                padding: '6px 12px',
                                                                fontSize: '0.8rem',
                                                                display: 'flex',
                                                                alignItems: 'center',
                                                                gap: '4px',
                                                            }}
                                                        >
                                                            {actionLoading[app.id] === 'ai' ? (
                                                                'Assigning...'
                                                            ) : app.status === 'AI_ASSIGNED' ? (
                                                                <><FiCheckCircle size={14} /> Reassign AI</>
                                                            ) : (
                                                                <><FiBriefcase size={14} /> Invite AI Interview</>
                                                            )}
                                                        </button>
                                                        <button
                                                            className="btn btn-sm"
                                                            onClick={() => setDeleteModal({ show: true, appId: app.id, studentName: app.student_name })}
                                                            disabled={actionLoading[app.id] === 'delete'}
                                                            style={{
                                                                padding: '6px 12px',
                                                                fontSize: '0.8rem',
                                                                display: 'flex',
                                                                alignItems: 'center',
                                                                gap: '4px',
                                                                backgroundColor: 'var(--color-bg-alt)',
                                                                color: 'var(--color-error)',
                                                                border: '1px solid var(--color-error)'
                                                            }}
                                                        >
                                                            <FiTrash2 size={14} /> {actionLoading[app.id] === 'delete' ? 'Deleting...' : 'Delete'}
                                                        </button>
                                                    </div>
                                                )}
                                                {app.status === 'AI_COMPLETED' && (
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                        {app.ai_session_id && (
                                                            <button
                                                                className="btn btn-sm btn-secondary"
                                                                onClick={() => fetchReport(app.ai_session_id)}
                                                                style={{
                                                                    padding: '6px 12px',
                                                                    fontSize: '0.8rem',
                                                                    display: 'inline-flex',
                                                                    alignItems: 'center',
                                                                    gap: '4px',
                                                                }}
                                                                title="View Full AI Interview Report"
                                                            >
                                                                <FiInfo size={14} /> Report
                                                            </button>
                                                        )}
                                                        <input
                                                            type="datetime-local"
                                                            className="input"
                                                            value={round2Schedule[app.id] || ''}
                                                            onChange={(e) => setRound2Schedule(prev => ({ ...prev, [app.id]: e.target.value }))}
                                                            min={new Date(Date.now() + 60000).toISOString().slice(0, 16)}
                                                            style={{ maxWidth: '220px' }}
                                                        />
                                                        <button
                                                            className="btn btn-sm btn-secondary"
                                                            onClick={() => inviteToRound2(app.id, app.pipeline_id)}
                                                            disabled={actionLoading[app.id] === 'round2'}
                                                            style={{
                                                                padding: '6px 12px',
                                                                fontSize: '0.8rem',
                                                                display: 'inline-flex',
                                                                alignItems: 'center',
                                                                gap: '6px',
                                                            }}
                                                        >
                                                            {actionLoading[app.id] === 'round2' ? 'Inviting...' : (<><FiBriefcase size={14} /> Round 2</>)}
                                                        </button>
                                                        <button
                                                            className="btn btn-sm"
                                                            onClick={() => setDeleteModal({ show: true, appId: app.id, studentName: app.student_name })}
                                                            disabled={actionLoading[app.id] === 'delete'}
                                                            style={{
                                                                padding: '6px 12px',
                                                                fontSize: '0.8rem',
                                                                display: 'inline-flex',
                                                                alignItems: 'center',
                                                                gap: '4px',
                                                                backgroundColor: 'var(--color-bg-alt)',
                                                                color: 'var(--color-error)',
                                                                border: '1px solid var(--color-error)'
                                                            }}
                                                        >
                                                            <FiTrash2 size={14} /> {actionLoading[app.id] === 'delete' ? 'Deleting...' : 'Delete'}
                                                        </button>
                                                    </div>
                                                )}
                                                {app.status === 'ROUND2_INVITED' && (
                                                    <div style={{ display: 'grid', gap: '6px' }}>
                                                        <span style={{ fontSize: '0.8rem', color: 'var(--color-secondary)' }}>
                                                            <FiCheckCircle style={{ marginRight: '4px' }} />
                                                            Round 2 Invited
                                                        </span>
                                                        {app.round2_scheduled_at && (
                                                            <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                                                                <FiClock style={{ marginRight: '4px' }} />
                                                                {new Date(app.round2_scheduled_at).toLocaleString()}
                                                            </span>
                                                        )}
                                                        <button
                                                            className="btn btn-sm"
                                                            onClick={() => setDeleteModal({ show: true, appId: app.id, studentName: app.student_name })}
                                                            disabled={actionLoading[app.id] === 'delete'}
                                                            style={{
                                                                padding: '6px 12px',
                                                                fontSize: '0.8rem',
                                                                display: 'flex',
                                                                alignItems: 'center',
                                                                gap: '4px',
                                                                backgroundColor: 'var(--color-bg-alt)',
                                                                color: 'var(--color-error)',
                                                                border: '1px solid var(--color-error)',
                                                                marginTop: '8px'
                                                            }}
                                                        >
                                                            <FiTrash2 size={14} /> Delete
                                                        </button>
                                                    </div>
                                                )}
                                                {app.status === 'HIRED' && (
                                                    <div style={{ display: 'grid', gap: '6px' }}>
                                                        <span style={{ fontSize: '0.8rem', color: 'var(--color-success)' }}>
                                                            <FiAward style={{ marginRight: '4px' }} />
                                                            Hired
                                                        </span>
                                                        <button
                                                            className="btn btn-sm"
                                                            onClick={() => setDeleteModal({ show: true, appId: app.id, studentName: app.student_name })}
                                                            disabled={actionLoading[app.id] === 'delete'}
                                                            style={{
                                                                padding: '6px 12px',
                                                                fontSize: '0.8rem',
                                                                display: 'flex',
                                                                alignItems: 'center',
                                                                gap: '4px',
                                                                backgroundColor: 'var(--color-bg-alt)',
                                                                color: 'var(--color-error)',
                                                                border: '1px solid var(--color-error)',
                                                                marginTop: '8px'
                                                            }}
                                                        >
                                                            <FiTrash2 size={14} /> Delete
                                                        </button>
                                                    </div>
                                                )}
                                                {app.status === 'REJECTED' && (
                                                    <div style={{ display: 'grid', gap: '6px' }}>
                                                        <button
                                                            className="btn btn-sm"
                                                            onClick={() => setDeleteModal({ show: true, appId: app.id, studentName: app.student_name })}
                                                            disabled={actionLoading[app.id] === 'delete'}
                                                            style={{
                                                                padding: '6px 12px',
                                                                fontSize: '0.8rem',
                                                                display: 'flex',
                                                                alignItems: 'center',
                                                                gap: '4px',
                                                                backgroundColor: 'var(--color-bg-alt)',
                                                                color: 'var(--color-error)',
                                                                border: '1px solid var(--color-error)',
                                                                marginTop: '8px'
                                                            }}
                                                        >
                                                            <FiTrash2 size={14} /> Delete
                                                        </button>
                                                    </div>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </div>

            {reportModal.show && reportModal.report && (
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.5)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 9999,
                }}>
                    <div style={{
                        backgroundColor: 'var(--color-bg-card)',
                        borderRadius: '8px',
                        padding: '24px',
                        maxWidth: '600px',
                        width: '90%',
                        maxHeight: '80vh',
                        overflowY: 'auto',
                    }}>
                        <h3 style={{ marginTop: 0, marginBottom: '16px' }}>AI Interview Report</h3>
                        <div style={{ marginBottom: '12px' }}><strong>Final Score:</strong> {reportModal.report.final_score ?? 'N/A'}</div>
                        <div style={{ marginBottom: '12px' }}><strong>Communication Score:</strong> {reportModal.report.communication_score ?? 'N/A'}</div>
                        <div style={{ marginBottom: '12px' }}><strong>Recommendation:</strong> {reportModal.report.recommendation ?? 'N/A'}</div>
                        <div style={{ marginBottom: '12px' }}><strong>Strengths:</strong> {reportModal.report.strengths?.length ? reportModal.report.strengths.join(', ') : 'N/A'}</div>
                        <div style={{ marginBottom: '12px' }}><strong>Weaknesses:</strong> {reportModal.report.weaknesses?.length ? reportModal.report.weaknesses.join(', ') : 'N/A'}</div>
                        <div style={{ marginBottom: '12px' }}><strong>Behavior Summary:</strong> {reportModal.report.behavior_summary ?? 'N/A'}</div>
                        <button
                            className="btn btn-secondary"
                            onClick={() => setReportModal({ show: false, report: null })}
                            style={{ marginTop: '16px' }}
                        >
                            Close
                        </button>
                    </div>
                </div>
            )}

            {/* AI Interview Rules Confirmation Modal */}
            {confirmAiModal.show && (
                <div style={{
                    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999,
                    backdropFilter: 'blur(4px)'
                }}>
                    <div style={{
                        backgroundColor: 'var(--color-bg-card)', borderRadius: '12px', padding: '32px', maxWidth: '600px', width: '90%',
                        boxShadow: '0 8px 32px rgba(0,0,0,0.2), inset 0 1px 1px rgba(255,255,255,0.05)',
                        border: '1px solid var(--color-border)', animation: 'slideUp 0.3s ease-out'
                    }}>
                        <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: 0, color: 'var(--color-text-primary)' }}>
                            <FiBriefcase style={{ color: 'var(--color-primary)' }} /> Send AI Interview
                        </h3>
                        <p style={{ color: 'var(--color-text-secondary)', marginBottom: '20px', lineHeight: '1.5' }}>
                            You are about to assign an AI Interview to this candidate. The AI enforces strict proctoring rules automatically:
                        </p>
                        <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 24px 0', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                            <li style={{ display: 'flex', gap: '10px', alignItems: 'center', fontSize: '0.95rem' }}>
                                <span style={{ color: 'var(--color-error)' }}>🖥️</span> <strong>Desktop Only:</strong> Mobile & Tablets are blocked.
                            </li>
                            <li style={{ display: 'flex', gap: '10px', alignItems: 'center', fontSize: '0.95rem' }}>
                                <span style={{ color: 'var(--color-error)' }}>📹</span> <strong>Strict Camera:</strong> Session ends if the face disappears.
                            </li>
                            <li style={{ display: 'flex', gap: '10px', alignItems: 'center', fontSize: '0.95rem' }}>
                                <span style={{ color: 'var(--color-error)' }}>📱</span> <strong>No Devices:</strong> Phones and notes trigger termination.
                            </li>
                            <li style={{ display: 'flex', gap: '10px', alignItems: 'center', fontSize: '0.95rem' }}>
                                <span style={{ color: 'var(--color-error)' }}>⚠️</span> <strong>No Tab Switch:</strong> Interview immediately terminates.
                            </li>
                        </ul>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                            <button className="btn btn-secondary" onClick={() => setConfirmAiModal({ show: false, appId: null, studentId: null, jobId: null })}>Cancel</button>
                            <button 
                                className="btn btn-primary" 
                                onClick={() => inviteToAiInterview(confirmAiModal.appId, confirmAiModal.studentId, confirmAiModal.jobId)}
                            >
                                Confirm & Assign
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Delete Confirmation Modal */}
            {deleteModal.show && (
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.5)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 9999,
                }}>
                    <div style={{
                        backgroundColor: 'var(--color-bg-card)',
                        borderRadius: '8px',
                        padding: '24px',
                        maxWidth: '400px',
                        width: '90%',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                    }}>
                        <h3 style={{ marginTop: 0, marginBottom: '16px', color: 'var(--color-error)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <FiTrash2 /> Delete Application
                        </h3>
                        <p style={{ marginBottom: '24px', lineHeight: '1.5' }}>
                            Are you sure you want to delete the application for <strong>{deleteModal.studentName}</strong>? This action cannot be undone.
                        </p>
                        <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                            <button
                                className="btn btn-secondary"
                                onClick={() => setDeleteModal({ show: false, appId: null, studentName: '' })}
                            >
                                Cancel
                            </button>
                            <button
                                className="btn"
                                onClick={handleDeleteApplication}
                                style={{ backgroundColor: 'var(--color-error)', color: 'white' }}
                            >
                                Delete
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
