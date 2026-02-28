import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { FiInbox, FiCheckCircle, FiXCircle, FiClock, FiBriefcase, FiUser, FiMail, FiAward } from 'react-icons/fi';

export default function Applications() {
    const { user } = useAuth();
    const [applications, setApplications] = useState([]);
    const [jobs, setJobs] = useState([]);
    const [selectedJobId, setSelectedJobId] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [actionLoading, setActionLoading] = useState({});

    const fetchJobs = async () => {
        try {
            const res = await api.get('/jobs/my');
            setJobs(res.data || []);
        } catch (e) {
            console.error('Failed to fetch jobs:', e);
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
            AI_COMPLETED: { icon: FiAward, className: 'status-badge-approved', label: 'AI Completed' },
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
                                                {app.ai_score !== null && app.ai_score !== undefined ? (
                                                    <span
                                                        style={{
                                                            fontWeight: 700,
                                                            color: app.ai_score >= 70 ? 'var(--color-success)' : app.ai_score >= 50 ? 'var(--color-warning)' : 'var(--color-error)',
                                                        }}
                                                    >
                                                        {app.ai_score}%
                                                    </span>
                                                ) : (
                                                    <span style={{ color: 'var(--color-text-muted)' }}>-</span>
                                                )}
                                            </td>
                                            <td>
                                                {(app.status === 'PENDING' || app.status === 'AI_ASSIGNED') && (
                                                    <button
                                                        className="btn btn-sm btn-primary"
                                                        onClick={() => inviteToAiInterview(app.id, app.student_id, app.job_id)}
                                                        disabled={actionLoading[app.id] === 'ai'}
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
                                                )}
                                                {app.status === 'AI_COMPLETED' && (
                                                    <span style={{ fontSize: '0.8rem', color: 'var(--color-success)' }}>
                                                        <FiCheckCircle style={{ marginRight: '4px' }} />
                                                        Ready for Round 2
                                                    </span>
                                                )}
                                                {app.status === 'ROUND2_INVITED' && (
                                                    <span style={{ fontSize: '0.8rem', color: 'var(--color-secondary)' }}>
                                                        <FiCheckCircle style={{ marginRight: '4px' }} />
                                                        Round 2 Invited
                                                    </span>
                                                )}
                                                {app.status === 'HIRED' && (
                                                    <span style={{ fontSize: '0.8rem', color: 'var(--color-success)' }}>
                                                        <FiAward style={{ marginRight: '4px' }} />
                                                        Hired
                                                    </span>
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
        </div>
    );
}
