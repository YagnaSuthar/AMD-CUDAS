import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { ROLE_LABELS } from '../utils/roles';
import api from '../utils/api';
import { FiUsers, FiCheckSquare, FiBriefcase, FiAlertTriangle, FiLayers } from 'react-icons/fi';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

// Role-specific dashboard components
import PrincipalDashboard from './PrincipalDashboard';
import HodDashboard from './HodDashboard';
import FacultyDashboard from './FacultyDashboard';
import StudentDashboard from './StudentDashboard';

const COLORS = ['#00bcd4', '#a87ef0', '#ffb703', '#22c55e', '#ef4444', '#667eea'];

export default function Dashboard({ analytics = false, departments = false }) {
    const { user } = useAuth();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        fetchDashboardData();
    }, [user.role, analytics]);

    const fetchDashboardData = async () => {
        try {
            setLoading(true);
            if (user.role === 'CUDAS_ADMIN') {
                const res = await api.get('/admin/analytics');
                setData(res.data);
            }
        } catch (err) {
            setError('Failed to load dashboard data');
        } finally {
            setLoading(false);
        }
    };

    if (loading && user.role === 'CUDAS_ADMIN') {
        return <div className="spinner" style={{ margin: '40px auto' }}></div>;
    }

    // ── Dispatch to role-specific dashboards ──────────────────────────
    if (user.role === 'COLLEGE_PRINCIPAL' && !departments) {
        return <PrincipalDashboard />;
    }

    if (user.role === 'COLLEGE_PRINCIPAL' && departments) {
        return <PrincipalDepartments />;
    }

    if (user.role === 'HOD') {
        return <HodDashboard />;
    }

    if (user.role === 'FACULTY') {
        return <FacultyDashboard />;
    }

    if (user.role === 'STUDENT') {
        return <StudentDashboard />;
    }

    // --- CUDAS ADMIN DASHBOARD ---
    if (user.role === 'CUDAS_ADMIN') {
        const roleChartData = data?.users_by_role
            ? Object.entries(data.users_by_role).map(([role, count]) => ({
                name: ROLE_LABELS[role] || role,
                count,
            }))
            : [];

        return (
            <div className="dashboard-content">
                <div className="page-header slide-in-left">
                    <h1 className="gradient-text">System Analytics Overview</h1>
                    <p>Welcome back, CUDAS administrator.</p>
                </div>

                {error && <div className="alert alert-error" style={{ marginBottom: '24px' }}>{error}</div>}

                <div className="stats-grid fade-in-up">
                    <div className="stat-card">
                        <div className="stat-card-header">
                            <span className="stat-card-label">Total Colleges</span>
                            <div className="stat-card-icon" style={{ background: 'var(--gradient-primary)' }}>
                                <FiBriefcase />
                            </div>
                        </div>
                        <div className="stat-card-value">{data?.total_colleges || 0}</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-card-header">
                            <span className="stat-card-label">Total Companies</span>
                            <div className="stat-card-icon" style={{ background: 'var(--gradient-secondary)' }}>
                                <FiBriefcase />
                            </div>
                        </div>
                        <div className="stat-card-value">{data?.total_companies || 0}</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-card-header">
                            <span className="stat-card-label">Total Users</span>
                            <div className="stat-card-icon" style={{ background: 'var(--color-success)' }}>
                                <FiUsers />
                            </div>
                        </div>
                        <div className="stat-card-value">{data?.total_users || 0}</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-card-header">
                            <span className="stat-card-label">Pending Approvals</span>
                            <div className="stat-card-icon" style={{ background: 'var(--color-warning)' }}>
                                <FiAlertTriangle />
                            </div>
                        </div>
                        <div className="stat-card-value">{data?.pending_approvals || 0}</div>
                    </div>
                </div>

                <div className="dashboard-card fade-in-up fade-in-delay-1 chart-card-full">
                    <h3>Users by Role</h3>
                    {roleChartData.length > 0 ? (
                        <ResponsiveContainer width="100%" height={320}>
                            <BarChart data={roleChartData} margin={{ top: 10, right: 30, left: 0, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                                <XAxis dataKey="name" stroke="var(--color-text-muted)" fontSize={11} />
                                <YAxis stroke="var(--color-text-muted)" fontSize={11} />
                                <Tooltip contentStyle={{
                                    background: 'var(--color-bg-card)',
                                    border: '1px solid var(--color-border)',
                                    borderRadius: '8px',
                                }} />
                                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                                    {roleChartData.map((_, i) => (
                                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    ) : (
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
                            {data?.users_by_role && Object.entries(data.users_by_role).map(([role, count]) => (
                                <div key={role} style={{ padding: '16px', background: 'var(--color-primary)', borderRadius: 'var(--radius-sm)' }}>
                                    <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginBottom: '4px' }}>{ROLE_LABELS[role] || role}</div>
                                    <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{count}</div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        );
    }

    // --- GENERAL USER DASHBOARD (Company Admin, Recruiter) ---
    return (
        <div className="dashboard-content">
            <div className="page-header slide-in-left">
                <h1 className="gradient-text">Welcome, {user.name}</h1>
                <p>Your current role is <strong>{ROLE_LABELS[user.role] || user.role}</strong>.</p>
            </div>

            <div className="stats-grid fade-in-up">
                <div className="stat-card">
                    <div className="stat-card-header">
                        <span className="stat-card-label">Quick Status</span>
                        <div className="stat-card-icon" style={{ background: 'var(--color-success)' }}>
                            <FiCheckSquare />
                        </div>
                    </div>
                    <div className="stat-card-value" style={{ fontSize: '1.5rem', paddingTop: '8px' }}>Active Account</div>
                </div>
            </div>

            <div className="dashboard-card fade-in-up fade-in-delay-1">
                <h3>Role Overview</h3>
                <p style={{ color: 'var(--color-text-secondary)', marginBottom: '16px' }}>
                    As a {ROLE_LABELS[user.role]}, you have specific permissions within the CUDAS platform hierarchy.
                    Use the sidebar to navigate to your allowed functions.
                </p>
                <ul style={{ paddingLeft: '20px', color: 'var(--color-text-muted)', display: 'grid', gap: '8px' }}>
                    {user.role === 'COMPANY_ADMIN' && <li>You can create and manage Recruiters for your company.</li>}
                    {user.role === 'RECRUITER' && <li>You can view student profiles and interview analytics.</li>}
                </ul>
            </div>
        </div>
    );
}

/* ── Principal Departments Sub-Component ──────────────────────────── */
function PrincipalDepartments() {
    const [depts, setDepts] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        (async () => {
            try {
                const res = await api.get('/college/principal/departments');
                setDepts(res.data);
            } catch (err) { console.error(err); }
            finally { setLoading(false); }
        })();
    }, []);

    if (loading) return <div className="spinner" style={{ margin: '40px auto' }}></div>;

    const chartData = depts.map(d => ({
        name: d.department,
        Students: d.student_count,
        Faculty: d.faculty_count,
    }));

    return (
        <div className="dashboard-content">
            <div className="page-header slide-in-left">
                <h1 className="gradient-text">Department Summary</h1>
                <p>Read-only view of all departments under your college</p>
            </div>

            {chartData.length > 0 && (
                <div className="dashboard-card fade-in-up chart-card-full">
                    <h3>Department Comparison</h3>
                    <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                            <XAxis dataKey="name" stroke="var(--color-text-muted)" fontSize={11} />
                            <YAxis stroke="var(--color-text-muted)" fontSize={11} />
                            <Tooltip contentStyle={{ background: 'var(--color-bg-card)', border: '1px solid var(--color-border)', borderRadius: '8px' }} />
                            <Bar dataKey="Students" fill="#00bcd4" radius={[4, 4, 0, 0]} />
                            <Bar dataKey="Faculty" fill="#a87ef0" radius={[4, 4, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            )}

            <div className="data-table-container fade-in-up fade-in-delay-1">
                <div className="data-table-header">
                    <h3>All Departments <span className="table-count">({depts.length})</span></h3>
                </div>
                {depts.length === 0 ? (
                    <div className="empty-state">
                        <FiLayers className="empty-state-icon" />
                        <h3>No Departments</h3>
                        <p>Add HODs with departments to see data here.</p>
                    </div>
                ) : (
                    <div className="table-scroll-wrapper">
                        <table className="data-table enhanced-table">
                            <thead>
                                <tr>
                                    <th>Department</th>
                                    <th>Students</th>
                                    <th>Faculty</th>
                                    <th>Avg %</th>
                                    <th>Performance</th>
                                </tr>
                            </thead>
                            <tbody>
                                {depts.map((d, i) => (
                                    <tr key={i} className={i % 2 === 0 ? 'row-even' : 'row-odd'}>
                                        <td style={{ fontWeight: 600 }}>{d.department}</td>
                                        <td>{d.student_count}</td>
                                        <td>{d.faculty_count}</td>
                                        <td>{d.average_marks}%</td>
                                        <td>
                                            <div className="progress-bar-wrapper">
                                                <div className="progress-bar-fill" style={{
                                                    width: `${Math.min(d.average_marks, 100)}%`,
                                                    background: d.average_marks >= 60 ? 'var(--color-success)' : d.average_marks >= 40 ? 'var(--color-warning)' : 'var(--color-error)',
                                                }} />
                                            </div>
                                        </td>
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
