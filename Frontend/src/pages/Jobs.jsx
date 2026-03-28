import { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { FiBriefcase, FiCheckCircle, FiClock, FiAward, FiMic, FiMapPin, FiDollarSign, FiShield, FiX, FiTrash2 } from 'react-icons/fi';

export default function Jobs() {
    const { user } = useAuth();
    const isRecruiter = user?.role === 'RECRUITER';
    const isStudent = user?.role === 'STUDENT';

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const [jobs, setJobs] = useState([]);
    const [applications, setApplications] = useState([]);
    const [selectedJob, setSelectedJob] = useState(null);

    const [title, setTitle] = useState('');
    const [packageLpa, setPackageLpa] = useState('');
    const [bond, setBond] = useState('');
    const [location, setLocation] = useState('');
    const [description, setDescription] = useState('');

    const canCreate = isRecruiter;

    const fetchJobs = async () => {
        try {
            setError('');
            setLoading(true);
            const url = isRecruiter ? '/jobs/my' : '/jobs/';
            const res = await api.get(url);
            setJobs(res.data || []);
        } catch (err) {
            setError('Failed to load jobs');
        } finally {
            setLoading(false);
        }
    };

    const fetchApplications = async () => {
        if (!isStudent) return;
        try {
            const res = await api.get('/applications/my');
            setApplications(res.data || []);
        } catch (err) {
            console.error('Failed to fetch applications:', err);
        }
    };

    const applyToJob = async (jobId) => {
        if (!isStudent) return;
        try {
            await api.post('/applications/apply', { job_id: jobId });
            await fetchApplications();
            alert('Applied successfully!');
        } catch (err) {
            setError(err?.response?.data?.detail || 'Failed to apply');
        }
    };

    useEffect(() => {
        fetchJobs();
        fetchApplications();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [user?.role]);

    const deleteJob = async (jobId, e) => {
        e.stopPropagation();
        if (!window.confirm("Are you sure you want to delete this job posting? This action cannot be undone.")) return;
        try {
            await api.delete(`/jobs/${jobId}`);
            setJobs(prevJobs => prevJobs.filter(j => j.id !== jobId));
            if (selectedJob && selectedJob.id === jobId) setSelectedJob(null);
        } catch (err) {
            setError(err?.response?.data?.detail || 'Failed to delete job');
        }
    };

    const getApplicationForJob = (jobId) => {
        return applications.find(app => app.job_id === jobId);
    };

    const getStatusDisplay = (status) => {
        const config = {
            PENDING: { icon: FiClock, color: 'var(--color-warning)', label: 'Applied - Pending' },
            AI_ASSIGNED: { icon: FiMic, color: 'var(--color-secondary)', label: 'AI Interview Assigned' },
            AI_COMPLETED: { icon: FiAward, color: 'var(--color-success)', label: 'AI Completed' },
            ROUND2_INVITED: { icon: FiCheckCircle, color: 'var(--color-success)', label: 'Round 2 Invited' },
            HIRED: { icon: FiAward, color: 'var(--color-success)', label: 'Hired!' },
            REJECTED: { icon: FiClock, color: 'var(--color-error)', label: 'Not Selected' },
        };
        return config[status] || config.PENDING;
    };

    const onCreate = async (e) => {
        e.preventDefault();
        if (!canCreate) return;

        try {
            setError('');
            await api.post('/jobs/', {
                title,
                description,
                package_lpa: packageLpa || null,
                bond: bond || null,
                location: location || null,
            });
            setTitle('');
            setPackageLpa('');
            setBond('');
            setLocation('');
            setDescription('');
            await fetchJobs();
        } catch (err) {
            setError(err?.response?.data?.detail || 'Failed to create job');
        }
    };

    const sortedJobs = useMemo(() => {
        const arr = Array.isArray(jobs) ? [...jobs] : [];
        arr.sort((a, b) => {
            const ta = new Date(a.created_at).getTime();
            const tb = new Date(b.created_at).getTime();
            return tb - ta;
        });
        return arr;
    }, [jobs]);

    if (loading) return <div className="spinner" style={{ margin: '40px auto' }}></div>;

    return (
        <div className="dashboard-content">
            <div className="page-header slide-in-left">
                <h1 className="gradient-text">Jobs</h1>
                <p style={{ color: 'var(--color-text-secondary)' }}>
                    {isRecruiter ? 'Create and manage job postings for students.' : 'Browse job postings shared by recruiters.'}
                </p>
            </div>

            {error && (
                <div className="alert alert-error" style={{ marginBottom: '16px' }}>
                    {error}
                </div>
            )}

            {canCreate && (
                <div className="dashboard-card fade-in-up" style={{ marginBottom: '24px' }}>
                    <h3>Create Job</h3>
                    <form onSubmit={onCreate} style={{ display: 'grid', gap: '12px', marginTop: '12px' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                            <input
                                className="input"
                                placeholder="Job Title"
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                                required
                            />
                            <input
                                className="input"
                                placeholder="Package (LPA)"
                                value={packageLpa}
                                onChange={(e) => setPackageLpa(e.target.value)}
                            />
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                            <input
                                className="input"
                                placeholder="Bond (e.g. 2 years / none)"
                                value={bond}
                                onChange={(e) => setBond(e.target.value)}
                            />
                            <input
                                className="input"
                                placeholder="Location"
                                value={location}
                                onChange={(e) => setLocation(e.target.value)}
                            />
                        </div>
                        <textarea
                            className="input"
                            placeholder="Job Description / JD"
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            rows={4}
                            required
                        />
                        <button className="btn btn-primary" type="submit">
                            Create Job
                        </button>
                    </form>
                </div>
            )}

            {/* Job Listings Header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }} className="fade-in-up fade-in-delay-1">
                <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '1rem' }}>
                    Job Listings <span className="table-count">({sortedJobs.length})</span>
                </h3>
            </div>

            {sortedJobs.length === 0 ? (
                <div className="empty-state fade-in-up">
                    <FiBriefcase size={48} style={{ opacity: 0.4, marginBottom: '12px' }} />
                    <h3>No Jobs</h3>
                    <p style={{ color: 'var(--color-text-muted)' }}>
                        {isRecruiter ? 'Create your first job posting.' : 'No jobs have been posted yet.'}
                    </p>
                </div>
            ) : (
                <div className="jobs-grid">
                    {sortedJobs.map((j, idx) => {
                        const app = isStudent ? getApplicationForJob(j.id) : null;
                        const statusDisplay = app ? getStatusDisplay(app.status) : null;
                        const StatusIcon = statusDisplay?.icon;

                        return (
                            <div
                                key={j.id || idx}
                                className="job-card"
                                style={{ animationDelay: `${idx * 0.07}s`, cursor: 'pointer' }}
                                onClick={() => setSelectedJob(j)}
                            >
                                {/* Gradient accent bar */}
                                <div className="job-card-accent"></div>

                                <div className="job-card-body">
                                    <div className="job-card-title">
                                        <FiBriefcase size={16} style={{ marginRight: '8px', opacity: 0.6, verticalAlign: 'text-bottom' }} />
                                        {j.title}
                                    </div>

                                    {j.description && (
                                        <div className="job-card-desc">{j.description}</div>
                                    )}

                                    <div className="job-meta-list">
                                        {j.package_lpa && (
                                            <div className="job-meta-item">
                                                <div className="job-meta-icon">
                                                    <FiDollarSign size={14} />
                                                </div>
                                                <div>
                                                    <div className="job-meta-label">Package</div>
                                                    <div className="job-meta-value">{j.package_lpa} LPA</div>
                                                </div>
                                            </div>
                                        )}
                                        {j.location && (
                                            <div className="job-meta-item">
                                                <div className="job-meta-icon">
                                                    <FiMapPin size={14} />
                                                </div>
                                                <div>
                                                    <div className="job-meta-label">Location</div>
                                                    <div className="job-meta-value">{j.location}</div>
                                                </div>
                                            </div>
                                        )}
                                        {j.bond && (
                                            <div className="job-meta-item">
                                                <div className="job-meta-icon">
                                                    <FiShield size={14} />
                                                </div>
                                                <div>
                                                    <div className="job-meta-label">Bond</div>
                                                    <div className="job-meta-value">{j.bond}</div>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {/* Footer with actions */}
                                <div className="job-card-footer">
                                    {isStudent && (
                                        <>
                                            {!app ? (
                                                <button
                                                    className="btn btn-sm btn-primary"
                                                    onClick={(e) => { e.stopPropagation(); applyToJob(j.id); }}
                                                >
                                                    Apply Now
                                                </button>
                                            ) : app.status === 'AI_ASSIGNED' ? (
                                                <a
                                                    href="/dashboard/interview"
                                                    className="btn btn-sm btn-secondary"
                                                    style={{ textDecoration: 'none' }}
                                                    onClick={(e) => e.stopPropagation()}
                                                >
                                                    <FiMic size={14} />
                                                    Start AI Interview
                                                </a>
                                            ) : app.status === 'AI_COMPLETED' ? (
                                                <span style={{ fontSize: '0.82rem', color: 'var(--color-success)', fontWeight: 600 }}>
                                                    <FiAward size={14} style={{ marginRight: '4px', verticalAlign: 'middle' }} />
                                                    Score: {app.ai_score || 'Pending'}%
                                                </span>
                                            ) : (
                                                <span></span>
                                            )}

                                            {statusDisplay && (
                                                <div className="job-status-display" style={{ color: statusDisplay.color }}>
                                                    {StatusIcon && <StatusIcon size={14} />}
                                                    <span>{statusDisplay.label}</span>
                                                </div>
                                            )}
                                        </>
                                    )}

                                    {isRecruiter && (
                                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                                            <span style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)' }}>
                                                {j.status || 'Active'}
                                            </span>
                                            <button 
                                                className="btn btn-sm" 
                                                style={{ padding: '6px', color: '#ff4d4d', background: 'rgba(255, 77, 77, 0.1)', border: '1px solid rgba(255, 77, 77, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                                                onClick={(e) => deleteJob(j.id, e)}
                                                title="Delete Job"
                                            >
                                                <FiTrash2 size={16} />
                                            </button>
                                        </div>
                                    )}

                                    {!isStudent && !isRecruiter && <span></span>}
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Job Details Modal */}
            {selectedJob && (
                <div className="job-modal-overlay fade-in" onClick={() => setSelectedJob(null)}>
                    <div className="job-modal-content slide-in-up" onClick={(e) => e.stopPropagation()}>
                        <button className="job-modal-close" onClick={() => setSelectedJob(null)}>
                            <FiX size={24} />
                        </button>
                        
                        <div className="job-modal-header">
                            <h2 className="gradient-text" style={{ fontSize: '1.8rem', marginBottom: '8px' }}>
                                <FiBriefcase size={24} style={{ marginRight: '12px', verticalAlign: 'bottom', color: 'var(--color-secondary)' }} />
                                {selectedJob.title}
                            </h2>
                            <div className="job-meta-list" style={{ marginTop: '20px' }}>
                                {selectedJob.package_lpa && (
                                    <div className="job-meta-item">
                                        <div className="job-meta-icon"><FiDollarSign size={16} /></div>
                                        <div><div className="job-meta-label">Package</div><div className="job-meta-value" style={{ fontSize: '1rem' }}>{selectedJob.package_lpa} LPA</div></div>
                                    </div>
                                )}
                                {selectedJob.location && (
                                    <div className="job-meta-item">
                                        <div className="job-meta-icon"><FiMapPin size={16} /></div>
                                        <div><div className="job-meta-label">Location</div><div className="job-meta-value" style={{ fontSize: '1rem' }}>{selectedJob.location}</div></div>
                                    </div>
                                )}
                                {selectedJob.bond && (
                                    <div className="job-meta-item">
                                        <div className="job-meta-icon"><FiShield size={16} /></div>
                                        <div><div className="job-meta-label">Bond</div><div className="job-meta-value" style={{ fontSize: '1rem' }}>{selectedJob.bond}</div></div>
                                    </div>
                                )}
                            </div>
                        </div>

                        <div className="job-modal-body">
                            <h4 style={{ color: 'var(--color-secondary)', fontFamily: 'var(--font-heading)', letterSpacing: '1px', marginBottom: '12px', textTransform: 'uppercase' }}>Job Description</h4>
                            <div className="job-modal-description">
                                {selectedJob.description?.split('\\n').map((para, i) => (
                                    <p key={i}>{para}</p>
                                ))}
                            </div>
                        </div>

                        {isStudent && (
                            <div className="job-modal-footer">
                                {(() => {
                                    const app = getApplicationForJob(selectedJob.id);
                                    if (!app) {
                                        return <button className="btn btn-primary" style={{ width: '100%', padding: '14px' }} onClick={(e) => { e.stopPropagation(); applyToJob(selectedJob.id); }}>Apply Now</button>;
                                    } else {
                                        const statusDisplay = getStatusDisplay(app.status);
                                        const StatusIcon = statusDisplay?.icon;
                                        return (
                                            <div className="job-status-display" style={{ color: statusDisplay.color, justifyContent: 'center', padding: '14px', background: 'rgba(255,255,255,0.03)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)', fontSize: '1.05rem' }}>
                                                {StatusIcon && <StatusIcon size={20} />}
                                                <span>You have already applied! Status: {statusDisplay.label}</span>
                                            </div>
                                        );
                                    }
                                })()}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
