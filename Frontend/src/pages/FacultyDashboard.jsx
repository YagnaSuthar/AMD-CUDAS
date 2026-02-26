import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { FiUsers, FiBookOpen, FiLayers, FiTrendingUp } from 'react-icons/fi';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const COLORS = ['#00bcd4', '#a87ef0', '#ffb703', '#22c55e', '#ef4444', '#667eea'];

export default function FacultyDashboard() {
    const { user } = useAuth();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        (async () => {
            try {
                const res = await api.get('/college/faculty/overview');
                setData(res.data);
            } catch (err) { console.error(err); }
            finally { setLoading(false); }
        })();
    }, []);

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
                <div className="stat-card">
                    <div className="stat-card-header">
                        <span className="stat-card-label">Assigned Semesters</span>
                        <div className="stat-card-icon" style={{ background: 'var(--gradient-primary)' }}><FiLayers /></div>
                    </div>
                    <div className="stat-card-value">{(data?.assigned_semesters || []).join(', ') || '—'}</div>
                </div>
                <div className="stat-card">
                    <div className="stat-card-header">
                        <span className="stat-card-label">Subjects</span>
                        <div className="stat-card-icon" style={{ background: 'var(--gradient-secondary)' }}><FiBookOpen /></div>
                    </div>
                    <div className="stat-card-value">{(data?.assigned_subjects || []).length}</div>
                </div>
                <div className="stat-card">
                    <div className="stat-card-header">
                        <span className="stat-card-label">Total Students</span>
                        <div className="stat-card-icon" style={{ background: 'var(--color-success)' }}><FiUsers /></div>
                    </div>
                    <div className="stat-card-value">{data?.total_students || 0}</div>
                </div>
            </div>

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
