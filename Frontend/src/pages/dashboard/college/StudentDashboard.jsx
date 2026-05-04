import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import api from '../../../utils/api';
import { FiAward, FiTrendingUp, FiHash, FiBarChart2, FiMic, FiBriefcase, FiClock, FiCheckCircle, FiXCircle, FiInfo } from 'react-icons/fi';
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid, Cell } from 'recharts';
import { useNavigate } from 'react-router-dom';
import '../../../style/interview.css';
import SkeletonCard from '../../../components/common/skeleton/SkeletonCard';
import SkeletonText from '../../../components/common/skeleton/SkeletonText';

/* â”€â”€ SVG Gauge â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
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
    const [pipelines, setPipelines] = useState([]);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    const normalizeSkill = (s) => (s || '').toString().trim();

    const classifySkills = (skills) => {
        const buckets = {
            Frontend: [],
            Backend: [],
            'AI/ML': [],
            Tools: [],
            Other: [],
        };

        const patterns = [
            {
                category: 'Frontend',
                test: /(react|next\.js|vue|angular|svelte|html|css|sass|tailwind|bootstrap|javascript|typescript|redux|ui|frontend)/i,
            },
            {
                category: 'Backend',
                test: /(node|express|nestjs|django|flask|fastapi|spring|java|dotnet|c#|php|laravel|api|backend|postgres|mysql|mongodb|redis|sql)/i,
            },
            {
                category: 'AI/ML',
                test: /(ml|ai|tensorflow|pytorch|keras|sklearn|scikit|nlp|llm|opencv|data science|pandas|numpy|matplotlib)/i,
            },
            {
                category: 'Tools',
                test: /(git|github|docker|kubernetes|linux|postman|jira|figma|vscode|ci\/cd|aws|azure|gcp|firebase|vercel|netlify)/i,
            },
        ];

        (skills || [])
            .map(normalizeSkill)
            .filter(Boolean)
            .forEach((skill) => {
                const match = patterns.find((p) => p.test.test(skill));
                const category = match ? match.category : 'Other';
                buckets[category].push(skill);
            });

        Object.keys(buckets).forEach((k) => {
            buckets[k] = Array.from(new Set(buckets[k])).sort((a, b) => a.localeCompare(b));
        });

        return buckets;
    };

    const isHighlightedSkill = (skill) => {
        const s = (skill || '').toLowerCase();
        return [
            'react',
            'javascript',
            'typescript',
            'node',
            'python',
            'fastapi',
            'django',
            'sql',
            'machine learning',
            'tensorflow',
            'pytorch',
            'git',
            'docker',
        ].some((k) => s === k || s.includes(k));
    };

    const fetchPipelines = useCallback(async () => {
        const pipelineRes = await api.get('/pipeline/student');
        setPipelines(pipelineRes.data || []);
    }, []);

    useEffect(() => {
        (async () => {
            try {
                console.log('ðŸ”„ Fetching student dashboard data...');
                
                // Try each API call separately to isolate the issue
                try {
                    const acaRes = await api.get('/college/student/academic');
                    console.log('âœ… Academic API success:', acaRes.data);
                    setData(acaRes.data);
                } catch (acaErr) {
                    console.error('âŒ Academic API failed:', acaErr);
                    if (acaErr.response) {
                        console.error('Status:', acaErr.response.status);
                        console.error('Error data:', acaErr.response.data);
                    }
                    setData(null); // Explicitly set to null on error
                }
                
                try {
                    const ttRes = await api.get('/college/student/timetable');
                    console.log('âœ… Timetable API success:', ttRes.data);
                    setTimetable(ttRes.data);
                } catch (ttErr) {
                    console.error('âŒ Timetable API failed:', ttErr);
                    if (ttErr.response) {
                        console.error('Status:', ttErr.response.status);
                        console.error('Error data:', ttErr.response.data);
                    }
                }
                
                try {
                    const pipelineRes = await api.get('/pipeline/student');
                    console.log('âœ… Pipeline API success:', pipelineRes.data);
                    setPipelines(pipelineRes.data || []);
                } catch (pipelineErr) {
                    console.error('âŒ Pipeline API failed:', pipelineErr);
                    if (pipelineErr.response) {
                        console.error('Status:', pipelineErr.response.status);
                        console.error('Error data:', pipelineErr.response.data);
                    }
                    setPipelines([]);
                }
                
            } catch (err) { 
                console.error('âŒ General error in dashboard data fetch:', err);
                setData(null);
            }
            finally { 
                setLoading(false); 
            }
        })();
    }, []);

    if (loading) {
        return (
            <div className="dashboard-content dashboard-home">
                <div className="page-header">
                    <SkeletonText variant="title" style={{ width: '300px', marginBottom: '8px' }} />
                    <SkeletonText variant="subtitle" style={{ width: '200px' }} />
                </div>
                
                <div className="dashboard-row" style={{ marginBottom: '20px' }}>
                    <SkeletonCard style={{ flex: 1, minHeight: '200px' }} />
                    <SkeletonCard style={{ flex: 1, minHeight: '200px' }} />
                </div>

                <div className="stats-grid">
                    <div className="skeleton-stat-card"><SkeletonText variant="subtitle" style={{marginBottom: '16px'}}/><SkeletonText style={{ height: '36px', width: '60px' }} /></div>
                    <div className="skeleton-stat-card"><SkeletonText variant="subtitle" style={{marginBottom: '16px'}}/><SkeletonText style={{ height: '36px', width: '60px' }} /></div>
                    <div className="skeleton-stat-card"><SkeletonText variant="subtitle" style={{marginBottom: '16px'}}/><SkeletonText style={{ height: '36px', width: '60px' }} /></div>
                    <div className="skeleton-stat-card"><SkeletonText variant="subtitle" style={{marginBottom: '16px'}}/><SkeletonText style={{ height: '36px', width: '60px' }} /></div>
                </div>

                <div className="dashboard-row" style={{ marginTop: '20px' }}>
                    <SkeletonCard style={{ flex: 1, minHeight: '280px' }} />
                    <SkeletonCard style={{ flex: 1, minHeight: '280px' }} />
                </div>
            </div>
        );
    }

    // Radar data for subject performance
    const radarData = (data?.marks || []).map(m => ({
        subject: m.subject_name.length > 10 ? m.subject_name.slice(0, 10) + 'â€¦' : m.subject_name,
        percentage: m.percentage,
        fullMark: 100,
    }));

    // Bar chart data
    const barData = (data?.marks || []).map(m => ({
        name: m.subject_name.length > 10 ? m.subject_name.slice(0, 10) + 'â€¦' : m.subject_name,
        Marks: m.marks_obtained,
        Max: m.max_marks,
    }));

    // Debug: Log current data state
    console.log('ðŸŽ¯ Current data state:', data);
    console.log('ðŸ“ˆ GPA:', data?.gpa);
    console.log('ðŸ“Š Marks count:', data?.marks?.length);
    console.log('ðŸŽ¨ Radar data length:', radarData.length);
    console.log('ðŸ“Š Bar data length:', barData.length);

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
        <div className="dashboard-content dashboard-home">
            <div className="page-header slide-in-left">
                <h1 className="gradient-text">Academic Overview</h1>
                <p>Welcome, <strong>{user.name}</strong> | {user.department || 'N/A'}</p>
            </div>

            {/* Technical Skills & AI Interview Grid */}
            <div className="dashboard-row fade-in-up" style={{ marginBottom: '20px' }}>
                {/* Technical Skills Section */}
                {user.skills && user.skills.length > 0 && (
                    <div className="dashboard-card skills-card" style={{ flex: 1 }}>
                        <div className="skills-card-header">
                            <div className="skills-card-title">
                                <span className="skills-card-eyebrow">Technical Skills</span>
                                <span className="skills-card-subtitle">Organized overview of your current skill set</span>
                            </div>
                            <button
                                type="button"
                                className="btn btn-secondary btn-sm"
                                onClick={() => navigate('/dashboard/skills')}
                            >
                                Manage
                            </button>
                        </div>

                        <div className="skills-groups">
                            {Object.entries(classifySkills(user.skills))
                                .filter(([, list]) => list.length > 0)
                                .map(([groupName, list]) => (
                                    <div key={groupName} className="skills-group">
                                        <div className="skills-group-header">
                                            <span className="skills-group-title">{groupName}</span>
                                            <span className="skills-group-count">{list.length}</span>
                                        </div>

                                        <div className="skills-chips">
                                            {list.map((skill) => (
                                                <span
                                                    key={`${groupName}:${skill}`}
                                                    className={`skills-chip ${isHighlightedSkill(skill) ? 'skills-chip-highlight' : ''}`}
                                                    title={skill}
                                                >
                                                    <span className="skills-chip-dot" aria-hidden="true" />
                                                    <span className="skills-chip-label">{skill}</span>
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                        </div>
                    </div>
                )}

                {/* AI Interview Section */}
                <div className="dashboard-card" style={{ flex: 1, padding: '15px' }}>
                <h4 style={{ marginBottom: '10px', fontSize: '0.9rem', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '1px' }}>
                    <FiBriefcase style={{ marginRight: '8px' }} />
                    AI Interview Pipeline
                </h4>
                {pipelines.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '20px', color: 'var(--color-text-muted)' }}>
                        <FiMic size={32} style={{ marginBottom: '10px', opacity: 0.5 }} />
                        <p>No AI interviews assigned yet. Check back later for new opportunities!</p>
                        <button 
                            className="btn btn-primary" 
                            onClick={() => navigate('/dashboard/interview', { state: { openRules: true } })}
                            style={{ marginTop: '10px' }}
                        >
                            Practice AI Interview
                        </button>
                    </div>
                ) : (
                    <div style={{ display: 'grid', gap: '12px' }}>
                        {pipelines.map((pipeline) => {
                            const getStatusColor = (status) => {
                                switch (status) {
                                    case 'AI_ASSIGNED': return 'var(--color-secondary)';
                                    case 'AI_COMPLETED': return 'var(--color-success)';
                                    case 'ROUND2_INVITED': return 'var(--color-warning)';
                                    case 'HIRED': return 'var(--color-success)';
                                    default: return 'var(--color-text-muted)';
                                }
                            };
                            
                            const getStatusIcon = (status) => {
                                switch (status) {
                                    case 'AI_ASSIGNED': return <FiClock />;
                                    case 'AI_COMPLETED': return <FiCheckCircle />;
                                    case 'ROUND2_INVITED': return <FiBriefcase />;
                                    case 'HIRED': return <FiAward />;
                                    default: return <FiClock />;
                                }
                            };

                            const formatStatus = (status) => {
                                if (status === 'AI_COMPLETED') return 'Submitted';
                                return status.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, l => l.toUpperCase());
                            };

                            return (
                                <div key={pipeline.id} style={{ 
                                    padding: '15px', 
                                    border: '1px solid var(--color-border)', 
                                    borderRadius: '8px',
                                    backgroundColor: 'var(--color-bg-card)'
                                }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                            {getStatusIcon(pipeline.status)}
                                            <span style={{ 
                                                color: getStatusColor(pipeline.status), 
                                                fontWeight: '600',
                                                fontSize: '0.9rem'
                                            }}>
                                                {formatStatus(pipeline.status)}
                                            </span>
                                        </div>
                                        <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                                            {pipeline.company_name ? `${pipeline.company_name} â€¢ ` : ''}
                                            {pipeline.job_title ? `${pipeline.job_title}` : `Job ID: ${pipeline.job_id?.slice(0, 8)}...`}
                                        </span>
                                    </div>
                                    
                                    {pipeline.status === 'AI_ASSIGNED' && !pipeline.ai_session_id && (
                                        <div style={{ marginTop: '10px' }}>
                                            <p style={{ fontSize: '0.9rem', color: 'var(--color-text-muted)', marginBottom: '10px' }}>
                                                You have been assigned Round 1 (AI interview). Click below to start.
                                            </p>
                                            <button 
                                                className="btn btn-primary btn-sm"
                                                onClick={() => navigate(`/dashboard/interview/live?job_id=${pipeline.job_id}`)}
                                            >
                                                <FiMic style={{ marginRight: '6px' }} />
                                                Start AI Interview
                                            </button>
                                        </div>
                                    )}

                                    {pipeline.status === 'AI_ASSIGNED' && pipeline.ai_session_id && (
                                        <div style={{ marginTop: '10px' }}>
                                            <p style={{ fontSize: '0.9rem', color: 'var(--color-warning)', marginBottom: '10px' }}>
                                                You have already started the AI interview for this job. Please complete it or contact support if you encountered issues.
                                            </p>
                                            <div style={{
                                                display: 'inline-flex',
                                                alignItems: 'center',
                                                gap: '6px',
                                                padding: '6px 12px',
                                                backgroundColor: 'var(--color-bg-secondary)',
                                                borderRadius: '20px',
                                                fontSize: '0.8rem',
                                                color: 'var(--color-text-muted)'
                                            }}>
                                                <FiInfo style={{ color: 'var(--color-warning)' }} />
                                                Interview in progress - No retakes allowed
                                            </div>
                                        </div>
                                    )}
                                    
                                    {pipeline.status === 'AI_COMPLETED' && (
                                        <div style={{ marginTop: '10px' }}>
                                            <p style={{ fontSize: '0.9rem', color: 'var(--color-success)', marginBottom: '5px', fontWeight: '600' }}>
                                                âœ“ Submitted
                                            </p>
                                            <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', marginBottom: '8px' }}>
                                                Your AI interview has been submitted successfully. The recruiter will review it.
                                            </p>
                                            {pipeline.ai_session_id && (
                                                <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                                                    Session ID: {pipeline.ai_session_id.slice(0, 8)}...
                                                </p>
                                            )}
                                            <div style={{ 
                                                display: 'inline-flex', 
                                                alignItems: 'center', 
                                                gap: '6px', 
                                                padding: '6px 12px', 
                                                backgroundColor: 'var(--color-bg-secondary)', 
                                                borderRadius: '20px',
                                                fontSize: '0.8rem',
                                                color: 'var(--color-text-muted)'
                                            }}>
                                                <FiCheckCircle style={{ color: 'var(--color-success)' }} />
                                                Interview completed - No retakes allowed
                                            </div>
                                        </div>
                                    )}
                                    
                                    {pipeline.status === 'ROUND2_INVITED' && pipeline.round2_link && (
                                        <div style={{ marginTop: '10px' }}>
                                            <p style={{ fontSize: '0.9rem', color: 'var(--color-warning)', marginBottom: '10px' }}>
                                                Congratulations! You've been invited to Round 2.
                                            </p>
                                            {pipeline.round2_scheduled_at && (
                                                <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', marginBottom: '10px' }}>
                                                    Scheduled: {new Date(pipeline.round2_scheduled_at).toLocaleString()}
                                                </p>
                                            )}
                                            <Link
                                                to={pipeline.round2_link}
                                                className="btn btn-secondary btn-sm"
                                            >
                                                <FiBriefcase style={{ marginRight: '6px' }} />
                                                Start Round 2
                                            </Link>
                                        </div>
                                    )}
                                    
                                    {pipeline.status === 'HIRED' && (
                                        <div style={{ marginTop: '10px' }}>
                                            <p style={{ fontSize: '0.9rem', color: 'var(--color-success)', fontWeight: '600' }}>
                                                ðŸŽ‰ Congratulations! You've been hired by {pipeline.hired_company_name}!
                                            </p>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
            </div>

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

            {/* Active Exam Timetable */}
            {timetable.length > 0 && (
                <div className="dashboard-card fade-in-up fade-in-delay-1" style={{ marginBottom: '24px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
                        <FiClock style={{ color: 'var(--color-primary)', fontSize: '1.2rem' }} />
                        <h3 style={{ margin: 0 }}>Upcoming Exam Schedule</h3>
                    </div>

                    {Object.entries(
                        timetable.reduce((acc, tt) => {
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
                                fontSize: '0.85rem', 
                                fontWeight: 700, 
                                color: 'var(--color-text-muted)', 
                                marginBottom: '10px',
                                textTransform: 'uppercase',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px'
                            }}>
                                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--color-primary)' }}></span>
                                Semester {sem}
                            </div>
                            <div className="table-scroll-wrapper" style={{ overflowX: 'auto' }}>
                                <table className="data-table enhanced-table">
                                    <thead>
                                        <tr>
                                            <th>Subject</th>
                                            <th>Date</th>
                                            <th>Time</th>
                                            <th>Status</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {semEntries.map((tt, i) => (
                                            <tr key={i}>
                                                <td style={{ fontWeight: 600 }}>{tt.subject_name}</td>
                                                <td>{tt.exam_date}</td>
                                                <td>{tt.exam_time}</td>
                                                <td>
                                                    <span className={`countdown-tag ${new Date(tt.exam_date) < new Date() ? 'passed' : 'upcoming'}`} style={{
                                                        padding: '4px 10px',
                                                        borderRadius: '20px',
                                                        fontSize: '0.75rem',
                                                        fontWeight: '600',
                                                        background: new Date(tt.exam_date) < new Date() ? 'var(--color-error-soft)' : 'var(--color-success-soft)',
                                                        color: new Date(tt.exam_date) < new Date() ? 'var(--color-error)' : 'var(--color-success)'
                                                    }}>
                                                        {new Date(tt.exam_date) < new Date() ? 'Completed' : 'Upcoming'}
                                                    </span>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    ))}
                </div>
            )}

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
