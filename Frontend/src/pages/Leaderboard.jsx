import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { FiTrendingUp, FiSearch, FiFilter, FiAward, FiBookOpen } from 'react-icons/fi';
import { toast } from 'react-toastify';

export default function Leaderboard() {
    const { user } = useAuth();
    const [leaderboard, setLeaderboard] = useState([]);
    const [departments, setDepartments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filters, setFilters] = useState({ department: '', semester: '' });

    useEffect(() => {
        fetchDepartments();
        fetchLeaderboard();
    }, []);

    useEffect(() => {
        fetchLeaderboard();
    }, [filters.department, filters.semester]);

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
                    <button className="btn btn-secondary" onClick={() => setFilters({ department: '', semester: '' })}>
                        Reset Filters
                    </button>
                </div>
            </div>

            <div className="data-table-container fade-in-up fade-in-delay-1">
                <div className="data-table-header">
                    <h3>Rankings <span className="table-count">({leaderboard.length} Students)</span></h3>
                </div>
                {loading ? (
                    <div className="spinner" style={{ margin: '40px auto' }}></div>
                ) : leaderboard.length === 0 ? (
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
                                    <th>Total Score</th>
                                </tr>
                            </thead>
                            <tbody>
                                {leaderboard.map((item) => (
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
