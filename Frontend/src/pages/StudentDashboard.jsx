import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { FiAward, FiTrendingUp, FiHash, FiBarChart2, FiMic } from 'react-icons/fi';
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid, Cell } from 'recharts';
import InterviewModal from '../components/InterviewModal';
import '../style/interview.css';

/* ── SVG Gauge ─────────────────────────────────────────────────────── */
function Gauge({ value, max = 10, label, color = '#00bcd4', unit = '' }) {
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
                    style={{ transition: 'stroke-dashoffset 1s ease' }} />
                <text x="80" y="75" textAnchor="middle" fill="var(--color-text-primary)"
                    fontFamily="var(--font-heading)" fontSize="24" fontWeight="700">
                    {value}{unit}
                </text>
                <text x="80" y="100" textAnchor="middle" fill="var(--color-text-muted)"
                    fontFamily="var(--font-body)" fontSize="11">{label}</text>
            </svg>
        </div>
    );
}

const COLORS = ['#00bcd4', '#a87ef0', '#ffb703', '#22c55e', '#ef4444', '#667eea', '#f093fb'];

export default function StudentDashboard() {
    const { user } = useAuth();
    const [data, setData] = useState(null);
    const [timetable, setTimetable] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showInterview, setShowInterview] = useState(false);

    useEffect(() => {
        (async () => {
            try {
                const [acaRes, ttRes] = await Promise.all([
                    api.get('/college/student/academic'),
                    api.get('/college/student/timetable'),
                ]);
                setData(acaRes.data);
                setTimetable(ttRes.data);
            } catch (err) { console.error(err); }
            finally { setLoading(false); }
        })();
    }, []);

    if (loading) return <div className="spinner" style={{ margin: '40px auto' }}></div>;

    // Radar data for subject performance
    const radarData = (data?.marks || []).map(m => ({
        subject: m.subject_name.length > 10 ? m.subject_name.slice(0, 10) + '…' : m.subject_name,
        percentage: m.percentage,
        fullMark: 100,
    }));

    // Bar chart data
    const barData = (data?.marks || []).map(m => ({
        name: m.subject_name.length > 10 ? m.subject_name.slice(0, 10) + '…' : m.subject_name,
        Marks: m.marks_obtained,
        Max: m.max_marks,
    }));

    // Countdown to next exam
    const now = new Date();
    const upcomingExams = timetable
        .map(e => ({ ...e, dateObj: new Date(e.exam_date) }))
        .filter(e => e.dateObj >= now)
        .sort((a, b) => a.dateObj - b.dateObj);
    const nextExam = upcomingExams[0];
    let countdown = null;
    if (nextExam) {
        const diff = nextExam.dateObj - now;
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        countdown = { days, hours, subject: nextExam.subject_name, date: nextExam.exam_date };
    }

    return (
        <div className="dashboard-content">
            <div className="page-header slide-in-left">
                <h1 className="gradient-text">Academic Overview</h1>
                <p>Welcome, <strong>{user.name}</strong> | {user.department || 'N/A'}</p>
            </div>

            {/* Technical Skills Section */}
            {user.skills && user.skills.length > 0 && (
                <div className="dashboard-card fade-in-up" style={{ marginBottom: '20px', padding: '15px' }}>
                    <h4 style={{ marginBottom: '10px', fontSize: '0.9rem', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '1px' }}>Technical Skills</h4>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                        {user.skills.map((skill, idx) => (
                            <span key={idx} className="badge bg-secondary" style={{ padding: '6px 12px', borderRadius: '50px' }}>
                                {skill}
                            </span>
                        ))}
                    </div>
                </div>
            )}

            <div className="stats-grid fade-in-up">
                <div className="stat-card">
                    <div className="stat-card-header">
                        <span className="stat-card-label">GPA</span>
                        <div className="stat-card-icon" style={{ background: 'var(--gradient-primary)' }}><FiAward /></div>
                    </div>
                    <div className="stat-card-value">{data?.gpa || 0}</div>
                </div>
                <div className="stat-card">
                    <div className="stat-card-header">
                        <span className="stat-card-label">Overall %</span>
                        <div className="stat-card-icon" style={{ background: 'var(--gradient-secondary)' }}><FiTrendingUp /></div>
                    </div>
                    <div className="stat-card-value">{data?.percentage || 0}%</div>
                </div>
                <div className="stat-card">
                    <div className="stat-card-header">
                        <span className="stat-card-label">Class Rank</span>
                        <div className="stat-card-icon" style={{ background: 'var(--color-warning)' }}><FiHash /></div>
                    </div>
                    <div className="stat-card-value">#{data?.rank || 1} <span style={{ fontSize: '0.9rem', color: 'var(--color-text-muted)' }}>/ {data?.total_in_class || 1}</span></div>
                </div>
                <div className="stat-card">
                    <div className="stat-card-header">
                        <span className="stat-card-label">Subjects</span>
                        <div className="stat-card-icon" style={{ background: 'var(--color-success)' }}><FiBarChart2 /></div>
                    </div>
                    <div className="stat-card-value">{(data?.marks || []).length}</div>
                </div>
            </div>

            {/* Exam Countdown */}
            {countdown && (
                <div className="countdown-card fade-in-up fade-in-delay-1">
                    <div className="countdown-label">Next Exam</div>
                    <div className="countdown-subject">{countdown.subject}</div>
                    <div className="countdown-timer">
                        <div className="countdown-unit">
                            <span className="countdown-number">{countdown.days}</span>
                            <span className="countdown-text">Days</span>
                        </div>
                        <div className="countdown-separator">:</div>
                        <div className="countdown-unit">
                            <span className="countdown-number">{countdown.hours}</span>
                            <span className="countdown-text">Hours</span>
                        </div>
                    </div>
                    <div className="countdown-date">{countdown.date}</div>
                </div>
            )}

            {/* GPA Gauge + Radar Chart */}
            <div className="dashboard-row fade-in-up fade-in-delay-1">
                <div className="dashboard-card gauge-card">
                    <h3>GPA Gauge</h3>
                    <Gauge value={data?.gpa || 0} max={10} label="CGPA / 10" color="#a87ef0" />
                </div>

                <div className="dashboard-card chart-card">
                    <h3>Subject Performance</h3>
                    {radarData.length > 0 ? (
                        <ResponsiveContainer width="100%" height={280}>
                            <RadarChart data={radarData}>
                                <PolarGrid stroke="var(--color-border)" />
                                <PolarAngleAxis dataKey="subject" stroke="var(--color-text-muted)" fontSize={10} />
                                <PolarRadiusAxis angle={30} domain={[0, 100]} stroke="var(--color-text-muted)" fontSize={10} />
                                <Radar name="Score %" dataKey="percentage" stroke="#00bcd4"
                                    fill="#00bcd4" fillOpacity={0.25} strokeWidth={2} />
                                <Tooltip contentStyle={{ background: 'var(--color-bg-card)', border: '1px solid var(--color-border)', borderRadius: '8px' }} />
                            </RadarChart>
                        </ResponsiveContainer>
                    ) : (
                        <p className="text-muted" style={{ textAlign: 'center', padding: '40px' }}>No marks data yet</p>
                    )}
                </div>
            </div>

            {/* Marks Bar Chart */}
            {barData.length > 0 && (
                <div className="dashboard-card fade-in-up fade-in-delay-2 chart-card-full">
                    <h3>Marks Breakdown</h3>
                    <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={barData} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                            <XAxis dataKey="name" stroke="var(--color-text-muted)" fontSize={11} />
                            <YAxis stroke="var(--color-text-muted)" fontSize={11} />
                            <Tooltip contentStyle={{ background: 'var(--color-bg-card)', border: '1px solid var(--color-border)', borderRadius: '8px' }} />
                            <Bar dataKey="Marks" radius={[6, 6, 0, 0]}>
                                {barData.map((_, i) => (
                                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            )}

            {/* Marks Table */}
            {(data?.marks || []).length > 0 && (
                <div className="data-table-container fade-in-up fade-in-delay-3">
                    <div className="data-table-header">
                        <h3>Semester Marks</h3>
                    </div>
                    <div className="table-scroll-wrapper">
                        <table className="data-table enhanced-table">
                            <thead>
                                <tr><th>Subject</th><th>Semester</th><th>Marks</th><th>Max</th><th>%</th></tr>
                            </thead>
                            <tbody>
                                {data.marks.map((m, i) => (
                                    <tr key={i} className={i % 2 === 0 ? 'row-even' : 'row-odd'}>
                                        <td style={{ fontWeight: 600 }}>{m.subject_name}</td>
                                        <td>{m.semester}</td>
                                        <td>{m.marks_obtained}</td>
                                        <td>{m.max_marks}</td>
                                        <td>
                                            <span style={{ color: m.percentage >= 60 ? 'var(--color-success)' : m.percentage >= 40 ? 'var(--color-warning)' : 'var(--color-error)', fontWeight: 700 }}>
                                                {m.percentage}%
                                            </span>
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
