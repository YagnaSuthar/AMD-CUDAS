import { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { FiX } from 'react-icons/fi';

export default function RecruiterClgs() {
    const { user } = useAuth();

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const [colleges, setColleges] = useState([]);
    const [departments, setDepartments] = useState([]);
    const [studentsLoading, setStudentsLoading] = useState(false);

    const [jobs, setJobs] = useState([]);

    const [selectedStudentId, setSelectedStudentId] = useState('');
    const [selectedCollegeId, setSelectedCollegeId] = useState('');
    const [selectedDepartmentId, setSelectedDepartmentId] = useState('');
    const [selectedDepartmentName, setSelectedDepartmentName] = useState('');
    const [selectedPrincipalId, setSelectedPrincipalId] = useState('');
    const [showDepartments, setShowDepartments] = useState(false);
    const [showStudents, setShowStudents] = useState(false);
    const [showColleges, setShowColleges] = useState(true);
    const [semester, setSemester] = useState('');
    const [minAvgMarks, setMinAvgMarks] = useState('');
    const [minPoints, setMinPoints] = useState('');
    const [skill, setSkill] = useState('');
    const [students, setStudents] = useState([]);

    const [profile, setProfile] = useState(null);
    const [profileLoading, setProfileLoading] = useState(false);

    const [assignJobId, setAssignJobId] = useState('');
    const [invitePipelineId, setInvitePipelineId] = useState('');
    const [inviteLink, setInviteLink] = useState('');
    const [hiredPipelineId, setHiredPipelineId] = useState('');
    const [hiredCompanyName, setHiredCompanyName] = useState('');

    const [messageModal, setMessageModal] = useState(false);
    const [messageSubject, setMessageSubject] = useState('');
    const [messageBody, setMessageBody] = useState('');

    const fetchColleges = async () => {
        const res = await api.get('/recruiter/colleges');
        setColleges(res.data || []);
    };

    const fetchJobs = async () => {
        const res = await api.get('/jobs/my');
        setJobs(res.data || []);
    };

    const fetchDepartments = async (collegeId) => {
        const res = await api.get(`/recruiter/colleges/${collegeId}/departments`);
        setDepartments(res.data || []);
    };

    const fetchStudents = async () => {
        if (!selectedPrincipalId) return;
        setStudentsLoading(true);
        try {
            const params = {
                college_principal_id: selectedPrincipalId,
            };
            if (selectedDepartmentName) params.department = selectedDepartmentName;
            if (semester) params.semester = Number(semester);
            if (minAvgMarks) params.min_avg_marks = Number(minAvgMarks);
            if (minPoints) params.min_points = Number(minPoints);
            if (skill) params.skill = skill;

            const res = await api.get('/recruiter/students', { params });
            setStudents(res.data || []);
        } catch (e) {
            setError(e?.response?.data?.detail || 'Failed to fetch students');
        } finally {
            setStudentsLoading(false);
        }
    };

    useEffect(() => {
        (async () => {
            try {
                setLoading(true);
                setError('');
                await fetchColleges();
                if (user?.role === 'RECRUITER') {
                    await fetchJobs();
                }
            } catch (e) {
                setError(e?.response?.data?.detail || 'Failed to load colleges');
            } finally {
                setLoading(false);
            }
        })();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [user?.role]);

    useEffect(() => {
        (async () => {
            if (!selectedCollegeId) {
                setDepartments([]);
                setSelectedDepartmentName('');
                setSelectedPrincipalId('');
                setStudents([]);
                setShowDepartments(false);
                setShowStudents(false);
                setShowColleges(true);
                return;
            }
            const c = colleges.find((x) => x.id === selectedCollegeId);
            setSelectedPrincipalId(c?.principal_id || '');
            setSelectedDepartmentId('');
            setSelectedDepartmentName('');
            setStudents([]);
            setSemester('');
            setShowStudents(false);
            setShowColleges(false);
            try {
                await fetchDepartments(selectedCollegeId);
                setShowDepartments(true);
            } catch (e) {
                setError(e?.response?.data?.detail || 'Failed to load departments');
            }
        })();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedCollegeId]);

    useEffect(() => {
        if (selectedPrincipalId && selectedDepartmentName) {
            fetchStudents();
            setShowStudents(true);
            setShowDepartments(false);
        } else {
            setShowStudents(false);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedPrincipalId, selectedDepartmentName, semester, minAvgMarks, minPoints, skill]);

    const backToColleges = () => {
        setSelectedCollegeId('');
        setSelectedDepartmentId('');
        setSelectedDepartmentName('');
        setSelectedPrincipalId('');
        setStudents([]);
        setShowColleges(true);
        setShowDepartments(false);
        setShowStudents(false);
    };

    const backToDepartments = () => {
        setSelectedDepartmentId('');
        setSelectedDepartmentName('');
        setStudents([]);
        setShowColleges(false);
        setShowDepartments(true);
        setShowStudents(false);
    };

    const sortedStudents = useMemo(() => {
        const arr = Array.isArray(students) ? [...students] : [];
        arr.sort((a, b) => {
            // Sort by total_score first, then by average_marks, then by semester
            const scoreA = a.total_score || 0;
            const scoreB = b.total_score || 0;
            if (scoreB !== scoreA) return scoreB - scoreA;

            const avgA = a.average_marks || 0;
            const avgB = b.average_marks || 0;
            if (avgB !== avgA) return avgB - avgA;

            const semA = a.semester ?? -1;
            const semB = b.semester ?? -1;
            return semB - semA;
        });
        return arr;
    }, [students]);

    const copy = async (text) => {
        try {
            await navigator.clipboard.writeText(text);
        } catch {
            // ignore
        }
    };

    const openProfile = async (sid) => {
        setSelectedStudentId(sid);
        setProfile(null);
        setInvitePipelineId('');
        setInviteLink('');
        setHiredPipelineId('');
        setHiredCompanyName('');

        setProfileLoading(true);
        try {
            const res = await api.get(`/recruiter/student/${sid}`);
            setProfile(res.data);
        } catch (e) {
            setError(e?.response?.data?.detail || 'Failed to load profile');
        } finally {
            setProfileLoading(false);
        }
    };

    const openMessageModal = () => {
        setMessageSubject('');
        setMessageBody('');
        setMessageModal(true);
    };

    const sendMessage = async () => {
        if (!selectedStudentId || !messageSubject.trim() || !messageBody.trim()) return;
        try {
            await api.post('/messages/send', {
                recipient_id: selectedStudentId,
                subject: messageSubject.trim(),
                body: messageBody.trim(),
            });
            setMessageModal(false);
            setMessageSubject('');
            setMessageBody('');
        } catch (e) {
            setError(e?.response?.data?.detail || 'Failed to send message');
        }
    };

    const closeProfile = () => {
        setSelectedStudentId('');
        setProfile(null);
    };

    const assignAi = async () => {
        if (!assignJobId || !selectedStudentId) return;
        try {
            setError('');
            await api.post('/pipeline/assign-ai', {
                student_id: selectedStudentId,
                job_id: assignJobId,
            });
            setAssignJobId('');
            await openProfile(selectedStudentId);
        } catch (e) {
            setError(e?.response?.data?.detail || 'Failed to assign AI interview');
        }
    };

    const inviteRound2 = async () => {
        if (!invitePipelineId || !inviteLink || !selectedStudentId) return;
        try {
            setError('');
            await api.post('/pipeline/invite-round2', {
                student_id: selectedStudentId,
                pipeline_id: invitePipelineId,
                round2_link: inviteLink,
            });
            setInvitePipelineId('');
            setInviteLink('');
            await openProfile(selectedStudentId);
        } catch (e) {
            setError(e?.response?.data?.detail || 'Failed to invite to round 2');
        }
    };

    const markHired = async () => {
        if (!hiredPipelineId || !hiredCompanyName || !selectedStudentId) return;
        try {
            setError('');
            await api.post('/pipeline/mark-hired', {
                student_id: selectedStudentId,
                pipeline_id: hiredPipelineId,
                hired_company_name: hiredCompanyName,
            });
            setHiredPipelineId('');
            setHiredCompanyName('');
            await openProfile(selectedStudentId);
        } catch (e) {
            setError(e?.response?.data?.detail || 'Failed to mark as hired');
        }
    };

    if (loading) {
        return (
            <div className="dashboard-page">
                <div className="page-header">
                    <h2>CLGs</h2>
                </div>
                <div style={{ padding: '2rem', textAlign: 'center' }}>Loading colleges...</div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="dashboard-page">
                <div className="page-header">
                    <h2>CLGs</h2>
                </div>
                <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-error)' }}>{error}</div>
            </div>
        );
    }

    return (
        <>
            <div className="dashboard-page">
                <div className="page-header slide-in-left">
                    <h2>CLGs</h2>
                    <p>Browse colleges, departments, and students</p>
                </div>

                <div className={`clgs-grid fade-in-up ${selectedStudentId && profile ? 'drawer-open' : ''}`}>
                    {/* Colleges Table - Show Only When No College Selected */}
                    <div className={`card clgs-card transition-table ${showColleges ? 'table-visible' : 'table-hidden'}`}>
                        <div className="card-header">
                            <h4>Colleges</h4>
                        </div>
                        <div className="card-body">
                            {colleges.length === 0 ? (
                                <div className="clgs-empty">No colleges found.</div>
                            ) : (
                                <div className="table-responsive">
                                    <table className="table clgs-table">
                                        <thead>
                                            <tr>
                                                <th>College</th>
                                                <th>Principal</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {colleges.map((c) => (
                                                <tr
                                                    key={c.id}
                                                    onClick={() => setSelectedCollegeId(c.id)}
                                                    className={c.id === selectedCollegeId ? 'clgs-row clgs-row-selected' : 'clgs-row'}
                                                >
                                                    <td className="clgs-strong">{c.name}</td>
                                                    <td>{c.principal_name || '-'}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Departments Table - Show Only After College Selection */}
                    <div className={`card clgs-card transition-table ${showDepartments ? 'table-visible' : 'table-hidden'}`}>
                        <div className="card-header">
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <h4>Departments</h4>
                                <button className="btn btn-sm btn-secondary" onClick={backToColleges}>
                                    ← Back to Colleges
                                </button>
                            </div>
                        </div>
                        <div className="card-body">
                            {departments.length === 0 ? (
                                <div className="clgs-empty">No departments found.</div>
                            ) : (
                                <div className="table-responsive">
                                    <table className="table clgs-table">
                                        <thead>
                                            <tr>
                                                <th>Department</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {departments.map((d) => (
                                                <tr
                                                    key={d.id || d.name}
                                                    onClick={() => {
                                                        setSelectedDepartmentId(d.id || '');
                                                        setSelectedDepartmentName(d.name || '');
                                                    }}
                                                    className={(d.id || '') === selectedDepartmentId ? 'clgs-row clgs-row-selected' : 'clgs-row'}
                                                >
                                                    <td className="clgs-strong">{d.name || '-'}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Students Table - Show Only After Department Selection */}
                    <div className={`card clgs-card transition-table ${showStudents ? 'table-visible' : 'table-hidden'}`}>
                        <div className="card-header">
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <h4>Students</h4>
                                <button className="btn btn-sm btn-secondary" onClick={backToDepartments}>
                                    ← Back to Departments
                                </button>
                            </div>
                        </div>
                        <div className="card-body">
                            <>
                                <div className="clgs-filters">
                                    <div>
                                        <label className="form-label">Semester</label>
                                        <select className="input" value={semester} onChange={(e) => setSemester(e.target.value)}>
                                            <option value="">All</option>
                                            <option value="8">8</option>
                                            <option value="7">7</option>
                                            <option value="6">6</option>
                                            <option value="5">5</option>
                                            <option value="4">4</option>
                                            <option value="3">3</option>
                                            <option value="2">2</option>
                                            <option value="1">1</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="form-label">Min Avg Marks</label>
                                        <input type="number" className="input" placeholder="e.g. 60" value={minAvgMarks} onChange={(e) => setMinAvgMarks(e.target.value)} />
                                    </div>
                                    <div>
                                        <label className="form-label">Min Points</label>
                                        <input type="number" className="input" placeholder="e.g. 50" value={minPoints} onChange={(e) => setMinPoints(e.target.value)} />
                                    </div>
                                    <div>
                                        <label className="form-label">Skill</label>
                                        <input type="text" className="input" placeholder="e.g. React" value={skill} onChange={(e) => setSkill(e.target.value)} />
                                    </div>
                                </div>

                                {studentsLoading ? (
                                    <div className="clgs-empty">Loading students...</div>
                                ) : sortedStudents.length === 0 ? (
                                    <div className="clgs-empty">No students found for the selected filters.</div>
                                ) : (
                                    <div className="table-responsive">
                                        <table className="table clgs-table">
                                            <thead>
                                                <tr>
                                                    <th>Name</th>
                                                    <th>Email</th>
                                                    <th>Semester</th>
                                                    <th>Avg</th>
                                                    <th>Score</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {sortedStudents.map((stu) => (
                                                    <tr
                                                        key={stu.id}
                                                        onClick={() => openProfile(stu.id)}
                                                        className="clgs-row"
                                                    >
                                                        <td className="clgs-strong">{stu.name}</td>
                                                        <td>{stu.email}</td>
                                                        <td>{stu.semester ?? '-'}</td>
                                                        <td>{stu.average_marks ?? '-'}</td>
                                                        <td>{stu.total_score ?? '-'}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </>
                        </div>
                    </div>

                </div>

                {selectedStudentId && profile && (
                    <>
                        <div
                            className="clgs-drawer-overlay"
                            onClick={closeProfile}
                        />
                        <div
                            className="clgs-drawer"
                        >
                            <div className="card clgs-drawer-card">
                                <div className="card-header clgs-drawer-header">
                                    <h4 style={{ margin: 0 }}>Student Profile</h4>
                                    <button className="btn btn-sm btn-secondary" onClick={closeProfile}>Close</button>
                                </div>
                                <div className="card-body">
                                    {profileLoading ? (
                                        <div>Loading profile...</div>
                                    ) : (
                                        <div style={{ display: 'grid', gap: '1.5rem' }}>
                                            <div>
                                                <div style={{ fontWeight: 700, marginBottom: '6px' }}>Name</div>
                                                <div style={{ color: 'var(--color-text-muted)' }}>{profile.name}</div>
                                            </div>

                                            <div>
                                                <div style={{ fontWeight: 700, marginBottom: '6px' }}>Email</div>
                                                <div style={{ color: 'var(--color-text-muted)', fontFamily: 'monospace', fontSize: '0.9rem' }}>
                                                    {profile.email}
                                                    <button
                                                        style={{ marginLeft: '8px', padding: '2px 6px', fontSize: '0.7rem' }}
                                                        onClick={() => copy(profile.email)}
                                                    >
                                                        Copy
                                                    </button>
                                                </div>
                                            </div>

                                            <div>
                                                <div style={{ fontWeight: 700, marginBottom: '6px' }}>Resume</div>
                                                <div style={{ color: 'var(--color-text-muted)' }}>
                                                    {profile.resume_url ? (
                                                        <a href={profile.resume_url} target="_blank" rel="noreferrer">View Resume</a>
                                                    ) : (
                                                        '-'
                                                    )}
                                                </div>
                                            </div>

                                            <div>
                                                <div style={{ fontWeight: 700, marginBottom: '6px' }}>Skills</div>
                                                <div style={{ color: 'var(--color-text-muted)' }}>
                                                    {Array.isArray(profile.skills) && profile.skills.length ? profile.skills.join(', ') : '-'}
                                                </div>
                                            </div>

                                            <div>
                                                <div style={{ fontWeight: 700, marginBottom: '6px' }}>Quick Actions</div>
                                                <div style={{ display: 'grid', gap: '8px' }}>
                                                    <button className="btn btn-secondary" type="button" onClick={openMessageModal}>
                                                        Message Student
                                                    </button>
                                                    <select className="input" value={assignJobId} onChange={(e) => setAssignJobId(e.target.value)}>
                                                        <option value="">Assign AI Interview: Select Job</option>
                                                        {jobs.map((j) => (
                                                            <option key={j.id} value={j.id}>{j.title}</option>
                                                        ))}
                                                    </select>
                                                    <button className="btn btn-primary" type="button" onClick={assignAi} disabled={!assignJobId}>
                                                        Assign AI (Round 1)
                                                    </button>

                                                    <input className="input" placeholder="Pipeline ID for Round 2" value={invitePipelineId} onChange={(e) => setInvitePipelineId(e.target.value)} />
                                                    <input className="input" placeholder="Round 2 meeting link" value={inviteLink} onChange={(e) => setInviteLink(e.target.value)} />
                                                    <button className="btn btn-primary" type="button" onClick={inviteRound2} disabled={!invitePipelineId || !inviteLink}>
                                                        Invite Round 2
                                                    </button>

                                                    <input className="input" placeholder="Pipeline ID to mark hired" value={hiredPipelineId} onChange={(e) => setHiredPipelineId(e.target.value)} />
                                                    <input className="input" placeholder="Company name" value={hiredCompanyName} onChange={(e) => setHiredCompanyName(e.target.value)} />
                                                    <button className="btn btn-primary" type="button" onClick={markHired} disabled={!hiredPipelineId || !hiredCompanyName}>
                                                        Mark Hired
                                                    </button>
                                                </div>
                                            </div>

                                            <div>
                                                <div style={{ fontWeight: 700, marginBottom: '6px' }}>Pipeline</div>
                                                {Array.isArray(profile.pipelines) && profile.pipelines.length ? (
                                                    <div style={{ display: 'grid', gap: '8px' }}>
                                                        {profile.pipelines.slice(0, 6).map((p) => (
                                                            <div key={p.pipeline_id} style={{ padding: '10px', border: '1px solid var(--color-border)', borderRadius: '10px' }}>
                                                                <div style={{ fontWeight: 800 }}>{p.status}</div>
                                                                <div style={{ color: 'var(--color-text-muted)', fontFamily: 'monospace', fontSize: '0.8rem' }}>{p.pipeline_id}</div>
                                                                <div style={{ color: 'var(--color-text-muted)', fontFamily: 'monospace', fontSize: '0.8rem' }}>job: {p.job_id}</div>
                                                                <div style={{ color: 'var(--color-text-muted)', fontFamily: 'monospace', fontSize: '0.8rem' }}>session: {p.ai_session_id || '-'}</div>
                                                                {p.round2_link && (
                                                                    <a href={p.round2_link} target="_blank" rel="noreferrer">Round 2 link</a>
                                                                )}
                                                                {p.hired_company_name && (
                                                                    <div>Hired: {p.hired_company_name}</div>
                                                                )}
                                                            </div>
                                                        ))}
                                                    </div>
                                                ) : (
                                                    <div style={{ color: 'var(--color-text-muted)' }}>-</div>
                                                )}
                                            </div>

                                            <div>
                                                <div style={{ fontWeight: 700, marginBottom: '6px' }}>Recent AI Interviews</div>
                                                {Array.isArray(profile.interviews) && profile.interviews.length ? (
                                                    <div style={{ display: 'grid', gap: '8px' }}>
                                                        {profile.interviews.slice(0, 6).map((it) => (
                                                            <div key={it.session_id} style={{ padding: '10px', border: '1px solid var(--color-border)', borderRadius: '10px' }}>
                                                                <div style={{ fontWeight: 800 }}>{it.job_role}</div>
                                                                <div style={{ color: 'var(--color-text-muted)' }}>status: {it.status}</div>
                                                                <div style={{ color: 'var(--color-text-muted)' }}>score: {it.final_score ?? '-'}</div>
                                                                <div style={{ color: 'var(--color-text-muted)' }}>
                                                                    {it.recommendation ? it.recommendation.slice(0, 160) + (it.recommendation.length > 160 ? '…' : '') : '-'}
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                ) : (
                                                    <div style={{ color: 'var(--color-text-muted)' }}>-</div>
                                                )}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </>
                )}
            </div>

            {/* Message Modal */}
            {messageModal && (
                <div className="modal-overlay" onClick={() => setMessageModal(false)}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h4>Send Message to Student</h4>
                            <button className="modal-close" onClick={() => setMessageModal(false)}>
                                <FiX />
                            </button>
                        </div>
                        <div className="modal-body">
                            <div className="form-group">
                                <label className="form-label">Subject</label>
                                <input
                                    type="text"
                                    className="form-input"
                                    value={messageSubject}
                                    onChange={(e) => setMessageSubject(e.target.value)}
                                    placeholder="Message subject"
                                    required
                                />
                            </div>
                            <div className="form-group">
                                <label className="form-label">Message</label>
                                <textarea
                                    className="form-input"
                                    rows={5}
                                    value={messageBody}
                                    onChange={(e) => setMessageBody(e.target.value)}
                                    placeholder="Type your message here..."
                                    required
                                />
                            </div>
                        </div>
                        <div className="modal-footer">
                            <button className="btn btn-secondary" onClick={() => setMessageModal(false)}>Cancel</button>
                            <button className="btn btn-primary" onClick={sendMessage} disabled={!messageSubject.trim() || !messageBody.trim()}>
                                Send Message
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
