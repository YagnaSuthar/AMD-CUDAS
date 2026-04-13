import { useState, useEffect } from 'react';
import { useAuth } from '../../../../context/AuthContext';
import api from '../../../../utils/api';
import { FiPlus, FiEdit2, FiLock, FiCheckCircle, FiX, FiSearch } from 'react-icons/fi';
import { toast } from 'react-toastify';
import SkeletonText from '../../../../components/common/skeleton/SkeletonText';
import SkeletonCard from '../../../../components/common/skeleton/SkeletonCard';
import SkeletonTableRow from '../../../../components/common/skeleton/SkeletonTableRow';

export default function MarksManagement() {
    const { user } = useAuth();
    const isHod = user.role === 'HOD';
    const isFaculty = user.role === 'FACULTY';
    const [marks, setMarks] = useState([]);
    const [students, setStudents] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [editId, setEditId] = useState(null);
    const [form, setForm] = useState({ student_id: '', subject_name: '', semester: '', marks_obtained: '', max_marks: '100' });
    const [searchTerm, setSearchTerm] = useState('');
    const [performanceFilter, setPerformanceFilter] = useState('');
    const [lockSemester, setLockSemester] = useState('');

    useEffect(() => { fetchData(); }, []);

    const fetchData = async () => {
        try {
            setLoading(true);
            const url = isHod ? '/college/hod/marks' : '/college/faculty/marks';
            const res = await api.get(url);
            setMarks(res.data);
            if (isFaculty) {
                const sRes = await api.get('/college/users');
                setStudents(sRes.data.filter(u => u.role === 'STUDENT'));
            }
        } catch (err) { console.error(err); }
        finally { setLoading(false); }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            if (editId) {
                await api.put(`/college/faculty/marks/${editId}`, {
                    marks_obtained: parseFloat(form.marks_obtained),
                    max_marks: parseFloat(form.max_marks),
                });
                toast.success('Marks updated');
            } else {
                await api.post('/college/faculty/marks', {
                    ...form,
                    semester: parseInt(form.semester),
                    marks_obtained: parseFloat(form.marks_obtained),
                    max_marks: parseFloat(form.max_marks),
                });
                toast.success('Marks uploaded');
            }
            resetModal();
            fetchData();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed');
        }
    };

    const handleEdit = (m) => {
        if (m.is_locked) { toast.error('Marks are locked by HOD'); return; }
        setEditId(m.id);
        setForm({ student_id: m.student_id, subject_name: m.subject_name, semester: m.semester, marks_obtained: m.marks_obtained, max_marks: m.max_marks });
        setShowModal(true);
    };

    const handleLock = async () => {
        if (!lockSemester) { toast.error('Enter semester to lock'); return; }
        try {
            await api.put('/college/hod/marks/lock', { semester: parseInt(lockSemester) });
            toast.success(`Semester ${lockSemester} marks locked`);
            fetchData();
        } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    };

    const handleApprove = async () => {
        if (!lockSemester) { toast.error('Enter semester to approve'); return; }
        try {
            await api.put('/college/hod/marks/approve', { semester: parseInt(lockSemester) });
            toast.success(`Semester ${lockSemester} results approved`);
            fetchData();
        } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    };

    const resetModal = () => {
        setShowModal(false);
        setEditId(null);
        setForm({ student_id: '', subject_name: '', semester: '', marks_obtained: '', max_marks: '100' });
    };

    const filtered = marks.filter(m => {
        const pct = m.max_marks > 0 ? (m.marks_obtained / m.max_marks * 100) : 0;

        if (performanceFilter === 'TOP' && pct < 85) return false;
        if (performanceFilter === 'WEAK' && pct >= 50) return false;

        if (!searchTerm) return true;
        const t = searchTerm.toLowerCase();
        return m.student_name?.toLowerCase().includes(t) || m.subject_name?.toLowerCase().includes(t);
    });

    if (loading) {
        return (
            <div className="dashboard-content fade-in">
                <div className="page-header slide-in-left">
                    <SkeletonText variant="title" style={{ width: '300px' }} />
                    <SkeletonText variant="subtitle" style={{ width: '400px' }} />
                </div>
                <div className="marks-controls fade-in-up" style={{ marginBottom: '24px' }}>
                    <SkeletonCard style={{ width: '150px', height: '40px' }} />
                </div>
                <div className="data-table-container fade-in-up">
                    <SkeletonTableRow rows={5} columns={7} />
                </div>
            </div>
        );
    }

    return (
        <div className="dashboard-content fade-in">
            <div className="page-header slide-in-left">
                <h1 className="gradient-text">{isHod ? 'Marks Monitoring' : 'Marks Management'}</h1>
                <p>{isHod ? 'View, lock, and approve student marks' : 'Upload and manage internal marks'}</p>
            </div>

            <div className="marks-controls fade-in-up">
                {isFaculty && (
                    <button className="btn btn-primary" onClick={() => { resetModal(); setShowModal(true); }}>
                        <FiPlus /> Upload Marks
                    </button>
                )}
                {isHod && (
                    <div className="lock-controls">
                        <input type="number" className="form-input" placeholder="Semester" min="1" max="8"
                            value={lockSemester} onChange={e => setLockSemester(e.target.value)}
                            style={{ width: '120px' }} />
                        <button className="btn btn-secondary" onClick={handleLock}>
                            <FiLock /> Lock Marks
                        </button>
                        <button className="btn btn-primary" onClick={handleApprove}>
                            <FiCheckCircle /> Approve Results
                        </button>
                    </div>
                )}
            </div>

            <div className="data-table-container fade-in-up fade-in-delay-1">
                <div className="data-table-header">
                    <h3>Marks Records <span className="table-count">({filtered.length})</span></h3>
                    <div className="table-search">
                        <FiSearch className="table-search-icon" />
                        <input type="text" placeholder="Search student or subject..."
                            className="table-search-input" value={searchTerm}
                            onChange={e => setSearchTerm(e.target.value)} />
                    </div>
                </div>
                <div className="filter-bar" style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'flex-end', margin: '12px 0 0' }}>
                    <div className="form-group" style={{ marginBottom: 0, minWidth: '180px' }}>
                        <label style={{ fontSize: '0.8rem' }}>Performance</label>
                        <select
                            className="form-input"
                            value={performanceFilter}
                            onChange={(e) => setPerformanceFilter(e.target.value)}
                        >
                            <option value="">All Students</option>
                            <option value="TOP">Top (â‰¥ 85%)</option>
                            <option value="WEAK">Weak (&lt; 50%)</option>
                        </select>
                    </div>
                    <button className="btn btn-secondary" onClick={() => setPerformanceFilter('')}>
                        Reset Performance
                    </button>
                </div>
                {filtered.length === 0 ? (
                    <div className="empty-state">
                        <h3>No Marks Found</h3>
                        <p>{isFaculty ? 'Upload marks to get started.' : 'No marks records yet.'}</p>
                    </div>
                ) : (
                    <div className="table-scroll-wrapper">
                        <table className="data-table enhanced-table">
                            <thead>
                                <tr>
                                    <th>Student</th>
                                    <th>Subject</th>
                                    <th>Semester</th>
                                    <th>Marks</th>
                                    <th>Max</th>
                                    <th>%</th>
                                    <th>Status</th>
                                    {isFaculty && <th>Actions</th>}
                                </tr>
                            </thead>
                            <tbody>
                                {filtered.map((m, i) => {
                                    const pct = m.max_marks > 0 ? (m.marks_obtained / m.max_marks * 100).toFixed(1) : 0;
                                    return (
                                        <tr key={m.id} className={i % 2 === 0 ? 'row-even' : 'row-odd'}>
                                            <td style={{ fontWeight: 600 }}>{m.student_name || 'â€”'}</td>
                                            <td>{m.subject_name}</td>
                                            <td>{m.semester}</td>
                                            <td>{m.marks_obtained}</td>
                                            <td>{m.max_marks}</td>
                                            <td>
                                                <span style={{
                                                    fontWeight: 700,
                                                    color: pct >= 60 ? 'var(--color-success)' : pct >= 40 ? 'var(--color-warning)' : 'var(--color-error)'
                                                }}>{pct}%</span>
                                            </td>
                                            <td>
                                                <span className={`status-badge ${m.is_locked ? 'status-badge-locked' : 'status-badge-approved'}`}>
                                                    {m.is_locked ? 'ðŸ”’ Locked' : 'Open'}
                                                </span>
                                            </td>
                                            {isFaculty && (
                                                <td>
                                                    <button className="action-btn action-btn-outline"
                                                        onClick={() => handleEdit(m)} title="Edit"
                                                        disabled={m.is_locked}>
                                                        <FiEdit2 />
                                                    </button>
                                                </td>
                                            )}
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Upload/Edit Modal */}
            {showModal && (
                <div className="modal-overlay" onClick={resetModal}>
                    <div className="modal-content fade-in-up" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3>{editId ? 'Edit Marks' : 'Upload Marks'}</h3>
                            <button className="modal-close" onClick={resetModal}><FiX /></button>
                        </div>
                        <form onSubmit={handleSubmit} className="modal-form">
                            {!editId && (
                                <>
                                    <div className="form-group">
                                        <label>Student *</label>
                                        <select className="form-input" value={form.student_id}
                                            onChange={e => setForm({ ...form, student_id: e.target.value })} required>
                                            <option value="">Select Student</option>
                                            {students.map(s => (
                                                <option key={s.id} value={s.id}>{s.name} ({s.email})</option>
                                            ))}
                                        </select>
                                    </div>
                                    <div className="form-group">
                                        <label>Subject Name *</label>
                                        <input type="text" className="form-input" value={form.subject_name}
                                            onChange={e => setForm({ ...form, subject_name: e.target.value })} required />
                                    </div>
                                    <div className="form-group">
                                        <label>Semester *</label>
                                        <input type="number" className="form-input" value={form.semester}
                                            onChange={e => setForm({ ...form, semester: e.target.value })} required min="1" max="8" />
                                    </div>
                                </>
                            )}
                            <div className="form-group">
                                <label>Marks Obtained *</label>
                                <input type="number" step="0.1" className="form-input" value={form.marks_obtained}
                                    onChange={e => setForm({ ...form, marks_obtained: e.target.value })} required />
                            </div>
                            <div className="form-group">
                                <label>Max Marks</label>
                                <input type="number" step="0.1" className="form-input" value={form.max_marks}
                                    onChange={e => setForm({ ...form, max_marks: e.target.value })} />
                            </div>
                            <div className="modal-actions">
                                <button type="button" className="btn btn-secondary" onClick={resetModal}>Cancel</button>
                                <button type="submit" className="btn btn-primary">{editId ? 'Update' : 'Upload'}</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
