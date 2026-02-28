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

    const [hiredPipelineId, setHiredPipelineId] = useState('');
    const [hiredCompanyName, setHiredCompanyName] = useState('');

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

    const onMarkHired = async (e) => {
        e.preventDefault();
        try {
            setError('');
            await api.put('/pipeline/mark-hired', {
                pipeline_id: hiredPipelineId,
                hired_company_name: hiredCompanyName,
            });
            setHiredPipelineId('');
            setHiredCompanyName('');
            await fetchData();
        } catch (err) {
            setError(err?.response?.data?.detail || 'Failed to mark hired');
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
                    <div className="dashboard-card fade-in-up">
                        <h3>Assign Round 1 (AI) Interview</h3>
                        <form onSubmit={onAssignAi} style={{ display: 'grid', gap: '12px', marginTop: '12px' }}>
                            <select className="input" value={jobId} onChange={(e) => setJobId(e.target.value)} required>
                                <option value="">Select Job</option>
                                {jobs.map((j) => (
                                    <option key={j.id} value={j.id}>{j.title}</option>
                                ))}
                            </select>
                            <input
                                className="input"
                                placeholder="Student ID (UUID)"
                                value={studentId}
                                onChange={(e) => setStudentId(e.target.value)}
                                required
                            />
                            <button className="btn btn-primary" type="submit">Assign AI Interview</button>
                        </form>
                        <p style={{ marginTop: '10px', color: 'var(--color-text-muted)' }}>
                            For now, paste the student UUID. Next step: add college/department/semester student picker.
                        </p>
                    </div>

                    <div className="dashboard-card fade-in-up">
                        <h3>Invite Round 2 (Human)</h3>
                        <form onSubmit={onInviteRound2} style={{ display: 'grid', gap: '12px', marginTop: '12px' }}>
                            <input
                                className="input"
                                placeholder="Pipeline ID (UUID)"
                                value={round2PipelineId}
                                onChange={(e) => setRound2PipelineId(e.target.value)}
                                required
                            />
                            <input
                                className="input"
                                placeholder="Meeting Link / Calendar Invite URL"
                                value={round2Link}
                                onChange={(e) => setRound2Link(e.target.value)}
                                required
                            />
                            <button className="btn btn-primary" type="submit">Invite Round 2</button>
                        </form>
                    </div>

                    <div className="dashboard-card fade-in-up">
                        <h3>Mark Hired</h3>
                        <form onSubmit={onMarkHired} style={{ display: 'grid', gap: '12px', marginTop: '12px' }}>
                            <input
                                className="input"
                                placeholder="Pipeline ID (UUID)"
                                value={hiredPipelineId}
                                onChange={(e) => setHiredPipelineId(e.target.value)}
                                required
                            />
                            <input
                                className="input"
                                placeholder="Hired Company Name"
                                value={hiredCompanyName}
                                onChange={(e) => setHiredCompanyName(e.target.value)}
                                required
                            />
                            <button className="btn btn-primary" type="submit">Mark Hired</button>
                        </form>
                    </div>
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
                                    <th>Status</th>
                                    <th>Job ID</th>
                                    <th>Student ID</th>
                                    <th>Session</th>
                                    <th>Round 2</th>
                                    <th>Hired</th>
                                </tr>
                            </thead>
                            <tbody>
                                {rows.map((p, idx) => (
                                    <tr key={p.id} className={idx % 2 === 0 ? 'row-even' : 'row-odd'}>
                                        <td style={{ fontWeight: 700 }}>{p.status}</td>
                                        <td style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>{p.job_id}</td>
                                        <td style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>{p.student_id}</td>
                                        <td style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>{p.ai_session_id || '-'}</td>
                                        <td>{p.round2_link ? <a href={p.round2_link} target="_blank" rel="noreferrer">Link</a> : '-'}</td>
                                        <td>{p.hired_company_name || '-'}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
