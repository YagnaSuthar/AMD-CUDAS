import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { FiPlus, FiEdit2, FiTrash2, FiX, FiCalendar, FiClock } from 'react-icons/fi';
import { toast } from 'react-toastify';

export default function TimetableManagement() {
    const { user } = useAuth();
    const isHod = user.role === 'HOD';
    const [entries, setEntries] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [editId, setEditId] = useState(null);
    const [form, setForm] = useState({ semester: '', subject_name: '', exam_date: '', exam_time: '' });

    useEffect(() => { fetchData(); }, []);

    const fetchData = async () => {
        try {
            setLoading(true);
            const url = isHod ? '/college/hod/timetable' : '/college/student/timetable';
            const res = await api.get(url);
            setEntries(res.data);
        } catch (err) { console.error(err); }
        finally { setLoading(false); }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            if (editId) {
                await api.put(`/college/hod/timetable/${editId}`, form);
                toast.success('Timetable entry updated');
            } else {
                await api.post('/college/hod/timetable', { ...form, semester: parseInt(form.semester) });
                toast.success('Timetable entry created');
            }
            setShowModal(false);
            setEditId(null);
            setForm({ semester: '', subject_name: '', exam_date: '', exam_time: '' });
            fetchData();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed');
        }
    };

    const handleEdit = (entry) => {
        setEditId(entry.id);
        setForm({ semester: entry.semester, subject_name: entry.subject_name, exam_date: entry.exam_date, exam_time: entry.exam_time });
        setShowModal(true);
    };

    const handleDelete = async (id) => {
        if (!window.confirm('Delete this timetable entry?')) return;
        try {
            await api.delete(`/college/hod/timetable/${id}`);
            toast.success('Entry deleted');
            fetchData();
        } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    };

    // Countdown helper
    const getCountdown = (dateStr) => {
        const diff = new Date(dateStr) - new Date();
        if (diff <= 0) return 'Passed';
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        return `${days}d ${hours}h`;
    };

    if (loading) return <div className="spinner" style={{ margin: '40px auto' }}></div>;

    return (
        <div className="dashboard-content fade-in">
            <div className="page-header slide-in-left">
                <h1 className="gradient-text">{isHod ? 'Exam Timetable Management' : 'Exam Timetable'}</h1>
                <p>{isHod ? 'Create, edit, and manage department exam schedule' : 'View your upcoming exams'}</p>
            </div>

            {isHod && (
                <div style={{ marginBottom: '24px' }}>
                    <button className="btn btn-primary" onClick={() => { setEditId(null); setForm({ semester: '', subject_name: '', exam_date: '', exam_time: '' }); setShowModal(true); }}>
                        <FiPlus /> Add Exam Entry
                    </button>
                </div>
            )}

            <div className="timetable-grid fade-in-up">
                {entries.length === 0 ? (
                    <div className="empty-state">
                        <FiCalendar className="empty-state-icon" />
                        <h3>No Exam Schedule</h3>
                        <p>{isHod ? 'Add exam entries to create a timetable.' : 'No timetable published yet.'}</p>
                    </div>
                ) : (
                    entries.map((e, i) => (
                        <div key={e.id} className={`timetable-card fade-in-up`} style={{ animationDelay: `${i * 0.05}s` }}>
                            <div className="timetable-card-header">
                                <span className="timetable-semester">Sem {e.semester}</span>
                                {isHod && (
                                    <div className="timetable-actions">
                                        <button className="action-btn action-btn-outline" onClick={() => handleEdit(e)} title="Edit"><FiEdit2 /></button>
                                        <button className="action-btn action-btn-danger" onClick={() => handleDelete(e.id)} title="Delete"><FiTrash2 /></button>
                                    </div>
                                )}
                            </div>
                            <div className="timetable-card-body">
                                <h4>{e.subject_name}</h4>
                                <div className="timetable-meta">
                                    <span><FiCalendar /> {e.exam_date}</span>
                                    <span><FiClock /> {e.exam_time}</span>
                                </div>
                                <div className="timetable-countdown">
                                    {getCountdown(e.exam_date)}
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Modal */}
            {showModal && (
                <div className="modal-overlay" onClick={() => setShowModal(false)}>
                    <div className="modal-content fade-in-up" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3><FiCalendar style={{ marginRight: 8 }} /> {editId ? 'Edit' : 'Add'} Exam Entry</h3>
                            <button className="modal-close" onClick={() => setShowModal(false)}><FiX /></button>
                        </div>
                        <form onSubmit={handleSubmit} className="modal-form">
                            <div className="form-group">
                                <label>Semester *</label>
                                <input type="number" className="form-input" value={form.semester}
                                    onChange={e => setForm({ ...form, semester: e.target.value })} required min="1" max="8" />
                            </div>
                            <div className="form-group">
                                <label>Subject Name *</label>
                                <input type="text" className="form-input" value={form.subject_name}
                                    onChange={e => setForm({ ...form, subject_name: e.target.value })} required />
                            </div>
                            <div className="form-group">
                                <label>Exam Date *</label>
                                <input type="date" className="form-input" value={form.exam_date}
                                    onChange={e => setForm({ ...form, exam_date: e.target.value })} required />
                            </div>
                            <div className="form-group">
                                <label>Exam Time *</label>
                                <input type="time" className="form-input" value={form.exam_time}
                                    onChange={e => setForm({ ...form, exam_time: e.target.value })} required />
                            </div>
                            <div className="modal-actions">
                                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                                <button type="submit" className="btn btn-primary">{editId ? 'Update' : 'Create'}</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
