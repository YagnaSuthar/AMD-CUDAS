import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { FiUsers, FiBookOpen, FiTrendingUp, FiAlertTriangle } from 'react-icons/fi';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';

/* ── SVG Gauge ─────────────────────────────────────────────────────── */
function Gauge({ value, max = 100, label, color = '#00bcd4' }) {
    const pct = Math.min((value / max) * 100, 100);
    const radius = 70;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (pct / 100) * circumference;

    return (
        <div className="gauge-container">
            <svg width="160" height="160" viewBox="0 0 160 160">
                <circle cx="80" cy="80" r={radius} fill="none" stroke="var(--color-border)" strokeWidth="12" />
                <circle cx="80" cy="80" r={radius} fill="none"
                    stroke={color} strokeWidth="12"
                    strokeDasharray={circumference} strokeDashoffset={offset}
                    strokeLinecap="round" transform="rotate(-90 80 80)"
                    style={{ transition: 'stroke-dashoffset 1s ease' }}
                />
                <text x="80" y="75" textAnchor="middle" fill="var(--color-text-primary)"
                    fontFamily="var(--font-heading)" fontSize="24" fontWeight="700">
                    {pct.toFixed(1)}%
                </text>
                <text x="80" y="100" textAnchor="middle" fill="var(--color-text-muted)"
                    fontFamily="var(--font-body)" fontSize="11">{label}</text>
            </svg>
        </div>
    );
}

const PIE_COLORS = ['#22c55e', '#ef4444', '#f59e0b'];

