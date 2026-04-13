import { useState, useEffect } from 'react';
import { FiPlus, FiTrash2, FiEdit2, FiCheck, FiX, FiBook, FiUser, FiLayers, FiBookOpen, FiCode } from 'react-icons/fi';
import api from '../../../../utils/api';
import { toast } from 'react-toastify';
import SkeletonText from '../../../../components/common/skeleton/SkeletonText';
import SkeletonCard from '../../../../components/common/skeleton/SkeletonCard';
import SkeletonTableRow from '../../../../components/common/skeleton/SkeletonTableRow';

export default function AssignSubjects() {
    const [faculty, setFaculty] = useState([]);
    const [assignments, setAssignments] = useState([]);
    const [loading, setLoading] = useState(false);
    const [submitting, setSubmitting] = useState(false);

    const [formData, setFormData] = useState({
        faculty_id: '',
        semester: '',
        subject_name: '',
        subject_code: ''
    });

    const [editingId, setEditingId] = useState(null);
    const [editData, setEditData] = useState({});

    const fetchData = async () => {
        setLoading(true);
        try {
            const [facRes, assignRes] = await Promise.all([
                api.get('/college/users'),
                api.get('/api/subject/all')
            ]);
            // Filter for faculty only
            setFaculty(facRes.data.filter(u => u.role === 'FACULTY'));
            setAssignments(assignRes.data);
        } catch (err) {
            console.error('Failed to fetch data', err);
            toast.error('Failed to load data');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!formData.faculty_id || !formData.semester || !formData.subject_name || !formData.subject_code) {
            toast.error('All fields are required');
            return;
        }

        setSubmitting(true);
        try {
            await api.post('/api/subject/assign', formData);
            toast.success('Subject assigned successfully');
            setFormData({ faculty_id: '', semester: '', subject_name: '', subject_code: '' });
            fetchData();
        } catch (err) {
            console.error('Failed to assign subject', err);
            toast.error(err.response?.data?.detail || 'Assignment failed');
        } finally {
            setSubmitting(false);
        }
    };

    const handleDelete = async (id) => {
        if (!window.confirm('Are you sure you want to remove this assignment?')) return;
        try {
            await api.delete(`/api/subject/${id}`);
            toast.success('Assignment removed');
            fetchData();
        } catch (err) {
            toast.error('Failed to delete');
        }
    };

    const startEdit = (assign) => {
        setEditingId(assign.id);
        setEditData({ ...assign });
    };

    const handleEditSave = async () => {
        try {
            await api.put(`/api/subject/${editingId}`, editData);
            toast.success('Assignment updated');
            setEditingId(null);
            fetchData();
        } catch (err) {
            toast.error('Update failed');
        }
    };

    if (loading && assignments.length === 0) {
        return (
            <div className="dashboard-content fade-in">
                <header className="page-header slide-in-left">
                    <SkeletonText variant="title" style={{ width: '300px' }} />
                    <SkeletonText variant="subtitle" style={{ width: '400px' }} />
                </header>
                <div className="dashboard-card fade-in-up" style={{ padding: '28px', marginBottom: '32px' }}>
                    <SkeletonCard style={{ height: '200px' }} />
                </div>
                <div className="data-table-container fade-in-up" style={{ animationDelay: '0.1s' }}>
                    <SkeletonTableRow rows={5} columns={5} />
                </div>
            </div>
        );
    }

    return (
        <div className="dashboard-content fade-in">
            <header className="page-header slide-in-left">
                <h1 className="gradient-text">Assign Subjects</h1>
                <p>Manage and map subjects to faculty members for the current academic session.</p>
            </header>

            {/* ASSIGNMENT FORM */}
            <div className="dashboard-card fade-in-up" style={{ padding: '28px', marginBottom: '32px' }}>
                <h3 style={{ marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--color-secondary)' }}>
                    <FiPlus /> New Subject Assignment
                </h3>
                <form onSubmit={handleSubmit} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '24px', alignItems: 'end' }}>
                    <div className="form-group" style={{ margin: 0 }}>
                        <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <FiUser style={{ color: 'var(--color-secondary)' }} /> Faculty Member
                        </label>
                        <select 
                            name="faculty_id" 
                            className="form-input" 
                            value={formData.faculty_id} 
                            onChange={handleChange}
                            required
                        >
                            <option value="">Select Faculty</option>
                            {faculty.map(f => (
                                <option key={f.id} value={f.id}>{f.name}</option>
                            ))}
                        </select>
                    </div>

                    <div className="form-group" style={{ margin: 0 }}>
                        <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <FiLayers style={{ color: 'var(--color-secondary)' }} /> Semester
                        </label>
                        <select 
                            name="semester" 
                            className="form-input" 
                            value={formData.semester} 
                            onChange={handleChange}
                            required
                        >
                            <option value="">Select Semester</option>
                            {[1, 2, 3, 4, 5, 6, 7, 8].map(s => (
                                <option key={s} value={s}>Semester {s}</option>
                            ))}
                        </select>
                    </div>

                    <div className="form-group" style={{ margin: 0 }}>
                        <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <FiBookOpen style={{ color: 'var(--color-secondary)' }} /> Subject Name
                        </label>
                        <input 
                            type="text" 
                            name="subject_name" 
                            className="form-input" 
                            placeholder="e.g. Operating Systems" 
                            value={formData.subject_name} 
                            onChange={handleChange}
                            required
                        />
                    </div>

                    <div className="form-group" style={{ margin: 0 }}>
                        <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <FiCode style={{ color: 'var(--color-secondary)' }} /> Subject Code
                        </label>
                        <input 
                            type="text" 
                            name="subject_code" 
                            className="form-input" 
                            placeholder="e.g. CS301" 
                            value={formData.subject_code} 
                            onChange={handleChange}
                            required
                        />
                    </div>

                    <div>
                        <button type="submit" className="btn btn-primary" disabled={submitting} style={{ width: '100%', height: '42px', padding: '0 20px' }}>
                            {submitting ? 'Assigning...' : 'Assign Subject'}
                        </button>
                    </div>
                </form>
            </div>

            {/* ASSIGNMENTS TABLE */}
            <div className="data-table-container fade-in-up" style={{ animationDelay: '0.1s' }}>
                <div className="data-table-header">
                    <h3>Active Assignments <span className="table-count">({assignments.length})</span></h3>
                </div>
                
                <div className="table-scroll-wrapper">
                    <table className="data-table enhanced-table">
                        <thead>
                            <tr>
                                <th>Faculty Name</th>
                                <th>Subject Name</th>
                                <th>Subject Code</th>
                                <th>Semester</th>
                                <th style={{ textAlign: 'right' }}>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {assignments.length > 0 ? (
                                assignments.map((assign, idx) => (
                                    <tr key={assign.id} className={idx % 2 === 0 ? 'row-even' : 'row-odd'}>
                                        <td style={{ fontWeight: 600 }}>{assign.faculty_name}</td>
                                        <td>
                                            {editingId === assign.id ? (
                                                <input 
                                                    className="form-input" 
                                                    style={{ height: '36px' }} 
                                                    value={editData.subject_name}
                                                    onChange={e => setEditData({...editData, subject_name: e.target.value})}
                                                />
                                            ) : assign.subject_name}
                                        </td>
                                        <td>
                                            {editingId === assign.id ? (
                                                <input 
                                                    className="form-input" 
                                                    style={{ height: '36px' }} 
                                                    value={editData.subject_code}
                                                    onChange={e => setEditData({...editData, subject_code: e.target.value})}
                                                />
                                            ) : (
                                                <code style={{ background: 'var(--color-primary-200)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.85rem' }}>
                                                    {assign.subject_code}
                                                </code>
                                            )}
                                        </td>
                                        <td>
                                            {editingId === assign.id ? (
                                                <select 
                                                    className="form-input" 
                                                    style={{ height: '36px' }}
                                                    value={editData.semester}
                                                    onChange={e => setEditData({...editData, semester: parseInt(e.target.value)})}
                                                >
                                                    {[1,2,3,4,5,6,7,8].map(s => <option key={s} value={s}>{s}</option>)}
                                                </select>
                                            ) : (
                                                <span className="role-badge">
                                                    Semester {assign.semester}
                                                </span>
                                            )}
                                        </td>
                                        <td style={{ textAlign: 'right' }}>
                                            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                                                {editingId === assign.id ? (
                                                    <>
                                                        <button className="icon-btn" title="Save" onClick={handleEditSave} style={{ color: 'var(--color-success)' }}>
                                                            <FiCheck />
                                                        </button>
                                                        <button className="icon-btn" title="Cancel" onClick={() => setEditingId(null)} style={{ color: 'var(--color-error)' }}>
                                                            <FiX />
                                                        </button>
                                                    </>
                                                ) : (
                                                    <>
                                                        <button className="action-btn action-btn-outline" title="Edit" onClick={() => startEdit(assign)} style={{ padding: '6px' }}>
                                                            <FiEdit2 />
                                                        </button>
                                                        <button className="action-btn action-btn-danger" title="Delete" onClick={() => handleDelete(assign.id)} style={{ padding: '6px' }}>
                                                            <FiTrash2 />
                                                        </button>
                                                    </>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            ) : (
                                <tr>
                                    <td colSpan="5">
                                        <div className="empty-state">
                                            <FiBook className="empty-state-icon" />
                                            <h3>No Assignments Yet</h3>
                                            <p>Select a faculty and subject above to start mapping them.</p>
                                        </div>
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
