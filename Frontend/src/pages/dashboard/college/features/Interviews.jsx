import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiFileText, FiShield, FiCamera, FiSmartphone, FiMonitor, FiUsers, FiCheck, FiX } from 'react-icons/fi';
import { useAuth } from '../../../../context/AuthContext';
import api from '../../../../utils/api';
import SkeletonText from '../../../../components/common/skeleton/SkeletonText';
import SkeletonTableRow from '../../../../components/common/skeleton/SkeletonTableRow';
import SkeletonCard from '../../../../components/common/skeleton/SkeletonCard';

function clampInt(n, min = 0, max = 10) {
    const x = Number.isFinite(Number(n)) ? Math.round(Number(n)) : 0;
    return Math.max(min, Math.min(max, x));
}

function formatApiError(err, fallback = 'Something went wrong') {
    const data = err?.response?.data;
    const detail = data?.detail ?? data;

    if (typeof detail === 'string' && detail.trim()) return detail;

    // FastAPI validation error shape: { detail: [ { loc: [...], msg: "...", type: "..." } ] }
    if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0];
        if (typeof first === 'string') return first;
        if (first && typeof first === 'object') {
            const loc = Array.isArray(first.loc) ? first.loc.join('.') : '';
            const msg = typeof first.msg === 'string' ? first.msg : '';
            const composed = [loc, msg].filter(Boolean).join(': ');
            if (composed) return composed;
            try {
                return JSON.stringify(first);
            } catch {
                return fallback;
            }
        }
    }

    if (detail && typeof detail === 'object') {
        try {
            return JSON.stringify(detail);
        } catch {
            return fallback;
        }
    }

    if (typeof err?.message === 'string' && err.message.trim()) return err.message;
    return fallback;
}

function safeNumber(v, fallback = 0) {
    const n = Number(v);
    return Number.isFinite(n) ? n : fallback;
}

function verdictMeta(verdict) {
    const v = (verdict || '').toString();
    if (v === 'Strong Hire') return { label: v, color: 'var(--color-success)', bg: 'rgba(46, 204, 113, 0.12)' };
    if (v === 'Consider') return { label: v, color: 'var(--color-warning)', bg: 'rgba(241, 196, 15, 0.14)' };
    if (v === 'Needs Improvement') return { label: v, color: 'var(--color-error)', bg: 'rgba(231, 76, 60, 0.12)' };
    return { label: v || 'N/A', color: 'var(--color-text-muted)', bg: 'rgba(255, 255, 255, 0.06)' };
}

function scoreTone(score) {
    const s = safeNumber(score, 0);
    if (s >= 7) return { color: 'var(--color-success)', bg: 'rgba(46, 204, 113, 0.16)' };
    if (s >= 5) return { color: 'var(--color-warning)', bg: 'rgba(241, 196, 15, 0.18)' };
    return { color: 'var(--color-error)', bg: 'rgba(231, 76, 60, 0.16)' };
}

