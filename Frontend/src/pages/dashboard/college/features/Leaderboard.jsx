import { useState, useEffect } from 'react';
import { useAuth } from '../../../../context/AuthContext';
import api from '../../../../utils/api';
import { FiTrendingUp, FiSearch, FiFilter, FiAward, FiBookOpen } from 'react-icons/fi';
import { toast } from 'react-toastify';

export default function Leaderboard() {
    const { user } = useAuth();
    const [leaderboard, setLeaderboard] = useState([]);
    const [departments, setDepartments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filters, setFilters] = useState({ department: '', semester: '', performance: '' });

    useEffect(() => {
        fetchDepartments();
        fetchLeaderboard();
    }, []);

    useEffect(() => {
        fetchLeaderboard();
    }, [filters.department, filters.semester]);

    const filteredLeaderboard = leaderboard.filter((item) => {
        const pct = typeof item.average_marks === 'number' ? item.average_marks : parseFloat(item.average_marks || 0);
        if (filters.performance === 'TOP' && pct < 85) return false;
        if (filters.performance === 'WEAK' && pct >= 50) return false;
        return true;
    });

    const fetchDepartments = async () => {
        try {
            const res = await api.get('/college/departments/list');
            setDepartments(res.data);
        } catch (err) {
            console.error('Failed to fetch departments:', err);
        }
    };

    const fetchLeaderboard = async () => {
        try {
            setLoading(true);
            const params = new URLSearchParams();
            if (filters.department) params.append('department', filters.department);
            if (filters.semester) params.append('semester', filters.semester);

            const res = await api.get(`/college/leaderboard?${params.toString()}`);
            setLeaderboard(res.data);
        } catch (err) {
            toast.error('Failed to fetch leaderboard');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="dashboard-content">
            <div className="page-header slide-in-left">
                <h1 className="gradient-text">Student Leaderboard</h1>
                <p>Top performers across the college based on marks and certificates.</p>
            </div>

            <div className="dashboard-card fade-in-up" style={{ marginBottom: '24px' }}>
                <div className="filter-bar" style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', alignItems: 'flex-end' }}>
                    <div className="form-group" style={{ marginBottom: 0, flex: 1, minWidth: '150px' }}>
                        <label style={{ fontSize: '0.8rem' }}><FiFilter /> Department</label>
                        <select
                            className="form-input"
                            value={filters.department}
                            onChange={(e) => setFilters({ ...filters, department: e.target.value })}
                        >
                            <option value="">All Departments</option>
                            {departments.map(d => (
                                <option key={d.id} value={d.name}>{d.name}</option>
                            ))}
                        </select>
                    </div>
                    <div className="form-group" style={{ marginBottom: 0, flex: 1, minWidth: '150px' }}>
                        <label style={{ fontSize: '0.8rem' }}>Semester</label>
                        <input
                            type="number"
                            className="form-input"
                            placeholder="All Semesters"
                            value={filters.semester}
                            onChange={(e) => setFilters({ ...filters, semester: e.target.value })}
                        />
                    </div>
                    <div className="form-group" style={{ marginBottom: 0, flex: 1, minWidth: '170px' }}>
                        <label style={{ fontSize: '0.8rem' }}>Performance</label>
                        <select
                            className="form-input"
                            value={filters.performance}
                            onChange={(e) => setFilters({ ...filters, performance: e.target.value })}
                        >
                            <option value="">All</option>
                            <option value="TOP">Top (â‰¥ 85%)</option>
                            <option value="WEAK">Weak (&lt; 50%)</option>
                        </select>
                    </div>
                    <button className="btn btn-secondary" onClick={() => setFilters({ department: '', semester: '' })}>
                        Reset Filters
                    </button>
                </div>
            </div>

            <div className="data-table-container fade-in-up fade-in-delay-1">
                <div className="data-table-header">
                    <h3>Rankings <span className="table-count">({filteredLeaderboard.length} Students)</span></h3>
                </div>
                {loading ? (
                    <div className="spinner" style={{ margin: '40px auto' }}></div>
                ) : filteredLeaderboard.length === 0 ? (
                    <div className="empty-state">
                        <FiTrendingUp className="empty-state-icon" style={{ opacity: 0.3 }} />
                        <p>No students found for the selected criteria.</p>
                    </div>
                ) : (
                    <div className="table-scroll-wrapper">
                        <table className="data-table enhanced-table">
                            <thead>
                                <tr>
                                    <th>Rank</th>
                                    <th>Student</th>
                                    <th>Dept & Sem</th>
                                    <th>Avg Marks</th>
                                    <th>Cert Points</th>
                                    <th>Badge</th>
                                    <th>Total Score</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredLeaderboard.map((item) => (
                                    <tr key={item.student_id}>
                                        <td>
                                            <span className={`rank-badge rank-${item.rank <= 3 ? item.rank : 'default'}`}>
                                                #{item.rank}
                                            </span>
                                        </td>
                                        <td>
                                            <div className="user-cell">
                                                <div className="user-avatar" style={{ background: item.rank <= 3 ? 'var(--gradient-primary)' : 'var(--color-bg-sidebar)' }}>
                                                    {item.rank <= 3 ? <FiAward /> : item.name.charAt(0)}
                                                </div>
                                                <div className="user-info">
                                                    <span className="user-name">{item.name}</span>
                                                    <span className="user-meta" style={{ fontSize: '0.75rem' }}>{item.email}</span>
                                                </div>
                                            </div>
                                        </td>
                                        <td>
                                            <div style={{ fontSize: '0.9rem', fontWeight: 500 }}>{item.department || 'N/A'}</div>
                                            <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>Semester {item.semester || 'N/A'}</div>
                                        </td>
                                        <td>
                                            <div className="progress-bar-wrapper" style={{ width: '80px' }}>
                                                <div className="progress-bar-fill" style={{ width: `${item.average_marks}%`, background: 'var(--color-success)' }} />
                                            </div>
                                            <span style={{ fontSize: '0.8rem', marginLeft: '4px' }}>{item.average_marks}%</span>
                                        </td>
                                        <td>
                                            <span className="points-badge" style={{ background: 'var(--color-bg-card)', border: '1px solid var(--color-border)', padding: '2px 8px', borderRadius: '12px', fontSize: '0.85rem', fontWeight: 600 }}>
                                                +{item.certificate_points} pts
                                            </span>
                                        </td>
                                        <td>
                                            {item.badge ? (
                                                <span
                                                    style={{
                                                        display: 'inline-flex',
                                                        alignItems: 'center',
                                                        padding: '2px 10px',
                                                        borderRadius: '999px',
                                                        fontSize: '0.8rem',
                                                        fontWeight: 700,
                                                        textTransform: 'capitalize',
                                                        border: '1px solid var(--color-border)',
                                                        background:
                                                            item.badge === 'gold'
                                                                ? 'linear-gradient(135deg, rgba(245, 158, 11, 0.25), rgba(251, 191, 36, 0.15))'
                                                                : item.badge === 'silver'
                                                                    ? 'linear-gradient(135deg, rgba(148, 163, 184, 0.25), rgba(203, 213, 225, 0.15))'
                                                                    : 'linear-gradient(135deg, rgba(217, 119, 6, 0.25), rgba(251, 146, 60, 0.15))',
                                                        color:
                                                            item.badge === 'gold'
                                                                ? '#fbbf24'
                                                                : item.badge === 'silver'
                                                                    ? '#cbd5e1'
                                                                    : '#fb923c',
                                                    }}
                                                >
                                                    {item.badge}
                                                </span>
                                            ) : (
                                                <span style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>â€”</span>
                                            )}
                                        </td>
                                        <td>
                                            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--color-secondary)' }}>
                                                {item.total_score}
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