export default function HodDashboard() {
    const [faculty, setFaculty] = useState([]);
    const [mentors, setMentors] = useState([]);
    const [mentorForm, setMentorForm] = useState({ faculty_id: '', semester: '' });
    const [mentorLoading, setMentorLoading] = useState(false);

    useEffect(() => {
        (async () => {
            try {
                const [ovRes, facRes, mentRes] = await Promise.all([
                    api.get('/college/hod/overview'),
                    api.get('/college/users'), // List direct subordinates
                    api.get('/college/hod/mentors')
                ]);
                setData(ovRes.data);
                setFaculty(facRes.data.filter(u => u.role === 'FACULTY'));
                setMentors(mentRes.data);
            } catch (err) { console.error(err); }
            finally { setLoading(false); }
        })();
    }, []);

    const handleAssignMentor = async (e) => {
        e.preventDefault();
        if (!mentorForm.faculty_id || !mentorForm.semester) {
            alert('Please select faculty and semester');
            return;
        }
        setMentorLoading(true);
        try {
            await api.post('/college/hod/assign-mentor', {
                faculty_id: mentorForm.faculty_id,
                semester: parseInt(mentorForm.semester)
            });
            const res = await api.get('/college/hod/mentors');
            setMentors(res.data);
            setMentorForm({ faculty_id: '', semester: '' });
        } catch (err) {
            alert(err.response?.data?.detail || 'Assignment failed');
        } finally {
            setMentorLoading(false);
        }
    };
    // ... rest of the file ...

    if (loading) return <div className="spinner" style={{ margin: '40px auto' }}></div>;

    const passCount = (data?.top_students || []).length;
    const failCount = (data?.weak_students || []).length;
    const totalStudents = data?.total_students || 0;
    const avgCount = Math.max(totalStudents - passCount - failCount, 0);

    const pieData = [
        { name: 'Above Average', value: passCount },
        { name: 'Below 40%', value: failCount },
        { name: 'Average', value: avgCount },
    ].filter(d => d.value > 0);

    return (
        <div className="dashboard-content">
            <div className="page-header slide-in-left">
                <h1 className="gradient-text">Department Overview</h1>
                <p>Department: <strong>{user.department || 'N/A'}</strong></p>
            </div>

            <div className="stats-grid fade-in-up">
                <div className="stat-card">
                    <div className="stat-card-header">
                        <span className="stat-card-label">Faculty</span>
                        <div className="stat-card-icon" style={{ background: 'var(--gradient-primary)' }}><FiBookOpen /></div>
                    </div>
                    <div className="stat-card-value">{data?.total_faculty || 0}</div>
                </div>
                <div className="stat-card">
                    <div className="stat-card-header">
                        <span className="stat-card-label">Students</span>
                        <div className="stat-card-icon" style={{ background: 'var(--gradient-secondary)' }}><FiUsers /></div>
                    </div>
                    <div className="stat-card-value">{data?.total_students || 0}</div>
                </div>
                <div className="stat-card">
                    <div className="stat-card-header">
                        <span className="stat-card-label">Dept Average</span>
                        <div className="stat-card-icon" style={{ background: 'var(--color-success)' }}><FiTrendingUp /></div>
                    </div>
                    <div className="stat-card-value">{data?.department_average || 0}%</div>
                </div>
                <div className="stat-card">
                    <div className="stat-card-header">
                        <span className="stat-card-label">Weak Students</span>
                        <div className="stat-card-icon" style={{ background: 'var(--color-error)' }}><FiAlertTriangle /></div>
                    </div>
                    <div className="stat-card-value">{failCount}</div>
                </div>
            </div>

            <div className="dashboard-row fade-in-up fade-in-delay-1">
                <div className="dashboard-card gauge-card">
                    <h3>Department Performance</h3>
                    <Gauge value={data?.department_average || 0} label="Dept Average" color="#a87ef0" />
                </div>

                <div className="dashboard-card chart-card">
                    <h3>Student Distribution</h3>
                    {pieData.length > 0 ? (
                        <ResponsiveContainer width="100%" height={260}>
                            <PieChart>
                                <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={90}
                                    dataKey="value" paddingAngle={3} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                                    labelLine={false}
                                    style={{ fontSize: '0.7rem' }}>
                                    {pieData.map((_, i) => (
                                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip contentStyle={{ background: 'var(--color-bg-card)', border: '1px solid var(--color-border)', borderRadius: '8px' }} />
                            </PieChart>
                        </ResponsiveContainer>
                    ) : (
                        <p className="text-muted" style={{ textAlign: 'center', padding: '40px' }}>No data available</p>
                    )}
                </div>
            </div>

            {/* Mentor Assignment Section */}
            <div className="dashboard-card fade-in-up fade-in-delay-1" style={{ marginTop: '24px' }}>
                <div className="stat-card-header">
                    <h3 style={{ margin: 0 }}>Assign Mentor</h3>
                </div>
                <form onSubmit={handleAssignMentor} className="modal-form" style={{ marginTop: '16px', display: 'flex', gap: '12px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
                    <div className="form-group" style={{ flex: 2, minWidth: '200px' }}>
                        <label>Select Faculty</label>
                        <select
                            className="form-input"
                            value={mentorForm.faculty_id}
                            onChange={(e) => setMentorForm({ ...mentorForm, faculty_id: e.target.value })}
                        >
                            <option value="">Select Faculty...</option>
                            {faculty.map(f => (
                                <option key={f.id} value={f.id}>{f.name}</option>
                            ))}
                        </select>
                    </div>
                    <div className="form-group" style={{ flex: 1, minWidth: '100px' }}>
                        <label>Semester</label>
                        <input
                            type="number"
                            className="form-input"
                            placeholder="e.g. 6"
                            value={mentorForm.semester}
                            onChange={(e) => setMentorForm({ ...mentorForm, semester: e.target.value })}
                        />
                    </div>
                    <button type="submit" className="btn btn-primary" style={{ height: '42px' }} disabled={mentorLoading}>
                        {mentorLoading ? 'Assigning...' : 'Assign Mentor'}
                    </button>
                </form>

                {mentors.length > 0 && (
                    <div className="mentor-list" style={{ marginTop: '24px' }}>
                        <h4 style={{ marginBottom: '12px', fontSize: '0.9rem', color: 'var(--color-text-muted)' }}>Active Mentor Assignments</h4>
                        <div className="mentor-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '12px' }}>
                            {mentors.map(m => (
                                <div key={m.id} className="mentor-item" style={{ background: 'var(--color-bg-card)', border: '1px solid var(--color-border)', borderRadius: '8px', padding: '12px' }}>
                                    <div style={{ fontWeight: 600 }}>{m.faculty_name}</div>
                                    <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>Semester {m.semester}</div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* Top 10 Students */}
            {(data?.top_students || []).length > 0 && (
                <div className="data-table-container fade-in-up fade-in-delay-2">
                    <div className="data-table-header">
                        <h3>Top 10 Students</h3>
                    </div>
                    <div className="table-scroll-wrapper">
                        <table className="data-table enhanced-table">
                            <thead>
                                <tr>
                                    <th>Rank</th>
                                    <th>Name</th>
                                    <th>Email</th>
                                    <th>Average %</th>
                                </tr>
                            </thead>
                            <tbody>
                                {data.top_students.map((s, i) => (
                                    <tr key={s.id} className={i % 2 === 0 ? 'row-even' : 'row-odd'}>
                                        <td>
                                            <span className={`rank-badge rank-${i < 3 ? i + 1 : 'default'}`}>#{i + 1}</span>
                                        </td>
                                        <td style={{ fontWeight: 600 }}>{s.name}</td>
                                        <td className="cell-email">{s.email}</td>
                                        <td>
                                            <div className="progress-bar-wrapper">
                                                <div className="progress-bar-fill" style={{ width: `${Math.min(s.average, 100)}%`, background: 'var(--color-success)' }} />
                                            </div>
                                            <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>{s.average}%</span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Weak Students */}
            {failCount > 0 && (
                <div className="data-table-container fade-in-up fade-in-delay-3" style={{ marginTop: '24px' }}>
                    <div className="data-table-header" style={{ borderLeftColor: 'var(--color-error)' }}>
                        <h3 style={{ color: 'var(--color-error)' }}>⚠ Students Below 40%</h3>
                    </div>
                    <div className="table-scroll-wrapper">
                        <table className="data-table">
                            <thead>
                                <tr><th>Name</th><th>Email</th><th>Average %</th></tr>
                            </thead>
                            <tbody>
                                {data.weak_students.map((s, i) => (
                                    <tr key={s.id}>
                                        <td style={{ fontWeight: 600 }}>{s.name}</td>
                                        <td className="cell-email">{s.email}</td>
                                        <td style={{ color: 'var(--color-error)', fontWeight: 700 }}>{s.average}%</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
}