function ProgressBar({ value, max = 10, tone = 'var(--color-primary)' }) {
    const pct = Math.max(0, Math.min(100, (safeNumber(value, 0) / max) * 100));
    return (
        <div style={{ height: '8px', borderRadius: '999px', background: 'var(--color-bg-alt)', border: '1px solid var(--color-border)', overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${pct}%`, background: tone }} />
        </div>
    );
}

function Chip({ text, tone }) {
    return (
        <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            padding: '6px 10px',
            borderRadius: '999px',
            fontSize: '0.78rem',
            fontWeight: 700,
            background: tone?.bg || 'rgba(255, 255, 255, 0.06)',
            color: tone?.color || 'var(--color-text-secondary)',
            border: '1px solid var(--color-border)'
        }}>
            {String(text)}
        </span>
    );
}

function safeArray(v) {
    return Array.isArray(v) ? v : [];
}

function normalizeEvaluationItem(item) {
    if (!item || typeof item !== 'object') return null;

    const evaluation = item.evaluation && typeof item.evaluation === 'object' ? item.evaluation : item;

    return {
        question: (item.question || item.question_text || '').toString(),
        topic: (item.topic || '').toString(),
        difficulty: (item.difficulty || '').toString(),
        correctness: clampInt(evaluation.correctness),
        concept_depth: clampInt(evaluation.concept_depth),
        communication: clampInt(evaluation.communication),
        confidence: clampInt(evaluation.confidence),
        mistakes: safeArray(evaluation.mistakes).map(String),
        missing_points: safeArray(evaluation.missing_points).map(String),
        misconceptions: safeArray(evaluation.misconceptions).map(String),
        severity: ['low', 'medium', 'high'].includes((evaluation.severity || '').toString().toLowerCase())
            ? evaluation.severity.toString().toLowerCase()
            : 'medium',
        final_feedback: (evaluation.final_feedback || '').toString(),
    };
}

function extractPerQuestionEvaluations(reportData) {
    if (!reportData || typeof reportData !== 'object') return [];
    const candidates = [
        reportData.per_question_evaluations,
        reportData.question_evaluations,
        reportData.evaluations,
        reportData.turns,
        reportData.questions,
        reportData?.recruiter_report?.per_question_evaluations,
        reportData?.recruiter_report?.question_evaluations,
    ];

    const arr = candidates.find(Array.isArray) || [];
    return arr.map(normalizeEvaluationItem).filter(Boolean);
}

function aggregateEvaluationInsights(items) {
    const evals = safeArray(items);
    if (evals.length === 0) {
        return {
            strengths: [],
            weaknesses: [],
            criticalIssues: [],
            severityCounts: { high: 0, medium: 0, low: 0 },
            avgCorrectness: 0,
            consistency: 'unknown',
            decision: 'REVIEW',
            decisionRationale: 'Per-question evaluation details are not available for this report.',
        };
    }

    const severityCounts = { high: 0, medium: 0, low: 0 };
    const correctnessList = [];

    const strengths = [];
    const weaknesses = [];
    const criticalIssues = [];

    for (const it of evals) {
        severityCounts[it.severity] = (severityCounts[it.severity] || 0) + 1;
        correctnessList.push(it.correctness);

        const isStrong = it.correctness >= 7 && it.concept_depth >= 6;
        if (isStrong) {
            const label = it.topic ? `Strong understanding of ${it.topic}` : 'Strong understanding of core concepts';
            if (!strengths.includes(label)) strengths.push(label);
        }

        for (const m of it.mistakes.slice(0, 3)) {
            const msg = it.topic ? `${m} (${it.topic})` : m;
            if (!weaknesses.includes(msg)) weaknesses.push(msg);
        }
        for (const mp of it.missing_points.slice(0, 3)) {
            const msg = it.topic ? `Missing: ${mp} (${it.topic})` : `Missing: ${mp}`;
            if (!weaknesses.includes(msg)) weaknesses.push(msg);
        }
        for (const mc of it.misconceptions.slice(0, 2)) {
            const msg = it.topic ? `${mc} (${it.topic})` : mc;
            if (!criticalIssues.includes(msg)) criticalIssues.push(msg);
        }
    }

    const avgCorrectness = correctnessList.reduce((a, b) => a + b, 0) / Math.max(1, correctnessList.length);
    const minC = Math.min(...correctnessList);
    const maxC = Math.max(...correctnessList);
    const spread = maxC - minC;
    const consistency = spread <= 2 ? 'high' : spread <= 4 ? 'medium' : 'low';

    const high = severityCounts.high || 0;
    const medium = severityCounts.medium || 0;
    const avg = avgCorrectness;

    let decision = 'REVIEW';
    let decisionRationale = '';

    if (high >= 2 || avg < 4) {
        decision = 'REJECT';
        decisionRationale = 'Multiple critical conceptual gaps and/or low average correctness.';
    } else if (high === 1 || (avg >= 4 && avg < 6) || consistency === 'low') {
        decision = 'WEAK_HIRE';
        decisionRationale = 'Some critical gaps or inconsistent performance; consider follow-up round.';
    } else if (avg >= 6.5 && consistency !== 'low' && high === 0 && medium <= Math.ceil(evals.length / 2)) {
        decision = 'SHOULD_HIRE';
        decisionRationale = 'Good correctness with acceptable consistency and no critical misconceptions.';
    } else if (avg >= 8 && consistency === 'high' && high === 0) {
        decision = 'STRONGLY_HIRE';
        decisionRationale = 'Consistently strong answers with high correctness and depth.';
    }

    return {
        strengths: strengths.slice(0, 8),
        weaknesses: weaknesses.slice(0, 10),
        criticalIssues: criticalIssues.slice(0, 10),
        severityCounts,
        avgCorrectness: Math.round(avgCorrectness * 10) / 10,
        consistency,
        decision,
        decisionRationale,
    };
}

export default function Interviews() {
    const navigate = useNavigate();
    const { user } = useAuth();
    const isRecruiter = user?.role === 'RECRUITER';
    const isStudent = user?.role === 'STUDENT';

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const [pipelines, setPipelines] = useState([]);
    const [jobs, setJobs] = useState([]);

    const [jobId, setJobId] = useState('');
    const [studentId, setStudentId] = useState('');

    const [round2PipelineId, setRound2PipelineId] = useState('');
    const [round2Link, setRound2Link] = useState('');

    const [feedbackModal, setFeedbackModal] = useState(false);
    const [selectedPipeline, setSelectedPipeline] = useState(null);
    const [feedbackText, setFeedbackText] = useState('');
    const [profile, setProfile] = useState(null);
    const [profileLoading, setProfileLoading] = useState(false);
    const [showProfile, setShowProfile] = useState(false);

    // Report modal state
    const [reportModal, setReportModal] = useState(false);
    const [reportData, setReportData] = useState(null);
    const [reportLoading, setReportLoading] = useState(false);
    const [pdfLoading, setPdfLoading] = useState(false);

    const [showRulesModal, setShowRulesModal] = useState({ show: false, jobId: null });
    const [rulesAccepted, setRulesAccepted] = useState(false);

    const fetchData = async () => {
        try {
            setError('');
            setLoading(true);

            if (isRecruiter) {
                const [pipeRes, jobsRes] = await Promise.all([
                    api.get('/pipeline/my'),
                    api.get('/jobs/my'),
                ]);
                setPipelines(pipeRes.data || []);
                setJobs(jobsRes.data || []);
            } else if (isStudent) {
                const pipeRes = await api.get('/pipeline/student');
                setPipelines(pipeRes.data || []);
            } else {
                setPipelines([]);
            }
        } catch (err) {
            setError(formatApiError(err, 'Failed to load interviews'));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [user?.role]);

    const onAssignAi = async (e) => {
        e.preventDefault();
        try {
            setError('');
            await api.post('/pipeline/assign-ai', {
                job_id: jobId,
                student_id: studentId,
            });
            setStudentId('');
            await fetchData();
        } catch (err) {
            setError(formatApiError(err, 'Failed to assign AI interview'));
        }
    };

    const onInviteRound2 = async (e) => {
        e.preventDefault();
        try {
            setError('');
            await api.put('/pipeline/invite-round2', {
                pipeline_id: round2PipelineId,
                round2_link: round2Link,
            });
            setRound2PipelineId('');
            setRound2Link('');
            await fetchData();
        } catch (err) {
            setError(formatApiError(err, 'Failed to invite round 2'));
        }
    };

    const onHireReject = async (pipelineId, action, feedback = '') => {
        try {
            setError('');
            if (action === 'hire') {
                await api.put('/pipeline/mark-hired', {
                    pipeline_id: pipelineId,
                    hired_company_name: user.company_name || 'Company',
                });
            } else {
                await api.put('/pipeline/reject', {
                    pipeline_id: pipelineId,
                    feedback: feedback,
                });
            }
            setFeedbackModal(false);
            setSelectedPipeline(null);
            setFeedbackText('');
            await fetchData();
        } catch (err) {
            setError(formatApiError(err, `Failed to ${action} candidate`));
        }
    };

    const openProfile = async (studentId) => {
        setProfileLoading(true);
        setShowProfile(true);
        try {
            const res = await api.get(`/recruiter/student/${studentId}`);
            setProfile(res.data);
        } catch (err) {
            setError(formatApiError(err, 'Failed to load profile'));
        } finally {
            setProfileLoading(false);
        }
    };

    const openReport = async (sessionId) => {
        setReportLoading(true);
        setReportModal(true);
        setReportData(null);
        try {
            const res = await api.get(`/ai/interview/report/${sessionId}/recruiter`);
            setReportData(res.data);
        } catch (err) {
            setError(formatApiError(err, 'Failed to load report'));
            setReportModal(false);
        } finally {
            setReportLoading(false);
        }
    };

    const downloadPDF = async (sessionId) => {
        if (!sessionId || pdfLoading) return;
        try {
            setPdfLoading(true);
            const res = await api.get(`/ai/interview/report/pdf/${sessionId}`, {
                responseType: 'blob'
            });

            const blob = new Blob([res.data], { type: 'application/pdf' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `Interview_Report_${sessionId.substring(0, 8)}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
        } catch (err) {
            console.error("Download failed", err);
            setError("Failed to download PDF report");
        } finally {
            setPdfLoading(false);
        }
    };

    const rows = useMemo(() => {
        const arr = Array.isArray(pipelines) ? [...pipelines] : [];
        arr.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
        return arr;
    }, [pipelines]);

    const perQuestionEvals = useMemo(() => extractPerQuestionEvaluations(reportData), [reportData]);
    const evalInsights = useMemo(() => aggregateEvaluationInsights(perQuestionEvals), [perQuestionEvals]);

    const structuredReport = useMemo(() => {
        if (!reportData || typeof reportData !== 'object') return null;
        const summary = reportData.summary && typeof reportData.summary === 'object' ? reportData.summary : null;
        const hasNewSummary = summary && ('overall_score' in summary || 'verdict' in summary);
        const hasNewLists = Array.isArray(reportData.strengths) || Array.isArray(reportData.weaknesses) || Array.isArray(reportData.questions);
        return hasNewSummary || hasNewLists ? reportData : null;
    }, [reportData]);

    if (loading) {
        return (
            <div className="dashboard-content">
                <div className="page-header slide-in-left">
                    <SkeletonText variant="title" style={{ width: '250px' }} />
                    <SkeletonText variant="subtitle" style={{ width: '400px' }} />
                </div>
                <div className="data-table-container">
                    <div className="table-scroll-wrapper">
                        <table className="data-table enhanced-table">
                            <thead>
                                <tr>
                                    <th>{isRecruiter ? 'Student Name' : 'Job / Role'}</th>
                                    <th>Status</th>
                                    <th>Report</th>
                                    <th>Profile</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {Array.from({ length: 5 }).map((_, i) => (
                                    <SkeletonTableRow key={i} columns={5} />
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="dashboard-content">
            <div className="page-header slide-in-left">
                <h1 className="gradient-text">Interviews</h1>
                <p style={{ color: 'var(--color-text-secondary)' }}>
                    {isRecruiter
                        ? 'Assign AI interviews to students and track their status.'
                        : isStudent
                            ? 'See your assigned interviews and their current status.'
                            : 'Interviews'}
                </p>
            </div>

            {error && (
                <div className="alert alert-error" style={{ marginBottom: '16px' }}>
                    {error}
                </div>
            )}

            {isRecruiter && (
                <div style={{ display: 'grid', gap: '16px', marginBottom: '20px' }}>
                    {/* Pipeline management moved to CLGs and Applications pages */}
                </div>
            )}

            <div className="data-table-container fade-in-up">
                <div className="data-table-header">
                    <h3>
                        Pipeline <span className="table-count">({rows.length})</span>
                    </h3>
                </div>

                {rows.length === 0 ? (
                    <div className="empty-state">
                        <h3>No Interview Pipeline</h3>
                        <p style={{ color: 'var(--color-text-muted)' }}>
                            {isRecruiter ? 'Assign an AI interview to start tracking.' : 'No interviews have been assigned yet.'}
                        </p>
                    </div>
                ) : (
                    <div className="table-scroll-wrapper">
                        <table className="data-table enhanced-table">
                            <thead>
                                <tr>
                                    <th>{isRecruiter ? 'Student Name' : 'Job / Role'}</th>
                                    <th>Status</th>
                                    <th>Report</th>
                                    <th>Profile</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {rows.map((p, idx) => (
                                    <tr key={p.id} className={idx % 2 === 0 ? 'row-even' : 'row-odd'}>
                                        <td style={{ fontWeight: 600 }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                <div
                                                    style={{
                                                        width: '32px',
                                                        height: '32px',
                                                        borderRadius: '50%',
                                                        background: 'var(--gradient-primary)',
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        justifyContent: 'center',
                                                        color: '#fff',
                                                        fontWeight: '700',
                                                        fontSize: '0.8rem',
                                                    }}
                                                >
                                                    {(isRecruiter ? p.student_name : (p.job_title || 'M'))?.charAt(0)?.toUpperCase() || '?'}
                                                </div>
                                                <div>
                                                    <div>{isRecruiter ? (p.student_name || 'Student') : (p.job_title || 'MNC Role')}</div>
                                                    <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                                                        {isRecruiter ? (p.student_email || '') : (p.company_name || '')}
                                                    </div>
                                                </div>
                                            </div>
                                        </td>
                                        <td>
                                            <span style={{
                                                padding: '4px 8px',
                                                borderRadius: '12px',
                                                fontSize: '0.8rem',
                                                fontWeight: '600',
                                                backgroundColor: p.status === 'AI_COMPLETED' ? 'var(--color-success)' : 
                                                                 p.status === 'ROUND2_INVITED' ? 'var(--color-warning)' : 
                                                                 p.status === 'HIRED' ? 'var(--color-success)' : 'var(--color-secondary)',
                                                color: '#fff'
                                            }}>
                                                {p.status.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, l => l.toUpperCase())}
                                            </span>
                                        </td>
                                        <td>
                                            {p.status === 'AI_COMPLETED' && p.ai_session_id ? (
                                                <button 
                                                    className="btn btn-sm btn-secondary" 
                                                    onClick={() => openReport(p.ai_session_id)}
                                                >
                                                    View Report
                                                </button>
                                            ) : (
                                                <span style={{ color: 'var(--color-text-muted)' }}>-</span>
                                            )}
                                        </td>
                                        <td>
                                            <button 
                                                className="btn btn-sm btn-primary"
                                                onClick={() => openProfile(p.student_id)}
                                            >
                                                Profile
                                            </button>
                                        </td>
                                        <td>
                                            {isRecruiter ? (
                                                <div style={{ display: 'flex', gap: '8px' }}>
                                                    <button 
                                                        className="btn btn-sm btn-success"
                                                        onClick={() => onHireReject(p.id, 'hire')}
                                                        title="Hire Candidate"
                                                    >
                                                        <FiCheck size={16} />
                                                    </button>
                                                    <button 
                                                        className="btn btn-sm btn-error"
                                                        onClick={() => {
                                                            setSelectedPipeline(p);
                                                            setFeedbackModal(true);
                                                        }}
                                                        title="Reject Candidate"
                                                    >
                                                        <FiX size={16} />
                                                    </button>
                                                </div>
                                            ) : (
                                                (p.status === 'AI_ASSIGNED') ? (
                                                    <button 
                                                        className="btn btn-sm btn-primary"
                                                        onClick={() => setShowRulesModal({ show: true, jobId: p.job_id })}
                                                    >
                                                        Start AI Interview
                                                    </button>
                                                ) : <span style={{ color: 'var(--color-text-muted)' }}>-</span>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Feedback Modal */}
            {feedbackModal && (
                <div className="modal-overlay" onClick={() => setFeedbackModal(false)}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h4>Rejection Feedback</h4>
                            <button className="modal-close" onClick={() => setFeedbackModal(false)}>
                                Ã—
                            </button>
                        </div>
                        <div className="modal-body">
                            <div className="form-group">
                                <label className="form-label">Why is this candidate not selected?</label>
                                <textarea
                                    className="form-input"
                                    rows={5}
                                    value={feedbackText}
                                    onChange={(e) => setFeedbackText(e.target.value)}
                                    placeholder="Please provide feedback for the student..."
                                    required
                                />
                            </div>
                        </div>
                        <div className="modal-footer">
                            <button className="btn btn-secondary" onClick={() => setFeedbackModal(false)}>Cancel</button>
                            <button 
                                className="btn btn-primary" 
                                onClick={() => onHireReject(selectedPipeline.id, 'reject', feedbackText)}
                                disabled={!feedbackText.trim()}
                            >
                                Send Feedback & Reject
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Profile Modal */}
            {showProfile && profile && (
                <div className="modal-overlay" onClick={() => setShowProfile(false)}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '600px' }}>
                        <div className="modal-header">
                            <h4>Student Profile</h4>
                            <button className="modal-close" onClick={() => setShowProfile(false)}>
                                Ã—
                            </button>
                        </div>
                        <div className="modal-body">
                            {profileLoading ? (
                                <div>Loading profile...</div>
                            ) : (
                                <div style={{ display: 'grid', gap: '1rem' }}>
                                    <div>
                                        <div style={{ fontWeight: 700, marginBottom: '4px' }}>Name</div>
                                        <div style={{ color: 'var(--color-text-muted)' }}>{profile.name}</div>
                                    </div>
                                    <div>
                                        <div style={{ fontWeight: 700, marginBottom: '4px' }}>Email</div>
                                        <div style={{ color: 'var(--color-text-muted)' }}>{profile.email}</div>
                                    </div>
                                    <div>
                                        <div style={{ fontWeight: 700, marginBottom: '4px' }}>Skills</div>
                                        <div style={{ color: 'var(--color-text-muted)' }}>
                                            {Array.isArray(profile.skills) && profile.skills.length ? profile.skills.join(', ') : '-'}
                                        </div>
                                    </div>
                                    <div>
                                        <div style={{ fontWeight: 700, marginBottom: '4px' }}>Resume</div>
                                        <div>
                                            {profile.resume_url ? (
                                                <a href={profile.resume_url} target="_blank" rel="noreferrer" className="btn btn-sm btn-secondary">
                                                    View Resume
                                                </a>
                                            ) : (
                                                <span style={{ color: 'var(--color-text-muted)' }}>-</span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                        <div className="modal-footer">
                            <button className="btn btn-secondary" onClick={() => setShowProfile(false)}>Close</button>
                        </div>
                    </div>
                </div>
            )}

            {/* Recruiter Report Modal */}
            {reportModal && (
                <div className="popup-overlay" onClick={() => setReportModal(false)}>
                    <div className="popup-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '720px' }}>
                        <div className="popup-header">
                            <div className="popup-header-left">
                                <div className="popup-icon-wrap">
                                    <FiFileText size={18} />
                                </div>
                                <div>
                                    <h3>AI Interview Report</h3>
                                    <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginTop: '2px' }}>
                                        Recruiter Assessment Summary
                                    </div>
                                </div>
                            </div>
                            <button className="popup-close" onClick={() => setReportModal(false)} aria-label="Close report">
                                Ã—
                                ×
                            </button>
                        </div>

                        <div className="popup-body report-body">
                            {reportLoading ? (
                                <div style={{ padding: '16px 0' }}>
                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '24px' }}>
                                        <SkeletonCard style={{ height: '80px' }} />
                                        <SkeletonCard style={{ height: '80px' }} />
                                        <SkeletonCard style={{ height: '80px' }} />
                                        <SkeletonCard style={{ height: '80px' }} />
                                    </div>
                                    <SkeletonCard style={{ height: '100px', marginBottom: '16px' }} />
                                    <SkeletonCard style={{ height: '100px' }} />
                                </div>
                            ) : reportData ? (
                                <>
                                    {structuredReport ? (
                                        (() => {
                                            const s = structuredReport.summary && typeof structuredReport.summary === 'object'
                                                ? structuredReport.summary
                                                : {};

                                            const overallScore = safeNumber(s.overall_score, 0);
                                            const verdict = verdictMeta(s.verdict);
                                            const avgCorrectness = safeNumber(s.average_correctness, 0);
                                            const avgDepth = safeNumber(s.average_concept_depth, 0);
                                            const avgCommunication = safeNumber(s.average_communication, 0);
                                            const commSummary = (s.communication_summary || 'Communication summary not available.').toString();

                                            const severity = s.severity_distribution && typeof s.severity_distribution === 'object'
                                                ? s.severity_distribution
                                                : { low: 0, medium: 0, high: 0 };

                                            const topicPerf = Array.isArray(s.topic_performance) ? s.topic_performance : [];
                                            const strengths = Array.isArray(structuredReport.strengths) ? structuredReport.strengths : [];
                                            const weaknesses = Array.isArray(structuredReport.weaknesses) ? structuredReport.weaknesses : [];
                                            const critical = Array.isArray(structuredReport.critical_issues) ? structuredReport.critical_issues : [];
                                            const questions = Array.isArray(structuredReport.questions) ? structuredReport.questions : [];
                                            const plan = Array.isArray(structuredReport.improvement_plan) ? structuredReport.improvement_plan : [];

                                            return (
                                                <>
                                                    {/* Header */}
                                                    <div className="report-section" style={{ marginBottom: '16px' }}>
                                                        <div style={{
                                                            display: 'flex',
                                                            justifyContent: 'space-between',
                                                            gap: '12px',
                                                            alignItems: 'flex-start',
                                                            flexWrap: 'wrap'
                                                        }}>
                                                            <div>
                                                                <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginBottom: '6px' }}>
                                                                    Overall Score
                                                                </div>
                                                                <div style={{ fontSize: '2.0rem', fontWeight: 900, lineHeight: 1.1 }}>
                                                                    {overallScore.toFixed(2)} / 10
                                                                </div>
                                                                <div style={{ marginTop: '8px', color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>
                                                                    {commSummary}
                                                                </div>
                                                            </div>

                                                            <div style={{ textAlign: 'right' }}>
                                                                <button
                                                                    className="btn btn-sm btn-secondary"
                                                                    onClick={() => downloadPDF(reportData.session_id)}
                                                                    disabled={pdfLoading}
                                                                    style={{ marginBottom: '10px', minWidth: '120px' }}
                                                                >
                                                                    {pdfLoading ? 'Downloading...' : 'Download PDF'}
                                                                </button>
                                                                <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginBottom: '6px' }}>
                                                                    Verdict
                                                                </div>
                                                                <div style={{
                                                                    display: 'inline-flex',
                                                                    alignItems: 'center',
                                                                    gap: '8px',
                                                                    padding: '8px 12px',
                                                                    borderRadius: '999px',
                                                                    background: verdict.bg,
                                                                    border: '1px solid var(--color-border)',
                                                                    color: verdict.color,
                                                                    fontWeight: 800
                                                                }}>
                                                                    {verdict.label}
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </div>

                                                    {/* Summary Cards */}
                                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '16px' }}>
                                                        <div className="report-section" style={{ marginBottom: 0, boxShadow: '0 10px 26px rgba(0,0,0,0.18)' }}>
                                                            <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>Correctness</div>
                                                            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'baseline' }}>
                                                                <div style={{ fontSize: '1.4rem', fontWeight: 900 }}>{avgCorrectness.toFixed(2)} / 10</div>
                                                                <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', fontWeight: 800 }}>
                                                                    {Math.round((avgCorrectness / 10) * 100)}%
                                                                </div>
                                                            </div>
                                                            <div style={{ marginTop: 10 }}>
                                                                <ProgressBar value={avgCorrectness} tone={scoreTone(avgCorrectness).color} />
                                                            </div>
                                                        </div>
                                                        <div className="report-section" style={{ marginBottom: 0, boxShadow: '0 10px 26px rgba(0,0,0,0.18)' }}>
                                                            <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>Concept Depth</div>
                                                            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'baseline' }}>
                                                                <div style={{ fontSize: '1.4rem', fontWeight: 900 }}>{avgDepth.toFixed(2)} / 10</div>
                                                                <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', fontWeight: 800 }}>
                                                                    {Math.round((avgDepth / 10) * 100)}%
                                                                </div>
                                                            </div>
                                                            <div style={{ marginTop: 10 }}>
                                                                <ProgressBar value={avgDepth} tone={scoreTone(avgDepth).color} />
                                                            </div>
                                                        </div>
                                                        <div className="report-section" style={{ marginBottom: 0, boxShadow: '0 10px 26px rgba(0,0,0,0.18)' }}>
                                                            <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>Communication</div>
                                                            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'baseline' }}>
                                                                <div style={{ fontSize: '1.4rem', fontWeight: 900 }}>{avgCommunication.toFixed(2)} / 10</div>
                                                                <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', fontWeight: 800 }}>
                                                                    {Math.round((avgCommunication / 10) * 100)}%
                                                                </div>
                                                            </div>
                                                            <div style={{ marginTop: 10 }}>
                                                                <ProgressBar value={avgCommunication} tone={scoreTone(avgCommunication).color} />
                                                            </div>
                                                        </div>
                                                    </div>

                                                    {/* Critical Issues */}
                                                    <div className="report-section" style={{ marginTop: '16px', border: '1px solid rgba(231, 76, 60, 0.35)', background: 'rgba(231, 76, 60, 0.08)' }}>
                                                        <h4 className="report-section-title" style={{ color: 'var(--color-error)' }}>Critical Issues</h4>
                                                        {critical.length > 0 ? (
                                                            <ul className="report-list">
                                                                {critical.map((c, i) => <li key={i}>{c}</li>)}
                                                            </ul>
                                                        ) : (
                                                            <div style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem' }}>
                                                                No critical issues detected.
                                                            </div>
                                                        )}
                                                    </div>

                                                    {/* Topic Performance */}
                                                    <div className="report-section" style={{ marginTop: '16px' }}>
                                                        <h4 className="report-section-title">Topic Performance</h4>
                                                        {topicPerf.length === 0 ? (
                                                            <div style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem' }}>No topic breakdown available.</div>
                                                        ) : (
                                                            <div style={{ display: 'grid', gap: '10px' }}>
                                                                {topicPerf.slice(0, 3).map((tp, i) => {
                                                                    const label = (tp?.topic || 'General').toString();
                                                                    const score = safeNumber(tp?.average_score, 0);
                                                                    const pct = Math.max(0, Math.min(100, (score / 10) * 100));
                                                                    return (
                                                                        <div key={i} style={{ display: 'grid', gap: '6px' }}>
                                                                            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                                                                                <div style={{ fontWeight: 700 }}>{label}</div>
                                                                                <div style={{ color: 'var(--color-text-muted)', fontWeight: 700 }}>{score.toFixed(2)}/10</div>
                                                                            </div>
                                                                            <div style={{ height: '8px', borderRadius: '999px', background: 'var(--color-bg-alt)', border: '1px solid var(--color-border)', overflow: 'hidden' }}>
                                                                                <div style={{ height: '100%', width: `${pct}%`, background: 'var(--gradient-primary)' }} />
                                                                            </div>
                                                                        </div>
                                                                    );
                                                                })}
                                                            </div>
                                                        )}
                                                    </div>

                                                    {/* Severity Distribution */}
                                                    <div className="report-section" style={{ marginTop: '16px' }}>
                                                        <h4 className="report-section-title">Severity Distribution</h4>
                                                        {(() => {
                                                            const low = safeNumber(severity.low, 0);
                                                            const medium = safeNumber(severity.medium, 0);
                                                            const high = safeNumber(severity.high, 0);
                                                            const total = Math.max(1, low + medium + high);

                                                            const rows = [
                                                                { label: 'Low', value: low, tone: { color: 'var(--color-success)' } },
                                                                { label: 'Medium', value: medium, tone: { color: 'var(--color-warning)' } },
                                                                { label: 'High', value: high, tone: { color: 'var(--color-error)' } },
                                                            ];

                                                            return (
                                                                <div style={{ display: 'grid', gap: '10px' }}>
                                                                    {rows.map((r, i) => (
                                                                        <div key={i} style={{ display: 'grid', gap: '6px' }}>
                                                                            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                                                                                <div style={{ fontWeight: 800 }}>{r.label}</div>
                                                                                <div style={{ color: 'var(--color-text-muted)', fontWeight: 800 }}>{r.value}</div>
                                                                            </div>
                                                                            <div style={{ height: '8px', borderRadius: '999px', background: 'var(--color-bg-alt)', border: '1px solid var(--color-border)', overflow: 'hidden' }}>
                                                                                <div style={{ height: '100%', width: `${Math.round((r.value / total) * 100)}%`, background: r.tone.color }} />
                                                                            </div>
                                                                        </div>
                                                                    ))}
                                                                </div>
                                                            );
                                                        })()}
                                                    </div>

                                                    {/* Question-wise Analysis */}
                                                    <div className="report-section" style={{ marginTop: '16px' }}>
                                                        <h4 className="report-section-title">Question-wise Analysis</h4>
                                                        {questions.length === 0 ? (
                                                            <div style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem' }}>No question-wise analysis available.</div>
                                                        ) : (
                                                            <div style={{ display: 'grid', gap: '10px' }}>
                                                                {questions.slice(0, 15).map((q, idx) => {
                                                                    const questionText = (q?.question || '').toString();
                                                                    const answerText = (q?.answer || '').toString();
                                                                    const correctness = safeNumber(q?.correctness, 0);
                                                                    const mistakes = Array.isArray(q?.mistakes) ? q.mistakes : [];
                                                                    const feedback = (q?.feedback || '').toString();
                                                                    const tone = scoreTone(correctness);

                                                                    return (
                                                                        <details key={idx} style={{
                                                                            padding: '10px 12px',
                                                                            borderRadius: '10px',
                                                                            background: 'var(--color-bg-alt)',
                                                                            border: '1px solid var(--color-border)',
                                                                            boxShadow: '0 10px 26px rgba(0,0,0,0.18)'
                                                                        }}>
                                                                            <summary style={{ cursor: 'pointer', fontWeight: 800 }}>
                                                                                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '10px' }}>
                                                                                    <span>Q{idx + 1}</span>
                                                                                    <span style={{
                                                                                        display: 'inline-flex',
                                                                                        alignItems: 'center',
                                                                                        padding: '6px 10px',
                                                                                        borderRadius: '999px',
                                                                                        background: tone.bg,
                                                                                        color: tone.color,
                                                                                        border: '1px solid var(--color-border)',
                                                                                        fontWeight: 900,
                                                                                        fontSize: '0.8rem'
                                                                                    }}>
                                                                                        Correctness {correctness}/10
                                                                                    </span>
                                                                                </span>
                                                                            </summary>
                                                                            <div style={{ marginTop: '10px', fontSize: '0.9rem', lineHeight: 1.6 }}>
                                                                                <div style={{ margin: '0 0 8px 0', fontWeight: 700 }}>
                                                                                    {questionText || 'Question not available.'}
                                                                                </div>
                                                                                <div style={{ color: 'var(--color-text-secondary)', marginBottom: 8, maxHeight: '150px', overflowY: 'auto' }}>
                                                                                    <strong>Answer:</strong>{' '}
                                                                                    {answerText || 'Answer not available.'}
                                                                                </div>
                                                                                {mistakes.length > 0 && (
                                                                                    <div style={{ marginBottom: 10 }}>
                                                                                        <div style={{ fontWeight: 800, marginBottom: 8 }}>Mistakes</div>
                                                                                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                                                                                            {mistakes.slice(0, 8).map((m, i) => (
                                                                                                <Chip key={i} text={m} tone={{ color: 'var(--color-error)', bg: 'rgba(231, 76, 60, 0.10)' }} />
                                                                                            ))}
                                                                                        </div>
                                                                                    </div>
                                                                                )}
                                                                                {feedback && (
                                                                                    <div style={{
                                                                                        marginTop: 10,
                                                                                        padding: '10px 12px',
                                                                                        borderRadius: '10px',
                                                                                        background: 'rgba(255, 255, 255, 0.04)',
                                                                                        border: '1px solid var(--color-border)'
                                                                                    }}>
                                                                                        <div style={{ fontWeight: 900, marginBottom: 6 }}>Feedback</div>
                                                                                        <div style={{ color: 'var(--color-text-secondary)' }}>{feedback}</div>
                                                                                    </div>
                                                                                )}
                                                                                {!feedback && mistakes.length === 0 && (
                                                                                    <div style={{ color: 'var(--color-text-muted)' }}>No additional notes for this question.</div>
                                                                                )}
                                                                            </div>
                                                                        </details>
                                                                    );
                                                                })}
                                                            </div>
                                                        )}
                                                    </div>

                                                    {/* Improvement Plan */}
                                                    <div className="report-section" style={{ marginTop: '16px' }}>
                                                        <h4 className="report-section-title">Improvement Plan</h4>
                                                        {plan.length === 0 ? (
                                                            <div style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem' }}>No improvement plan available.</div>
                                                        ) : (
                                                            <div style={{ display: 'grid', gap: '10px' }}>
                                                                {plan.map((item, i) => (
                                                                    <label key={i} style={{
                                                                        display: 'flex',
                                                                        gap: '10px',
                                                                        alignItems: 'flex-start',
                                                                        padding: '10px 12px',
                                                                        borderRadius: '10px',
                                                                        background: 'var(--color-bg-alt)',
                                                                        border: '1px solid var(--color-border)'
                                                                    }}>
                                                                        <input type="checkbox" readOnly style={{ marginTop: '3px' }} />
                                                                        <span style={{ color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>{String(item)}</span>
                                                                    </label>
                                                                ))}
                                                            </div>
                                                        )}
                                                    </div>
                                                </>
                                            );
                                        })()
                                    ) : (
                                        <>
                                            <div className="report-scores-grid">
                                                <div className="report-score-card">
                                                    <div className="report-score-value">{((reportData.technical_score || 0) * 100).toFixed(0)}%</div>
                                                    <div className="report-score-label">Technical</div>
                                                </div>
                                                <div className="report-score-card">
                                                    <div className="report-score-value">{((reportData.communication_score || 0) * 100).toFixed(0)}%</div>
                                                    <div className="report-score-label">Communication</div>
                                                </div>
                                                <div className="report-score-card">
                                                    <div className="report-score-value">{((reportData.behavior_score || 0) * 100).toFixed(0)}%</div>
                                                    <div className="report-score-label">Behavior</div>
                                                </div>
                                                <div className="report-score-card report-score-final">
                                                    <div className="report-score-value">{((reportData.final_score || 0) * 100).toFixed(0)}%</div>
                                                    <div className="report-score-label">Overall</div>
                                                </div>
                                            </div>

                                            <div style={{ textAlign: 'center', margin: '6px 0 18px' }}>
                                                <span className={`report-recommendation-badge report-rec-${(reportData.recommendation || '').toLowerCase().replace(/ /g, '_')}`}>
                                                    {`Recommendation: ${reportData.recommendation || 'N/A'}`}
                                                </span>
                                            </div>

                                            {reportData.justification && (
                                                <div className="report-section">
                                                    <h4 className="report-section-title">Summary</h4>
                                                    <p style={{ color: 'var(--color-text-secondary)', lineHeight: '1.65', fontSize: '0.9rem', margin: 0 }}>
                                                        {reportData.justification}
                                                    </p>
                                                </div>
                                            )}
                                        </>
                                    )}

                                    {!structuredReport && (
                                        <>
                                            {/* --- STRENGTHS (NEW DATA-DRIVEN) --- */}
                                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '16px' }}>
                                                <div className="report-section" style={{ marginBottom: 0 }}>
                                                    <h4 className="report-section-title" style={{ color: 'var(--color-success)' }}>Strengths</h4>
                                                    <ul className="report-list">
                                                        {(reportData.strengths || []).map((s, i) => <li key={i}>{s}</li>)}
                                                        {(!reportData.strengths || !reportData.strengths.length) && (
                                                            <li style={{ color: 'var(--color-text-muted)' }}>No strong areas identified</li>
                                                        )}
                                                    </ul>
                                                </div>

                                                {/* --- WEAKNESSES (NEW DATA-DRIVEN) --- */}
                                                <div className="report-section" style={{ marginBottom: 0 }}>
                                                    <h4 className="report-section-title" style={{ color: 'var(--color-error)' }}>Areas to improve</h4>
                                                    <ul className="report-list">
                                                        {(reportData.weaknesses || []).map((w, i) => <li key={i}>{w}</li>)}
                                                        {(!reportData.weaknesses || !reportData.weaknesses.length) && (
                                                            <li style={{ color: 'var(--color-text-muted)' }}>No improvement areas listed</li>
                                                        )}
                                                    </ul>
                                                </div>
                                            </div>

                                            {/* --- CRITICAL ISSUES (NEW) --- */}
                                            {(reportData.critical_issues && reportData.critical_issues.length > 0) && (
                                                <div className="report-section" style={{ marginTop: '16px' }}>
                                                    <h4 className="report-section-title" style={{ color: 'var(--color-error)' }}>Critical Issues</h4>
                                                    <ul className="report-list">
                                                        {reportData.critical_issues.map((c, i) => <li key={i}>{c}</li>)}
                                                    </ul>
                                                </div>
                                            )}

                                            {/* --- QUESTION-WISE ANALYSIS (NEW) --- */}
                                            {(reportData.evaluations && reportData.evaluations.length > 0) && (
                                                <div className="report-section" style={{ marginTop: '16px' }}>
                                                    <h4 className="report-section-title">Question-wise Analysis</h4>
                                                    <div style={{ display: 'grid', gap: '10px' }}>
                                                        {reportData.evaluations.slice(0, 15).map((ev, idx) => (
                                                            <details key={idx} style={{
                                                                padding: '10px 12px',
                                                                borderRadius: '10px',
                                                                background: 'var(--color-bg-alt)',
                                                                border: '1px solid var(--color-border)'
                                                            }}>
                                                                <summary style={{ cursor: 'pointer', fontWeight: 700 }}>
                                                                    Q{idx + 1}{ev.topic ? ` • ${ev.topic}` : ''}{ev.severity ? ` • ${ev.severity.toUpperCase()}` : ''}
                                                                </summary>
                                                                <div style={{ marginTop: '10px', fontSize: '0.9rem', lineHeight: 1.6 }}>
                                                                    <p style={{ margin: '0 0 8px 0', fontWeight: 600 }}>{ev.question}</p>
                                                                    {ev.answer && (
                                                                        <p style={{ margin: '0 0 8px 0', color: 'var(--color-text-secondary)', maxHeight: '150px', overflowY: 'auto' }}>
                                                                            <strong>Answer:</strong> {ev.answer}
                                                                        </p>
                                                                    )}
                                                                    <p style={{ margin: '0 0 4px 0' }}><strong>Correctness:</strong> {ev.correctness}/10</p>
                                                                    {ev.mistakes && ev.mistakes.length > 0 && (
                                                                        <p style={{ margin: '0 0 4px 0' }}>
                                                                            <strong>Mistakes:</strong> {ev.mistakes.join('; ')}
                                                                        </p>
                                                                    )}
                                                                    {ev.missing_points && ev.missing_points.length > 0 && (
                                                                        <p style={{ margin: '0 0 4px 0' }}>
                                                                            <strong>Missing points:</strong> {ev.missing_points.join('; ')}
                                                                        </p>
                                                                    )}
                                                                    {ev.final_feedback && (
                                                                        <p style={{ margin: '8px 0 0 0' }}>
                                                                            <strong>Feedback:</strong> {ev.final_feedback}
                                                                        </p>
                                                                    )}
                                                                </div>
                                                            </details>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                        </>
                                    )}

                                    {/* --- LEGACY ASSESSMENTS (OPTIONAL, HIDE IF NEW DATA EXISTS) --- */}
                                    {!structuredReport && (!reportData.evaluations || reportData.evaluations.length === 0) && (
                                        <>
                                            {reportData.technical_assessment && (
                                                <div className="report-section" style={{ marginTop: '16px' }}>
                                                    <h4 className="report-section-title">Technical assessment</h4>
                                                    <p style={{ color: 'var(--color-text-secondary)', lineHeight: '1.65', fontSize: '0.9rem', margin: 0 }}>
                                                        {reportData.technical_assessment}
                                                    </p>
                                                </div>
                                            )}
                                            {reportData.communication_assessment && (
                                                <div className="report-section">
                                                    <h4 className="report-section-title">Communication assessment</h4>
                                                    <p style={{ color: 'var(--color-text-secondary)', lineHeight: '1.65', fontSize: '0.9rem', margin: 0 }}>
                                                        {reportData.communication_assessment}
                                                    </p>
                                                </div>
                                            )}
                                            {reportData.behavior_analysis && (
                                                <div className="report-section">
                                                    <h4 className="report-section-title">Behavior analysis</h4>
                                                    <p style={{ color: 'var(--color-text-secondary)', lineHeight: '1.65', fontSize: '0.9rem', margin: 0 }}>
                                                        {reportData.behavior_analysis}
                                                    </p>
                                                </div>
                                            )}
                                        </>
                                    )}

                                    {/* --- Enhanced insights (appended; does not replace existing sections) --- */}
                                    {!structuredReport && perQuestionEvals.length > 0 && (
                                        <div className="report-section" style={{ marginTop: '16px' }}>
                                            <h4 className="report-section-title">Severity-based insights</h4>
                                            <ul className="report-list">
                                                <li>
                                                    High severity answers: <strong>{evalInsights.severityCounts.high || 0}</strong>
                                                </li>
                                                <li>
                                                    Medium severity answers: <strong>{evalInsights.severityCounts.medium || 0}</strong>
                                                </li>
                                                <li>
                                                    Low severity answers: <strong>{evalInsights.severityCounts.low || 0}</strong>
                                                </li>
                                                <li>
                                                    Avg correctness: <strong>{evalInsights.avgCorrectness}/10</strong>
                                                </li>
                                                <li>
                                                    Consistency: <strong>{evalInsights.consistency}</strong>
                                                </li>
                                            </ul>
                                            {(evalInsights.severityCounts.high || 0) >= 2 && (
                                                <div style={{ marginTop: 10, color: 'var(--color-error)', fontWeight: 600 }}>
                                                    Multiple critical conceptual gaps detected.
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {!structuredReport && perQuestionEvals.length > 0 && (
                                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '16px' }}>
                                            <div className="report-section" style={{ marginBottom: 0 }}>
                                                <h4 className="report-section-title" style={{ color: 'var(--color-success)' }}>Strengths (from answers)</h4>
                                                <ul className="report-list">
                                                    {evalInsights.strengths.map((s, i) => <li key={i}>{s}</li>)}
                                                    {evalInsights.strengths.length === 0 && (
                                                        <li style={{ color: 'var(--color-text-muted)' }}>No strong strengths detected from per-question evaluations</li>
                                                    )}
                                                </ul>
                                            </div>
                                            <div className="report-section" style={{ marginBottom: 0 }}>
                                                <h4 className="report-section-title" style={{ color: 'var(--color-error)' }}>Weaknesses (from answers)</h4>
                                                <ul className="report-list">
                                                    {evalInsights.weaknesses.map((w, i) => <li key={i}>{w}</li>)}
                                                    {evalInsights.weaknesses.length === 0 && (
                                                        <li style={{ color: 'var(--color-text-muted)' }}>No specific mistakes/missing points extracted</li>
                                                    )}
                                                </ul>
                                            </div>
                                        </div>
                                    )}

                                    {!structuredReport && perQuestionEvals.length > 0 && (
                                        <div className="report-section" style={{ marginTop: '16px' }}>
                                            <h4 className="report-section-title" style={{ color: 'var(--color-error)' }}>Critical issues (misconceptions)</h4>
                                            <ul className="report-list">
                                                {evalInsights.criticalIssues.map((c, i) => <li key={i}>{c}</li>)}
                                                {evalInsights.criticalIssues.length === 0 && (
                                                    <li style={{ color: 'var(--color-text-muted)' }}>No misconceptions detected</li>
                                                )}
                                            </ul>
                                        </div>
                                    )}

                                    {!structuredReport && perQuestionEvals.length > 0 && (
                                        <div className="report-section">
                                            <h4 className="report-section-title">Hiring decision (computed)</h4>
                                            <div style={{
                                                padding: '10px 12px',
                                                borderRadius: '10px',
                                                background: 'var(--color-bg-alt)',
                                                border: '1px solid var(--color-border)'
                                            }}>
                                                <div style={{ fontWeight: 800, marginBottom: 6 }}>{evalInsights.decision}</div>
                                                <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem', lineHeight: 1.5 }}>
                                                    {evalInsights.decisionRationale}
                                                </div>
                                            </div>
                                            <div style={{ marginTop: 8, color: 'var(--color-text-muted)', fontSize: '0.8rem' }}>
                                                Note: This is an additional computed signal and does not replace the existing recommendation above.
                                            </div>
                                        </div>
                                    )}

                                    {/* Optional expandable per-question view */}
                                    {!structuredReport && perQuestionEvals.length > 0 && (
                                        <div className="report-section">
                                            <h4 className="report-section-title">Per-question insights</h4>
                                            <div style={{ display: 'grid', gap: 10 }}>
                                                {perQuestionEvals.slice(0, 15).map((q, idx) => (
                                                    <details key={idx} style={{
                                                        padding: '10px 12px',
                                                        borderRadius: '10px',
                                                        background: 'var(--color-bg-alt)',
                                                        border: '1px solid var(--color-border)'
                                                    }}>
                                                        <summary style={{ cursor: 'pointer', fontWeight: 700 }}>
                                                            Q{idx + 1}{q.topic ? ` • ${q.topic}` : ''}{q.severity ? ` • ${q.severity.toUpperCase()}` : ''}
                                                        </summary>
                                                        <div style={{ marginTop: 8, color: 'var(--color-text-secondary)', lineHeight: 1.55, fontSize: '0.9rem' }}>
                                                            {q.question ? <div style={{ marginBottom: 8 }}><strong>Question:</strong> {q.question}</div> : null}
                                                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginBottom: 8 }}>
                                                                <div><strong>{q.correctness}</strong>/10<div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>Correctness</div></div>
                                                                <div><strong>{q.concept_depth}</strong>/10<div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>Depth</div></div>
                                                                <div><strong>{q.communication}</strong>/10<div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>Communication</div></div>
                                                                <div><strong>{q.confidence}</strong>/10<div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>Confidence</div></div>
                                                            </div>
                                                            {q.final_feedback && (
                                                                <div style={{ marginBottom: 8 }}><strong>Feedback:</strong> {q.final_feedback}</div>
                                                            )}
                                                            {q.mistakes.length > 0 && (
                                                                <div style={{ marginBottom: 8 }}>
                                                                    <strong>Mistakes:</strong>
                                                                    <ul className="report-list" style={{ marginTop: 6 }}>
                                                                        {q.mistakes.slice(0, 5).map((m, i) => <li key={i}>{m}</li>)}
                                                                    </ul>
                                                                </div>
                                                            )}
                                                            {q.missing_points.length > 0 && (
                                                                <div style={{ marginBottom: 8 }}>
                                                                    <strong>Missing points:</strong>
                                                                    <ul className="report-list" style={{ marginTop: 6 }}>
                                                                        {q.missing_points.slice(0, 5).map((m, i) => <li key={i}>{m}</li>)}
                                                                    </ul>
                                                                </div>
                                                            )}
                                                            {q.misconceptions.length > 0 && (
                                                                <div>
                                                                    <strong>Misconceptions:</strong>
                                                                    <ul className="report-list" style={{ marginTop: 6 }}>
                                                                        {q.misconceptions.slice(0, 5).map((m, i) => <li key={i}>{m}</li>)}
                                                                    </ul>
                                                                </div>
                                                            )}
                                                        </div>
                                                    </details>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </>
                            ) : (
                                <div style={{ padding: '22px 0', color: 'var(--color-text-muted)', textAlign: 'center' }}>
                                    No report is available for this session.
                                </div>
                            )}
                        </div>

                        <div className="popup-footer">
                            <button className="btn btn-secondary btn-sm" onClick={() => setReportModal(false)}>
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Rules Modal */}
            {showRulesModal.show && (
                <div style={{
                    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999,
                    backdropFilter: 'blur(4px)'
                }}>
                    <div style={{
                        backgroundColor: 'var(--color-bg-card)', borderRadius: '12px', padding: '32px', maxWidth: '600px', width: '90%',
                        boxShadow: '0 8px 32px rgba(0,0,0,0.2), inset 0 1px 1px rgba(255,255,255,0.05)',
                        border: '1px solid var(--color-border)', animation: 'slideUp 0.3s ease-out', maxHeight: '90vh', overflowY: 'auto'
                    }}>
                        <h2 style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: 0, color: 'var(--color-text-primary)' }}>
                            <FiShield style={{ color: 'var(--color-primary)' }} /> Interview Rules & Regulations
                        </h2>
                        <p style={{ color: 'var(--color-text-secondary)', marginBottom: '24px' }}>
                            Please review the strict AI proctoring policies before starting your session.
                        </p>
                        <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 24px 0', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                            <li style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                                <FiCamera size={20} />
                                <div><strong style={{ display: 'block' }}>Camera Required</strong><span style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>You must keep your webcam enabled. If your face is out of view, the interview will terminate instantly.</span></div>
                            </li>
                            <li style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                                <FiSmartphone size={20} />
                                <div><strong style={{ display: 'block', color: 'var(--color-error)' }}>No Mobile Phones or Tablets</strong><span style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>If a phone, tablet, or external remote is detected in your frame, the session will be immediately flagged and terminated.</span></div>
                            </li>
                            <li style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                                <FiMonitor size={20} />
                                <div><strong style={{ display: 'block', color: 'var(--color-error)' }}>No Tab Switching</strong><span style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>Any attempt to switch tabs, copy-paste, or minimize the browser window will terminate the test instantly.</span></div>
                            </li>
                            <li style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                                <FiUsers size={20} />
                                <div><strong style={{ display: 'block' }}>Solo Interview</strong><span style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>Only ONE person must be in the frame. The presence of multiple faces will trigger termination.</span></div>
                            </li>
                        </ul>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer', marginBottom: '24px', padding: '12px', backgroundColor: 'var(--color-bg-alt)', borderRadius: '8px' }}>
                            <input type="checkbox" checked={rulesAccepted} onChange={e => setRulesAccepted(e.target.checked)} style={{ transform: 'scale(1.2)' }} />
                            <span style={{ fontSize: '0.9rem', color: 'var(--color-text-primary)', fontWeight: 600 }}>I understand and agree to follow all proctoring rules.</span>
                        </label>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                            <button className="btn btn-secondary" onClick={() => { setShowRulesModal({ show: false, jobId: null }); setRulesAccepted(false); }}>Cancel</button>
                            <button 
                                className="btn btn-primary" 
                                disabled={!rulesAccepted}
                                onClick={() => {
                                    const path = showRulesModal.jobId 
                                        ? `/dashboard/interview/live?mode=recruiter&job_id=${showRulesModal.jobId}` 
                                        : '/dashboard/interview/live?mode=practice';
                                    setShowRulesModal({ show: false, jobId: null });
                                    navigate(path);
                                }}
                            >
                                Start Interview
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
