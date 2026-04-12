import { useState, useEffect } from 'react';
import { useAuth } from '../../../context/AuthContext';
import api from '../../../utils/api';
import { FiUsers, FiBookOpen, FiAward, FiLayers } from 'react-icons/fi';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

/* â”€â”€ SVG Gauge Component â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
function Gauge({ value, max = 100, label, color = '#00bcd4' }) {
    const pct = Math.min((value / max) * 100, 100);
    const radius = 70;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (pct / 100) * circumference;

    return (
        <div className="gauge-container">
            <svg width="160" height="160" viewBox="0 0 160 160">
                <circle cx="80" cy="80" r={radius} fill="none" stroke="var(--color-border)" strokeWidth="12" />
                <circle
                    cx="80" cy="80" r={radius} fill="none"
                    stroke={color} strokeWidth="12"
                    strokeDasharray={circumference} strokeDashoffset={offset}
                    strokeLinecap="round"
                    transform="rotate(-90 80 80)"
                    style={{ transition: 'stroke-dashoffset 1s ease' }}
                />
                <text x="80" y="75" textAnchor="middle" fill="var(--color-text-primary)"
                    fontFamily="var(--font-heading)" fontSize="24" fontWeight="700">
                    {pct.toFixed(1)}%
                </text>
                <text x="80" y="100" textAnchor="middle" fill="var(--color-text-muted)"
                    fontFamily="var(--font-body)" fontSize="11">
                    {label}
                </text>
            </svg>
        </div>
    );
}

const COLORS = ['#00bcd4', '#a87ef0', '#ffb703', '#22c55e', '#ef4444', '#f59e0b', '#667eea'];

export default function PrincipalDashboard() {
    const { user } = useAuth();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        (async () => {
            try {
                const res = await api.get('/college/principal/overview');
                setData(res.data);
            } catch (err) {
                console.error('Failed to load principal overview', err);
            } finally {
                setLoading(false);
            }
        })();
    }, []);

    if (loading) return <div className="spinner" style={{ margin: '40px auto' }}></div>;

    const chartData = (data?.departments || []).map(d => ({
        name: d.department,
        Students: d.student_count,
        Faculty: d.faculty_count,
        'Avg %': d.average_marks,
    }));

    return (
        <div className="dashboard-content dashboard-home">
            <div className="page-header slide-in-left">
                <h1 className="gradient-text">College Overview</h1>
                <p>Welcome back, Principal <strong>{user.name}</strong></p>
            </div>

            <div className="stats-grid fade-in-up">
                <div className="stat-card">
                    <div className="stat-card-header">
                        <span className="stat-card-label">Departments</span>
                        <div className="stat-card-icon" style={{ background: 'var(--gradient-primary)' }}><FiLayers /></div>
                    </div>
                    <div className="stat-card-value">{data?.total_departments || 0}</div>
                </div>
                <div className="stat-card">
                    <div className="stat-card-header">
                        <span className="stat-card-label">HODs</span>
                        <div className="stat-card-icon" style={{ background: 'var(--gradient-secondary)' }}><FiAward /></div>
                    </div>
                    <div className="stat-card-value">{data?.total_hods || 0}</div>
                </div>
                <div className="stat-card">
                    <div className="stat-card-header">
                        <span className="stat-card-label">Faculty</span>
                        <div className="stat-card-icon" style={{ background: 'var(--color-success)' }}><FiBookOpen /></div>
                    </div>
                    <div className="stat-card-value">{data?.total_faculty || 0}</div>
                </div>
                <div className="stat-card">
                    <div className="stat-card-header">
                        <span className="stat-card-label">Students</span>
                        <div className="stat-card-icon" style={{ background: 'var(--color-warning)' }}><FiUsers /></div>
                    </div>
                    <div className="stat-card-value">{data?.total_students || 0}</div>
                </div>
            </div>

            {/* Performance Gauge + Chart Row */}
            <div className="dashboard-row fade-in-up fade-in-delay-1">
                <div className="dashboard-card gauge-card">
                    <h3>Overall Performance</h3>
                    <Gauge value={data?.overall_performance || 0} label="College Average" color="#00bcd4" />
                </div>

                <div className="dashboard-card chart-card">
                    <h3>Department Distribution</h3>
                    {chartData.length > 0 ? (
                        <ResponsiveContainer width="100%" height={280}>
                            <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                                <XAxis dataKey="name" stroke="var(--color-text-muted)" fontSize={11} />
                                <YAxis stroke="var(--color-text-muted)" fontSize={11} />
                                <Tooltip
                                    contentStyle={{
                                        background: 'var(--color-bg-card)',
                                        border: '1px solid var(--color-border)',
                                        borderRadius: '8px',
                                        fontSize: '0.85rem',
                                    }}
                                />
                                <Bar dataKey="Students" radius={[4, 4, 0, 0]}>
                                    {chartData.map((_, i) => (
                                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                                    ))}
                                </Bar>
                                <Bar dataKey="Faculty" fill="#a87ef0" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    ) : (
                        <p className="text-muted" style={{ textAlign: 'center', padding: '40px' }}>
                            No department data available yet
                        </p>
                    )}
                </div>
            </div>

            {/* Department Details Table */}
            {(data?.departments || []).length > 0 && (
                <div className="data-table-container fade-in-up fade-in-delay-2">
                    <div className="data-table-header">
                        <h3>Department Summary</h3>
                    </div>
                    <div className="table-scroll-wrapper">
                        <table className="data-table enhanced-table">
                            <thead>
                                <tr>
                                    <th>Department</th>
                                    <th>Students</th>
                                    <th>Faculty</th>
                                    <th>Average %</th>
                                    <th>Performance</th>
                                </tr>
                            </thead>
                            <tbody>
                                {data.departments.map((d, i) => (
                                    <tr key={i} className={i % 2 === 0 ? 'row-even' : 'row-odd'}>
                                        <td style={{ fontWeight: 600 }}>{d.department}</td>
                                        <td>{d.student_count}</td>
                                        <td>{d.faculty_count}</td>
                                        <td>{d.average_marks}%</td>
                                        <td>
                                            <div className="progress-bar-wrapper">
                                                <div
                                                    className="progress-bar-fill"
                                                    style={{
                                                        width: `${Math.min(d.average_marks, 100)}%`,
                                                        background: d.average_marks >= 60 ? 'var(--color-success)' : d.average_marks >= 40 ? 'var(--color-warning)' : 'var(--color-error)',
                                                    }}
                                                />
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
