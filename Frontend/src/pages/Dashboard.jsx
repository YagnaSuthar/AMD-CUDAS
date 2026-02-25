import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { ROLE_LABELS } from '../utils/roles';
import api from '../utils/api';
import { FiUsers, FiCheckSquare, FiBriefcase, FiAlertTriangle } from 'react-icons/fi';

export default function Dashboard({ analytics = false }) {
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
            } else {
                // For other roles, just get basic stats using the users endpoint for now
                const res = await api.get('/college/users');
                setData({ subordinateCount: res.data.length });
            }
        } catch (err) {
            setError('Failed to load dashboard data');
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return <div className="spinner" style={{ margin: '40px auto' }}></div>;
    }

    // --- CUDAS ADMIN DASHBOARD ---
    if (user.role === 'CUDAS_ADMIN') {
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
                                <FiUsers />
                            </div>
                        </div>
                        <div className="stat-card-value">{data?.total_colleges || 0}</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-card-header">
                            <span className="stat-card-label">Approved Colleges</span>
                            <div className="stat-card-icon" style={{ background: 'var(--color-success)' }}>
                                <FiCheckSquare />
                            </div>
                        </div>
                        <div className="stat-card-value">{data?.approved_colleges || 0}</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-card-header">
                            <span className="stat-card-label">Pending Approvals</span>
                            <div className="stat-card-icon" style={{ background: 'var(--color-warning)' }}>
                                <FiAlertTriangle />
                            </div>
                        </div>
                        <div className="stat-card-value">{data?.pending_colleges || 0}</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-card-header">
                            <span className="stat-card-label">Total Users</span>
                            <div className="stat-card-icon" style={{ background: 'var(--gradient-secondary)' }}>
                                <FiUsers />
                            </div>
                        </div>
                        <div className="stat-card-value">{data?.total_users || 0}</div>
                    </div>
                </div>

                <div className="dashboard-card fade-in-up fade-in-delay-1">
                    <h3>Users by Role Breakdown</h3>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
                        {data?.users_by_role && Object.entries(data.users_by_role).map(([role, count]) => (
                            <div key={role} style={{ padding: '16px', background: 'var(--color-primary)', borderRadius: 'var(--radius-sm)' }}>
                                <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginBottom: '4px' }}>{ROLE_LABELS[role] || role}</div>
                                <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{count}</div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    // --- GENERAL USER DASHBOARD ---
    return (
        <div className="dashboard-content">
            <div className="page-header slide-in-left">
                <h1 className="gradient-text">Welcome, {user.name}</h1>
                <p>Your current role is <strong>{ROLE_LABELS[user.role] || user.role}</strong>.</p>
            </div>

            <div className="stats-grid fade-in-up">
                {user.role !== 'STUDENT' && (
                    <div className="stat-card">
                        <div className="stat-card-header">
                            <span className="stat-card-label">Direct Subordinates</span>
                            <div className="stat-card-icon" style={{ background: 'var(--gradient-primary)' }}>
                                <FiUsers />
                            </div>
                        </div>
                        <div className="stat-card-value">{data?.subordinateCount || 0}</div>
                    </div>
                )}

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
                    {user.role === 'COLLEGE_PRINCIPAL' && <li>You can create and manage Head of Departments (HODs).</li>}
                    {user.role === 'HOD' && <li>You can create and manage Faculty members for your department.</li>}
                    {user.role === 'FACULTY' && <li>You can create and manage Student accounts.</li>}
                    {user.role === 'STUDENT' && <li>You can update your profile and interact with the AI Interview Agents.</li>}
                    {user.role === 'COMPANY_ADMIN' && <li>You can create and manage Recruiters for your company.</li>}
                    {user.role === 'RECRUITER' && <li>You can view student profiles and interview analytics.</li>}
                </ul>
            </div>
        </div>
    );
}
