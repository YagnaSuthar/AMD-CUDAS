import { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';

export default function Jobs() {
    const { user } = useAuth();
    const isRecruiter = user?.role === 'RECRUITER';

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const [jobs, setJobs] = useState([]);

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

    useEffect(() => {
        fetchJobs();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [user?.role]);

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
                <div className="dashboard-card fade-in-up" style={{ marginBottom: '20px' }}>
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
                            rows={6}
                            required
                        />
                        <button className="btn btn-primary" type="submit">
                            Create Job
                        </button>
                    </form>
                </div>
            )}

            <div className="data-table-container fade-in-up">
                <div className="data-table-header">
                    <h3>
                        Job Listings <span className="table-count">({sortedJobs.length})</span>
                    </h3>
                </div>

                {sortedJobs.length === 0 ? (
                    <div className="empty-state">
                        <h3>No Jobs</h3>
                        <p style={{ color: 'var(--color-text-muted)' }}>
                            {isRecruiter ? 'Create your first job posting.' : 'No jobs have been posted yet.'}
                        </p>
                    </div>
                ) : (
                    <div className="table-scroll-wrapper">
                        <table className="data-table enhanced-table">
                            <thead>
                                <tr>
                                    <th>Title</th>
                                    <th>Package</th>
                                    <th>Bond</th>
                                    <th>Location</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {sortedJobs.map((j, idx) => (
                                    <tr key={j.id || idx} className={idx % 2 === 0 ? 'row-even' : 'row-odd'}>
                                        <td style={{ fontWeight: 600 }}>{j.title}</td>
                                        <td>{j.package_lpa || '-'}</td>
                                        <td>{j.bond || '-'}</td>
                                        <td>{j.location || '-'}</td>
                                        <td>{j.status || '-'}</td>
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
