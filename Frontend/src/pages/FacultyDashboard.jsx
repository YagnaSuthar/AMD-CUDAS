import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { FiUsers, FiBookOpen, FiLayers, FiTrendingUp, FiCalendar } from 'react-icons/fi';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const COLORS = ['#00bcd4', '#a87ef0', '#ffb703', '#22c55e', '#ef4444', '#667eea'];

export default function FacultyDashboard() {
    const { user } = useAuth();
    const [data, setData] = useState(null);
    const [mentors, setMentors] = useState([]);
    const [subjects, setSubjects] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        (async () => {
            try {
                const [overviewRes, mentorRes, subjectRes] = await Promise.all([
                    api.get('/college/faculty/overview'),
                    api.get(`/api/mentor/faculty/${user.id}`),
                    api.get(`/api/subject/faculty/${user.id}`)
                ]);
                setData(overviewRes.data);
                setMentors(mentorRes.data);
                setSubjects(subjectRes.data);
            } catch (err) { console.error(err); }
            finally { setLoading(false); }
        })();
    }, [user.id]);

    if (loading) return <div className="spinner" style={{ margin: '40px auto' }}></div>;

    const chartData = (data?.subject_stats || []).map(s => ({
        name: s.subject_name.length > 12 ? s.subject_name.slice(0, 12) + '…' : s.subject_name,
        'Avg %': s.average_marks,
        Students: s.student_count,
    }));

    return (
        <div className="dashboard-content">
            <div className="page-header slide-in-left">
                <h1 className="gradient-text">Class Overview</h1>
                <p>Welcome, Professor <strong>{user.name}</strong></p>
            </div>

            <div className="stats-grid fade-in-up">
                {/* Mentor Responsibilities Card */}
                <div className="stat-card" style={{ display: 'flex', flexDirection: 'column', height: '220px' }}>
                    <div className="stat-card-header" style={{ marginBottom: '12px' }}>
                        <span className="stat-card-label" style={{ fontWeight: 700 }}>Mentor Responsibilities</span>
                        <div className="stat-card-icon" style={{ background: 'var(--gradient-primary)' }}><FiLayers /></div>
                    </div>
                    <div style={{ flex: 1, overflowY: 'auto', paddingRight: '4px' }}>
                        {mentors.length > 0 ? (
                            <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                {mentors.map((m, i) => (
                                    <li key={i} style={{ fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <span style={{ color: 'var(--color-primary)', fontWeight: 'bold' }}>•</span>
                                        Semester {m.semester}
                                    </li>
                                ))}
                            </ul>
                        ) : (
                            <span style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem', fontStyle: 'italic' }}>None assigned</span>
                        )}
                    </div>
                </div>

                {/* Subjects Assigned Card */}
                <div className="stat-card" style={{ display: 'flex', flexDirection: 'column', height: '220px' }}>
                    <div className="stat-card-header" style={{ marginBottom: '12px' }}>
                        <span className="stat-card-label" style={{ fontWeight: 700 }}>Subjects Assigned</span>
                        <div className="stat-card-icon" style={{ background: 'var(--gradient-secondary)' }}><FiBookOpen /></div>
                    </div>
                    <div style={{ flex: 1, overflowY: 'auto', paddingRight: '4px' }}>
                        {subjects.length > 0 ? (
                            <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                {subjects.map((s, i) => (
                                    <li key={i} style={{ fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <span style={{ color: 'var(--color-secondary)', fontWeight: 'bold' }}>•</span>
                                        {s.subject_name} (Sem {s.semester})
                                    </li>
                                ))}
                            </ul>
                        ) : (
                            <span style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem', fontStyle: 'italic' }}>None assigned</span>
                        )}
                    </div>
                </div>

                {/* Total Students Card (Preserved) */}
                <div className="stat-card" style={{ display: 'flex', flexDirection: 'column', height: '220px' }}>
                    <div className="stat-card-header">
                        <span className="stat-card-label">Total Students</span>
                        <div className="stat-card-icon" style={{ background: 'var(--color-success)' }}><FiUsers /></div>
                    </div>
                    <div className="stat-card-value" style={{ marginTop: 'auto' }}>{data?.total_students || 0}</div>
                </div>
            </div>

            {/* Department Exam Timetable (Active) */}
            {data?.active_timetable?.length > 0 && (
                <div className="dashboard-card fade-in-up fade-in-delay-1" style={{ marginBottom: '24px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
                        <FiCalendar style={{ color: 'var(--color-primary)', fontSize: '1.2rem' }} />
                        <h3 style={{ margin: 0 }}>Upcoming Department Exams</h3>
                    </div>
                    
                    {Object.entries(
                        data.active_timetable.reduce((acc, tt) => {
                            const sem = tt.semester;
                            if (!acc[sem]) acc[sem] = [];
                            acc[sem].push(tt);
                            return acc;
                        }, {})
                    )
                    .sort(([a], [b]) => a - b)
                    .map(([sem, semEntries]) => (
                        <div key={sem} style={{ marginBottom: '24px' }}>
                            <div style={{ 
                                fontSize: '0.9rem', 
                                fontWeight: 700, 
                                color: 'var(--color-text-muted)', 
                                marginBottom: '12px',
                                textTransform: 'uppercase',
                                letterSpacing: '0.5px',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px'
                            }}>
                                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--color-primary)' }}></span>
                                Semester {sem}
                            </div>
                            <div className="table-scroll-wrapper" style={{ overflowX: 'auto', marginBottom: '12px' }}>
                                <table className="data-table enhanced-table">
                                    <thead>
                                        <tr>
                                            <th>Subject</th>
                                            <th>Date</th>
                                            <th>Time</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {semEntries.map((tt, i) => (
                                            <tr key={i}>
                                                <td style={{ fontWeight: 600 }}>{tt.subject_name}</td>
                                                <td>{tt.exam_date}</td>
                                                <td>{tt.exam_time}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Subject Performance Bar Chart */}
            <div className="dashboard-card fade-in-up fade-in-delay-1 chart-card-full">
                <h3>Subject Performance</h3>
                {chartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height={320}>
                        <BarChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 5 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                            <XAxis dataKey="name" stroke="var(--color-text-muted)" fontSize={11} />
                            <YAxis stroke="var(--color-text-muted)" fontSize={11} />
                            <Tooltip contentStyle={{ background: 'var(--color-bg-card)', border: '1px solid var(--color-border)', borderRadius: '8px' }} />
                            <Bar dataKey="Avg %" radius={[6, 6, 0, 0]}>
                                {chartData.map((_, i) => (
                                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                ) : (
                    <p className="text-muted" style={{ textAlign: 'center', padding: '40px' }}>No marks data available yet. Upload marks to see analytics.</p>
                )}
            </div>

            {/* Subject Stats Table */}
            {(data?.subject_stats || []).length > 0 && (
                <div className="data-table-container fade-in-up fade-in-delay-2">
                    <div className="data-table-header">
                        <h3>Subject Details</h3>
                    </div>
                    <div className="table-scroll-wrapper">
                        <table className="data-table enhanced-table">
                            <thead>
                                <tr>
                                    <th>Subject</th>
                                    <th>Students</th>
                                    <th>Avg Marks %</th>
                                    <th>Performance</th>
                                </tr>
                            </thead>
                            <tbody>
                                {data.subject_stats.map((s, i) => (
                                    <tr key={i} className={i % 2 === 0 ? 'row-even' : 'row-odd'}>
                                        <td style={{ fontWeight: 600 }}>{s.subject_name}</td>
                                        <td>{s.student_count}</td>
                                        <td>{s.average_marks}%</td>
                                        <td>
                                            <div className="progress-bar-wrapper">
                                                <div className="progress-bar-fill" style={{
                                                    width: `${Math.min(s.average_marks, 100)}%`,
                                                    background: s.average_marks >= 60 ? 'var(--color-success)' : s.average_marks >= 40 ? 'var(--color-warning)' : 'var(--color-error)',
                                                }} />
                                            </div>
                                        </td>
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
