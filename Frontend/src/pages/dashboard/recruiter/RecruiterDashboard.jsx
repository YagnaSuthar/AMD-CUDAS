import { useState, useEffect } from 'react';
import { useAuth } from '../../../context/AuthContext';
import api from '../../../utils/api';
import { 
    FiUsers, FiCheckCircle, FiClock, FiBriefcase, FiAward, FiTrendingUp, 
    FiBarChart2, FiActivity, FiUser, FiMail, FiCalendar, FiTarget, FiInfo
} from 'react-icons/fi';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const COLORS = ['#00bcd4', '#a87ef0', '#ffb703', '#22c55e', '#ef4444', '#667eea'];

export default function RecruiterDashboard() {
    const { user } = useAuth();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [reportModal, setReportModal] = useState({ show: false, report: null });

    const fetchReport = async (sessionId) => {
        try {
            const res = await api.get(`/ai/interview/report/${sessionId}`);
            setReportModal({ show: true, report: res.data });
        } catch (e) {
            console.error('Failed to fetch report:', e);
            alert('Failed to load report. The interview may not be completed yet.');
        }
    };

    useEffect(() => {
        fetchDashboardData();
    }, []);

    const fetchDashboardData = async () => {
        try {
            setLoading(true);
            const res = await api.get('/recruiter/dashboard');
            setData(res.data);
        } catch (err) {
            setError('Failed to load dashboard data');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return <div className="spinner" style={{ margin: '40px auto' }}></div>;
    }

    if (error) {
        return (
            <div className="dashboard-content">
                <div className="alert alert-error" style={{ margin: '20px' }}>
                    {error}
                </div>
            </div>
        );
    }

    const stats = data?.statistics || {};
    const recentInterviews = data?.recent_interviews || [];
    const statusBreakdown = data?.status_breakdown || {};

    const getStatusColor = (status) => {
        switch (status) {
            case 'AI_ASSIGNED': return '#ffb703';
            case 'AI_COMPLETED': return '#22c55e';
            case 'ROUND2_INVITED': return '#00bcd4';
            case 'ROUND2_COMPLETED': return '#a87ef0';
            case 'HIRED': return '#10b981';
            default: return '#667eea';
        }
    };

    // Prepare chart data
    const statusChartData = Object.entries(statusBreakdown).map(([status, count]) => ({
        name: status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        value: count,
        color: getStatusColor(status)
    }));

    const scoreDistribution = recentInterviews
        .filter(i => i.final_score !== null)
        .reduce((acc, interview) => {
            const score = interview.final_score;
            let range;
            if (score >= 8) range = '8-10 (Excellent)';
            else if (score >= 6) range = '6-8 (Good)';
            else if (score >= 4) range = '4-6 (Average)';
            else range = '0-4 (Needs Improvement)';
            
            acc[range] = (acc[range] || 0) + 1;
            return acc;
        }, {});

    const scoreChartData = Object.entries(scoreDistribution).map(([range, count]) => ({
        name: range,
        count
    }));

    const getRecommendationColor = (recommendation) => {
        if (!recommendation) return '#667eea';
        if (recommendation.includes('strong_hire')) return '#10b981';
        if (recommendation.includes('hire')) return '#22c55e';
        if (recommendation.includes('maybe')) return '#ffb703';
        return '#ef4444';
    };

    const formatDate = (dateString) => {
        if (!dateString) return 'N/A';
        return new Date(dateString).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    return (
        <div className="dashboard-content dashboard-home">
            <div className="page-header slide-in-left">
                <h1 className="gradient-text">Recruiter Dashboard</h1>
                <p>Welcome back, <strong>{user.name}</strong> | Manage your interview pipelines</p>
            </div>

            {/* Statistics Grid */}
            <div className="stats-grid fade-in-up">
                <div className="stat-card">
                    <div className="stat-card-header">
                        <span className="stat-card-label">Total Assigned</span>
                        <div className="stat-card-icon" style={{ background: 'var(--gradient-primary)' }}>
                            <FiUsers />
                        </div>
                    </div>
                    <div className="stat-card-value">{stats.total_assigned}</div>
                </div>

                <div className="stat-card">
                    <div className="stat-card-header">
                        <span className="stat-card-label">AI Completed</span>
                        <div className="stat-card-icon" style={{ background: 'var(--color-success)' }}>
                            <FiCheckCircle />
                        </div>
                    </div>
                    <div className="stat-card-value">{stats.ai_completed}</div>
                </div>

                <div className="stat-card">
                    <div className="stat-card-header">
                        <span className="stat-card-label">Round 2 Invited</span>
                        <div className="stat-card-icon" style={{ background: 'var(--color-secondary)' }}>
                            <FiCalendar />
                        </div>
                    </div>
                    <div className="stat-card-value">{stats.round2_invited}</div>
                </div>

                <div className="stat-card">
                    <div className="stat-card-header">
                        <span className="stat-card-label">Hired</span>
                        <div className="stat-card-icon" style={{ background: 'var(--color-success)' }}>
                            <FiAward />
                        </div>
                    </div>
                    <div className="stat-card-value">{stats.hired}</div>
                </div>

                <div className="stat-card">
                    <div className="stat-card-header">
                        <span className="stat-card-label">Avg Score</span>
                        <div className="stat-card-icon" style={{ background: 'var(--gradient-secondary)' }}>
                            <FiTrendingUp />
                        </div>
                    </div>
                    <div className="stat-card-value">{stats.average_score}/10</div>
                </div>

                <div className="stat-card">
                    <div className="stat-card-header">
                        <span className="stat-card-label">Completion Rate</span>
                        <div className="stat-card-icon" style={{ background: 'var(--color-warning)' }}>
                            <FiBarChart2 />
                        </div>
                    </div>
                    <div className="stat-card-value">
                        {stats.total_assigned > 0 
                            ? Math.round((stats.completed_interviews / stats.total_assigned) * 100) 
                            : 0}%
                    </div>
                </div>
            </div>

            {/* Charts Row */}
            <div className="dashboard-row fade-in-up fade-in-delay-1">
                {/* Status Breakdown Chart */}
                <div className="dashboard-card chart-card">
                    <h3>Pipeline Status</h3>
                    {statusChartData.length > 0 ? (
                        <ResponsiveContainer width="100%" height={280}>
                            <PieChart>
                                <Pie
                                    data={statusChartData}
                                    cx="50%"
                                    cy="50%"
                                    labelLine={false}
                                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                                    outerRadius={80}
                                    fill="#8884d8"
                                    dataKey="value"
                                >
                                    {statusChartData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.color} />
                                    ))}
                                </Pie>
                                <Tooltip />
                            </PieChart>
                        </ResponsiveContainer>
                    ) : (
                        <p className="text-muted" style={{ textAlign: 'center', padding: '40px' }}>
                            No interview data yet
                        </p>
                    )}
                </div>

                {/* Score Distribution Chart */}
                <div className="dashboard-card chart-card">
                    <h3>Score Distribution</h3>
                    {scoreChartData.length > 0 ? (
                        <ResponsiveContainer width="100%" height={280}>
                            <BarChart data={scoreChartData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                                <XAxis dataKey="name" stroke="var(--color-text-muted)" fontSize={10} />
                                <YAxis stroke="var(--color-text-muted)" fontSize={10} />
                                <Tooltip contentStyle={{ 
                                    background: 'var(--color-bg-card)', 
                                    border: '1px solid var(--color-border)', 
                                    borderRadius: '8px' 
                                }} />
                                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                                    {scoreChartData.map((_, i) => (
                                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    ) : (
                        <p className="text-muted" style={{ textAlign: 'center', padding: '40px' }}>
                            No completed interviews yet
                        </p>
                    )}
                </div>
            </div>

            {/* Recent Interviews Table */}
            <div className="data-table-container fade-in-up fade-in-delay-2">
                <div className="data-table-header">
                    <h3>Recent AI Interviews</h3>
                    <span className="table-count">({recentInterviews.length})</span>
                </div>
                
                {recentInterviews.length === 0 ? (
                    <div className="empty-state">
                        <FiActivity className="empty-state-icon" />
                        <h3>No Interviews Yet</h3>
                        <p>Students will appear here once they complete AI interviews.</p>
                    </div>
                ) : (
                    <div className="table-scroll-wrapper">
                        <table className="data-table enhanced-table">
                            <thead>
                                <tr>
                                    <th>Student</th>
                                    <th>Department</th>
                                    <th>Job Role</th>
                                    <th>AI Score</th>
                                    <th>Communication</th>
                                    <th>Recommendation</th>
                                    <th>Status</th>
                                    <th>Report</th>
                                    <th>Completed</th>
                                </tr>
                            </thead>
                            <tbody>
                                {recentInterviews.map((interview, index) => (
                                    <tr key={interview.session_id} className={index % 2 === 0 ? 'row-even' : 'row-odd'}>
                                        <td>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                <FiUser style={{ color: 'var(--color-text-muted)' }} />
                                                <div>
                                                    <div style={{ fontWeight: 600 }}>{interview.student_name}</div>
                                                    <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                                                        {interview.student_email}
                                                    </div>
                                                </div>
                                            </div>
                                        </td>
                                    <td>
                                        <span className="badge bg-secondary" style={{ fontSize: '0.8rem' }}>
                                            {interview.student_department}
                                        </span>
                                    </td>
                                    <td>{interview.job_role}</td>
                                    <td>
                                        {interview.final_score !== null ? (
                                            <div style={{
                                                display: 'inline-block',
                                                padding: '4px 8px',
                                                borderRadius: '4px',
                                                backgroundColor: interview.final_score >= 8 ? 'var(--color-success)' :
                                                                   interview.final_score >= 5 ? 'var(--color-warning)' : 'var(--color-error)',
                                                color: 'white',
                                                fontWeight: 600,
                                                fontSize: '0.75rem'
                                            }}>
                                                {interview.final_score.toFixed(1)}/10
                                            </div>
                                        ) : (
                                            <span style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>
                                                Pending
                                            </span>
                                        )}
                                    </td>
                                        <td>
                                            {interview.recommendation ? (
                                                <span 
                                                    className="badge"
                                                    style={{ 
                                                        backgroundColor: getRecommendationColor(interview.recommendation),
                                                        color: 'white',
                                                        fontSize: '0.75rem'
                                                    }}
                                                >
                                                    {interview.recommendation.split(':')[0]}
                                                </span>
                                            ) : (
                                                <span style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>
                                                    Pending
                                                </span>
                                            )}
                                        </td>
                                        <td>
                                            <span 
                                                className="badge"
                                                style={{ 
                                                    backgroundColor: getStatusColor(interview.pipeline_status || interview.status),
                                                    color: 'white',
                                                    fontSize: '0.75rem'
                                                }}
                                            >
                                                {(interview.pipeline_status || interview.status).replace(/_/g, ' ')}
                                            </span>
                                        </td>
                                        <td>
                                            {interview.status === 'completed' ? (
                                                <button
                                                    className="btn btn-sm btn-secondary"
                                                    onClick={() => fetchReport(interview.session_id)}
                                                    style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                                                    title="View Full Report"
                                                >
                                                    <FiInfo size={12} /> Report
                                                </button>
                                            ) : (
                                                <span style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>
                                                    -
                                                </span>
                                            )}
                                        </td>
                                        <td>
                                            <div style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
                                                {formatDate(interview.ended_at)}
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Key Insights */}
            {recentInterviews.length > 0 && (
                <div className="dashboard-card fade-in-up fade-in-delay-3">
                    <h3>Key Insights</h3>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '16px' }}>
                        <div style={{ padding: '16px', background: 'var(--color-bg-secondary)', borderRadius: '8px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                                <FiTarget style={{ color: 'var(--color-primary)' }} />
                                <strong>Top Performer</strong>
                            </div>
                            {recentInterviews.filter(i => i.final_score !== null).length > 0 ? (
                                <div>
                                    <div style={{ fontWeight: 600 }}>
                                        {recentInterviews.reduce((best, current) => 
                                            (current.final_score || 0) > (best.final_score || 0) ? current : best
                                        ).student_name}
                                    </div>
                                    <div style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
                                        Score: {Math.max(...recentInterviews.map(i => i.final_score || 0)).toFixed(1)}/10
                                    </div>
                                </div>
                            ) : (
                                <div style={{ color: 'var(--color-text-muted)' }}>No scores available</div>
                            )}
                        </div>

                        <div style={{ padding: '16px', background: 'var(--color-bg-secondary)', borderRadius: '8px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                                <FiBriefcase style={{ color: 'var(--color-secondary)' }} />
                                <strong>Most Common Role</strong>
                            </div>
                            {recentInterviews.length > 0 ? (
                                <div>
                                    <div style={{ fontWeight: 600 }}>
                                        {Object.entries(
                                            recentInterviews.reduce((acc, i) => {
                                                acc[i.job_role] = (acc[i.job_role] || 0) + 1;
                                                return acc;
                                            }, {})
                                        ).sort((a, b) => b[1] - a[1])[0]?.[0] || 'N/A'}
                                    </div>
                                    <div style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
                                        {Object.values(
                                            recentInterviews.reduce((acc, i) => {
                                                acc[i.job_role] = (acc[i.job_role] || 0) + 1;
                                                return acc;
                                            }, {})
                                        ).sort((a, b) => b[1] - a[1])[0]} interviews
                                    </div>
                                </div>
                            ) : (
                                <div style={{ color: 'var(--color-text-muted)' }}>No data available</div>
                            )}
                        </div>

                        <div style={{ padding: '16px', background: 'var(--color-bg-secondary)', borderRadius: '8px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                                <FiTrendingUp style={{ color: 'var(--color-success)' }} />
                                <strong>Success Rate</strong>
                            </div>
                            <div>
                                <div style={{ fontWeight: 600, fontSize: '1.2rem' }}>
                                    {stats.total_assigned > 0 
                                        ? Math.round((stats.hired / stats.total_assigned) * 100) 
                                        : 0}%
                                </div>
                                <div style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
                                    Hired / Total Assigned
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
            {reportModal.show && reportModal.report && (
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.5)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 9999,
                }}>
                    <div style={{
                        backgroundColor: 'var(--color-bg)',
                        borderRadius: '8px',
                        padding: '24px',
                        maxWidth: '600px',
                        width: '90%',
                        maxHeight: '80vh',
                        overflowY: 'auto',
                    }}>
                        <h3 style={{ marginTop: 0, marginBottom: '16px' }}>AI Interview Report</h3>
                        <div style={{ marginBottom: '12px' }}><strong>Final Score:</strong> {reportModal.report.final_score ?? 'N/A'}</div>
                        <div style={{ marginBottom: '12px' }}><strong>Communication Score:</strong> {reportModal.report.communication_score ?? 'N/A'}</div>
                        <div style={{ marginBottom: '12px' }}><strong>Recommendation:</strong> {reportModal.report.recommendation ?? 'N/A'}</div>
                        <div style={{ marginBottom: '12px' }}><strong>Strengths:</strong> {reportModal.report.strengths?.length ? reportModal.report.strengths.join(', ') : 'N/A'}</div>
                        <div style={{ marginBottom: '12px' }}><strong>Weaknesses:</strong> {reportModal.report.weaknesses?.length ? reportModal.report.weaknesses.join(', ') : 'N/A'}</div>
                        <div style={{ marginBottom: '12px' }}><strong>Behavior Summary:</strong> {reportModal.report.behavior_summary ?? 'N/A'}</div>
                        <button
                            className="btn btn-secondary"
                            onClick={() => setReportModal({ show: false, report: null })}
                            style={{ marginTop: '16px' }}
                        >
                            Close
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
