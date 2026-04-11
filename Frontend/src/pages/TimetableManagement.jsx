import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { 
    FiPlus, FiEdit2, FiTrash2, FiX, FiCalendar, FiClock, 
    FiDownload, FiUploadCloud, FiCheckCircle, FiAlertCircle,
    FiEye, FiList, FiCheck, FiChevronRight, FiLayers, FiBookOpen
} from 'react-icons/fi';
import { toast } from 'react-toastify';

export default function TimetableManagement() {
    const { user } = useAuth();
    const isHod = user?.role === 'HOD';
    const [activeTab, setActiveTab] = useState('view'); // 'view', 'add', 'bulk'
    const [entries, setEntries] = useState([]);
    const [loading, setLoading] = useState(true);
    const [statusFilter, setStatusFilter] = useState('active');
    
    // Multi-row form state
    const [batchSemester, setBatchSemester] = useState('');
    const [batchRows, setBatchRows] = useState([{ subject: '', date: '', time: '' }]);
    
    // Bulk Upload state
    const [file, setFile] = useState(null);
    const [uploadLoading, setUploadLoading] = useState(false);
    const [previewData, setPreviewData] = useState(null);
    const [bulkSubmitting, setBulkSubmitting] = useState(false);

    // Edit modal state
    const [showModal, setShowModal] = useState(false);
    const [editId, setEditId] = useState(null);
    const [form, setForm] = useState({ semester: '', subject_name: '', exam_date: '', exam_time: '' });

    useEffect(() => { fetchData(); }, [statusFilter]);

    const fetchData = async () => {
        try {
            setLoading(true);
            const url = isHod ? `/college/hod/timetable?status=${statusFilter}` : '/college/student/timetable';
            const res = await api.get(url);
            setEntries(res.data);
        } catch (err) { console.error(err); }
        finally { setLoading(false); }
    };

    const addBatchRow = () => {
        setBatchRows([...batchRows, { subject: '', date: '', time: '' }]);
    };

    const removeBatchRow = (index) => {
        setBatchRows(batchRows.filter((_, i) => i !== index));
    };

    const handleBatchRowChange = (index, field, value) => {
        const newRows = [...batchRows];
        newRows[index][field] = value;
        setBatchRows(newRows);
    };

    const handleBatchSubmit = async (e) => {
        e.preventDefault();
        if (!batchSemester) return toast.error('Please select a semester');
        
        try {
            const exams = batchRows.map(r => ({
                semester: batchSemester.toString(),
                subject: r.subject,
                date: r.date,
                time: r.time
            }));
            
            await api.post('/exam/bulk-create-exams', { exams });
            toast.success('Exams created successfully');
            setBatchRows([{ subject: '', date: '', time: '' }]);
            setBatchSemester('');
            setActiveTab('view');
            fetchData();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to create exams');
        }
    };

    const handleDownloadTemplate = async () => {
        try {
            const res = await api.get('/exam/template', { responseType: 'blob' });
            const url = window.URL.createObjectURL(new Blob([res.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', 'exam_timetable_template.csv');
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (err) { toast.error('Failed to download template'); }
    };

    const handleUploadPreview = async () => {
        if (!file) return toast.error('Please select a CSV file');
        setUploadLoading(true);
        const formData = new FormData();
        formData.append('file', file);
        try {
            const res = await api.post('/exam/upload-exam-csv', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            if (res.data.status === 'success') {
                setPreviewData(res.data.data);
            } else {
                toast.error(res.data.message);
            }
        } catch (err) { toast.error('Upload failed'); }
        finally { setUploadLoading(false); }
    };

    const handleBulkSubmit = async () => {
        if (!previewData) return;
        const validRows = previewData.filter(p => p.valid).map(p => p.row);
        if (validRows.length === 0) return toast.error('No valid rows to submit');

        setBulkSubmitting(true);
        try {
            await api.post('/exam/bulk-create-exams', { exams: validRows });
            toast.success(`Successfully uploaded ${validRows.length} exams`);
            setPreviewData(null);
            setFile(null);
            setActiveTab('view');
            fetchData();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to submit bulk data');
        } finally { setBulkSubmitting(false); }
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
        } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
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

    const getCountdown = (dateStr) => {
        const diff = new Date(dateStr) - new Date();
        if (diff <= 0) return 'Passed';
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        return `${days}d ${hours}h`;
    };

    if (loading && entries.length === 0) return <div className="spinner" style={{ margin: '40px auto' }}></div>;

    const hasErrors = previewData?.some(p => !p.valid);

    return (
        <div className="dashboard-content fade-in">
            <header className="page-header slide-in-left">
                <h1 className="gradient-text">{isHod ? 'Exam Timetable Management' : 'Exam Timetable'}</h1>
                <p>{isHod ? 'Create, edit, and manage department exam schedule' : 'View your upcoming exams'}</p>
            </header>

            {isHod && (
                <div className="dashboard-tabs" style={{ 
                    display: 'flex', 
                    gap: '12px', 
                    marginBottom: '32px', 
                    borderBottom: '1px solid var(--color-border)',
                    padding: '0 4px'
                }}>
                    <button 
                        className={`tab-btn-premium ${activeTab === 'view' ? 'active' : ''}`} 
                        onClick={() => setActiveTab('view')}
                    >
                        <FiEye /> View Timetable
                    </button>
                    <button 
                        className={`tab-btn-premium ${activeTab === 'add' ? 'active' : ''}`} 
                        onClick={() => setActiveTab('add')}
                    >
                        <FiPlus /> Add Exams
                    </button>
                    <button 
                        className={`tab-btn-premium ${activeTab === 'bulk' ? 'active' : ''}`} 
                        onClick={() => setActiveTab('bulk')}
                    >
                        <FiUploadCloud /> Upload Excel
                    </button>

                    <style>{`
                        .tab-btn-premium {
                            display: flex;
                            align-items: center;
                            gap: 8px;
                            padding: 12px 20px;
                            background: transparent;
                            border: none;
                            border-bottom: 3px solid transparent;
                            color: var(--color-text-muted);
                            font-weight: 600;
                            font-size: 0.95rem;
                            cursor: pointer;
                            transition: all 0.3s ease;
                        }
                        .tab-btn-premium:hover {
                            color: var(--color-secondary);
                            background: rgba(0, 188, 212, 0.04);
                        }
                        .tab-btn-premium.active {
                            color: var(--color-secondary);
                            border-bottom-color: var(--color-secondary);
                        }
                    `}</style>
                </div>
            )}

            {/* TAB: VIEW */}
            {activeTab === 'view' && (
                <div className="fade-in-up">
                    {isHod && (
                        <div className="status-toggle-bar" style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '24px' }}>
                            <div className="toggle-group-premium" style={{ 
                                display: 'inline-flex', 
                                background: 'var(--color-bg-card)', 
                                padding: '4px', 
                                borderRadius: '12px',
                                border: '1px solid var(--color-border)',
                                boxShadow: 'var(--shadow-soft)'
                            }}>
                                <button 
                                    className={`toggle-btn-p ${statusFilter === 'active' ? 'active' : ''}`}
                                    onClick={() => setStatusFilter('active')}
                                >
                                    Current
                                </button>
                                <button 
                                    className={`toggle-btn-p ${statusFilter === 'archived' ? 'active' : ''}`}
                                    onClick={() => setStatusFilter('archived')}
                                >
                                    Archive
                                </button>
                                <style>{`
                                    .toggle-btn-p {
                                        padding: 8px 20px;
                                        border-radius: 10px;
                                        font-size: 0.85rem;
                                        font-weight: 700;
                                        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                                        border: none;
                                        cursor: pointer;
                                        background: transparent;
                                        color: var(--color-text-muted);
                                    }
                                    .toggle-btn-p.active {
                                        background: var(--gradient-primary);
                                        color: white;
                                        box-shadow: 0 4px 12px rgba(0, 188, 212, 0.25);
                                    }
                                `}</style>
                            </div>
                        </div>
                    )}

                    {entries.length === 0 ? (
                        <div className="dashboard-card" style={{ textAlign: 'center', padding: '80px 40px' }}>
                            <FiCalendar style={{ fontSize: '4rem', color: 'var(--color-secondary)', opacity: 0.2, marginBottom: '20px' }} />
                            <h3 style={{ fontSize: '1.4rem', color: 'var(--color-text-primary)' }}>No {statusFilter === 'archived' ? 'Archived ' : ''}Exam Schedule</h3>
                            <p style={{ color: 'var(--color-text-muted)', maxWidth: '400px', margin: '0 auto' }}>
                                {isHod ? `Initialize the ${statusFilter} session by adding exam entries.` : `The ${statusFilter} timetable has not been published yet.`}
                            </p>
                        </div>
                    ) : (
                        Object.entries(
                            entries.reduce((acc, e) => {
                                const sem = e.semester;
                                if (!acc[sem]) acc[sem] = [];
                                acc[sem].push(e);
                                return acc;
                            }, {})
                        )
                        .sort(([a], [b]) => a - b)
                        .map(([sem, semEntries], sIdx) => (
                            <div key={sem} className="fade-in-up" style={{ marginBottom: '40px', animationDelay: `${sIdx * 0.1}s` }}>
                                <div style={{ 
                                    display: 'flex', 
                                    alignItems: 'center', 
                                    gap: '12px', 
                                    marginBottom: '18px'
                                }}>
                                    <h3 style={{ margin: 0, fontSize: '1.2rem', fontFamily: 'var(--font-heading)', color: 'var(--color-text-primary)' }}>
                                        Semester {sem}
                                    </h3>
                                    <span className="role-badge" style={{ background: 'rgba(0, 188, 212, 0.1)', color: 'var(--color-secondary)' }}>
                                        {semEntries.length} Exams
                                    </span>
                                </div>
                                <div className="data-table-container enhanced-table-wrapper">
                                    <table className="data-table enhanced-table">
                                        <thead>
                                            <tr>
                                                <th style={{ width: '35%' }}>Subject Name</th>
                                                <th>Exam Date</th>
                                                <th>Exam Time</th>
                                                <th>Countdown</th>
                                                {isHod && <th style={{ textAlign: 'right' }}>Actions</th>}
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {semEntries.map((e, i) => (
                                                <tr key={e.id} className={i % 2 === 0 ? 'row-even' : 'row-odd'}>
                                                    <td style={{ fontWeight: 600 }}>{e.subject_name}</td>
                                                    <td>
                                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                            <FiCalendar style={{ color: 'var(--color-secondary)' }} />
                                                            {e.exam_date}
                                                        </div>
                                                    </td>
                                                    <td>
                                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                            <FiClock style={{ color: 'var(--color-accent)' }} />
                                                            {e.exam_time}
                                                        </div>
                                                    </td>
                                                    <td>
                                                        <span style={{
                                                            padding: '4px 12px',
                                                            borderRadius: '20px',
                                                            fontSize: '0.8rem',
                                                            fontWeight: '700',
                                                            background: getCountdown(e.exam_date) === 'Passed' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(34, 197, 94, 0.1)',
                                                            color: getCountdown(e.exam_date) === 'Passed' ? 'var(--color-error)' : 'var(--color-success)',
                                                            display: 'inline-flex',
                                                            alignItems: 'center',
                                                            gap: '6px'
                                                        }}>
                                                            <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'currentColor' }}></span>
                                                            {getCountdown(e.exam_date)}
                                                        </span>
                                                    </td>
                                                    {isHod && (
                                                        <td style={{ textAlign: 'right' }}>
                                                            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                                                                <button className="action-btn action-btn-outline" onClick={() => handleEdit(e)} title="Edit" style={{ padding: '6px' }}>
                                                                    <FiEdit2 />
                                                                </button>
                                                                <button className="action-btn action-btn-danger" onClick={() => handleDelete(e.id)} title="Delete" style={{ padding: '6px' }}>
                                                                    <FiTrash2 />
                                                                </button>
                                                            </div>
                                                        </td>
                                                    )}
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            )}

            {/* TAB: ADD EXAMS */}
            {isHod && activeTab === 'add' && (
                <div className="dashboard-card fade-in-up" style={{ padding: '32px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '32px' }}>
                        <div style={{ width: 44, height: 44, borderRadius: '12px', background: 'var(--gradient-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white' }}>
                            <FiPlus style={{ fontSize: '1.4rem' }} />
                        </div>
                        <h3 style={{ margin: 0, fontSize: '1.2rem' }}>Manual Entry</h3>
                    </div>

                    <form onSubmit={handleBatchSubmit}>
                        <div className="form-group" style={{ maxWidth: '320px', marginBottom: '40px' }}>
                            <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <FiLayers style={{ color: 'var(--color-secondary)' }} /> Applies to Semester *
                            </label>
                            <select className="form-input" value={batchSemester} onChange={e => setBatchSemester(e.target.value)} required>
                                <option value="">Select Semester</option>
                                {[1, 2, 3, 4, 5, 6, 7, 8].map(s => <option key={s} value={s}>Semester {s}</option>)}
                            </select>
                        </div>

                        <div style={{ marginBottom: '32px' }}>
                            {batchRows.map((row, idx) => (
                                <div key={idx} className="fade-in-up" style={{ 
                                    display: 'grid', 
                                    gridTemplateColumns: '2fr 1.5fr 1fr 44px', 
                                    gap: '20px', 
                                    alignItems: 'end', 
                                    marginBottom: '20px', 
                                    paddingBottom: '20px', 
                                    borderBottom: '1px solid var(--color-border)',
                                    animationDelay: `${idx * 0.05}s`
                                }}>
                                    <div className="form-group" style={{ margin: 0 }}>
                                        <label className="form-label">Subject</label>
                                        <input type="text" className="form-input" placeholder="e.g. Data Structures" value={row.subject} onChange={e => handleBatchRowChange(idx, 'subject', e.target.value)} required />
                                    </div>
                                    <div className="form-group" style={{ margin: 0 }}>
                                        <label className="form-label">Exam Date</label>
                                        <input type="date" className="form-input" value={row.date} onChange={e => handleBatchRowChange(idx, 'date', e.target.value)} required />
                                    </div>
                                    <div className="form-group" style={{ margin: 0 }}>
                                        <label className="form-label">Time</label>
                                        <input type="time" className="form-input" value={row.time} onChange={e => handleBatchRowChange(idx, 'time', e.target.value)} required />
                                    </div>
                                    <button 
                                        type="button" 
                                        className="icon-btn" 
                                        style={{ height: '42px', color: 'var(--color-error)' }} 
                                        onClick={() => removeBatchRow(idx)} 
                                        disabled={batchRows.length === 1}
                                    >
                                        <FiTrash2 />
                                    </button>
                                </div>
                            ))}
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <button type="button" className="action-btn action-btn-outline" onClick={addBatchRow} style={{ padding: '10px 24px' }}>
                                <FiPlus /> Add Another Subject
                            </button>
                            <button type="submit" className="btn btn-primary" style={{ padding: '10px 40px' }}>
                                Publish Exams ({batchRows.length})
                            </button>
                        </div>
                    </form>
                </div>
            )}

            {/* TAB: UPLOAD EXCEL */}
            {isHod && activeTab === 'bulk' && (
                <div className="fade-in-up">
                    <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: '28px' }}>
                        <button onClick={handleDownloadTemplate} className="btn-secondary-card" style={{ 
                            display: 'flex', 
                            alignItems: 'center', 
                            gap: '10px', 
                            padding: '12px 24px', 
                            background: 'var(--color-bg-card)',
                            border: '1px solid var(--color-border)',
                            borderRadius: '12px',
                            fontWeight: 600,
                            color: 'var(--color-text-secondary)',
                            cursor: 'pointer',
                            transition: 'all 0.2s ease'
                        }}>
                            <FiDownload style={{ color: 'var(--color-secondary)' }} /> Download CSV Template
                        </button>
                        <style>{`
                            .btn-secondary-card:hover { 
                                border-color: var(--color-secondary); 
                                box-shadow: var(--shadow-soft);
                                transform: translateY(-1px);
                            }
                        `}</style>
                    </div>
 
                    <div className="dashboard-card" style={{ padding: '40px', textAlign: 'center' }}>
                        <label htmlFor="exam-csv" style={{ 
                            display: 'block', 
                            padding: '60px 20px',
                            border: '2px dashed var(--color-border)',
                            borderRadius: '20px',
                            background: 'var(--color-bg-main)',
                            textAlign: 'center',
                            cursor: 'pointer',
                            transition: 'all 0.3s ease',
                            marginBottom: '32px'
                        }} className="upload-label-premium">
                            <FiUploadCloud style={{ fontSize: '3.5rem', color: 'var(--color-secondary)', marginBottom: '16px' }} />
                            <h3 style={{ marginBottom: '8px', color: 'var(--color-text-primary)' }}>
                                {file ? file.name : 'UPLOAD EXAM SCHEDULE'}
                            </h3>
                            <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem' }}>
                                Select a CSV file following the template structure
                            </p>
                            <input id="exam-csv" type="file" accept=".csv" onChange={e => { setFile(e.target.files[0]); setPreviewData(null); }} style={{ display: 'none' }} />
                        </label>
                        <style>{`
                            .upload-label-premium:hover {
                                border-color: var(--color-secondary);
                                background: rgba(0, 188, 212, 0.04);
                            }
                        `}</style>
                        
                        <button className="btn btn-primary" style={{ 
                            width: '100%', 
                            height: '52px', 
                            fontSize: '1rem',
                            fontWeight: 700,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '10px'
                        }} onClick={handleUploadPreview} disabled={!file || uploadLoading}>
                            {uploadLoading ? 'Processing File...' : 'Upload & Preview Entries'}
                        </button>
                    </div>

                    {file && !previewData && (
                        <div style={{ textAlign: 'center', marginTop: '-16px', marginBottom: '32px' }}>
                            <button className="text-btn" style={{ color: 'var(--color-error)', fontSize: '0.9rem', fontWeight: 600 }} onClick={() => { setFile(null); setPreviewData(null); }}>
                                Remove File
                            </button>
                        </div>
                    )}

                    {previewData && (
                        <div className="fade-in-up">
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                                <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
                                    <FiList /> Preview Assignments <span style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem', fontWeight: 400 }}>({previewData.length} total)</span>
                                </h3>
                                <button className="btn btn-primary" onClick={handleBulkSubmit} disabled={hasErrors || bulkSubmitting} style={{ padding: '10px 24px' }}>
                                    {bulkSubmitting ? 'Submitting...' : 'Confirm & Publish'}
                                </button>
                            </div>
                            
                            {hasErrors && (
                                <div style={{ 
                                    padding: '16px', 
                                    background: 'rgba(239, 68, 68, 0.08)', 
                                    color: 'var(--color-error)', 
                                    borderRadius: '12px', 
                                    marginBottom: '32px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '12px',
                                    fontWeight: 600,
                                    fontSize: '0.9rem'
                                }}>
                                    <FiAlertCircle />
                                    <span>Template validation failed. Please fix marked errors in your CSV and re-upload.</span>
                                </div>
                            )}

                            {Object.entries(
                                previewData.reduce((acc, p) => {
                                    const sem = p.row.semester;
                                    if (!acc[sem]) acc[sem] = [];
                                    acc[sem].push(p);
                                    return acc;
                                }, {})
                            )
                            .sort(([a], [b]) => a - b)
                            .map(([sem, semRows]) => (
                                <div key={sem} style={{ marginBottom: '32px' }}>
                                    <div style={{ 
                                        display: 'flex', 
                                        alignItems: 'center', 
                                        gap: '10px', 
                                        marginBottom: '16px' 
                                    }}>
                                        <h4 style={{ margin: 0, fontSize: '1rem', color: 'var(--color-text-primary)' }}>Semester {sem}</h4>
                                        <span className="role-badge" style={{ fontSize: '0.7rem' }}>{semRows.length} Rows</span>
                                    </div>
                                    <div className="data-table-container enhanced-table-wrapper">
                                        <table className="data-table enhanced-table">
                                            <thead>
                                                <tr>
                                                    <th>Subject</th>
                                                    <th>Date</th>
                                                    <th>Time</th>
                                                    <th style={{ textAlign: 'right' }}>Status</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {semRows.map((p, i) => (
                                                    <tr key={i} style={{ 
                                                        background: p.valid ? 'transparent' : 'rgba(239, 68, 68, 0.04)'
                                                    }}>
                                                        <td style={{ fontWeight: 600 }}>{p.row.subject}</td>
                                                        <td>{p.row.date}</td>
                                                        <td>{p.row.time}</td>
                                                        <td style={{ textAlign: 'right' }}>
                                                            {p.valid ? 
                                                                <span style={{ color: 'var(--color-success)', fontSize: '0.85rem', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                                                                    <FiCheck /> Verified
                                                                </span> : 
                                                                <span style={{ color: 'var(--color-error)', fontSize: '0.85rem', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                                                                    <FiAlertCircle /> {p.error}
                                                                </span>
                                                            }
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
                </div>
            )}

            {/* Modal for Quick Edit */}
            {showModal && (
                <div className="modal-overlay" onClick={() => setShowModal(false)}>
                    <div className="modal-content fade-in-up" onClick={e => e.stopPropagation()} style={{ maxWidth: '520px' }}>
                        <div className="modal-header">
                            <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                <FiCalendar style={{ color: 'var(--color-secondary)' }} /> {editId ? 'Modify' : 'Create'} Exam Entry
                            </h3>
                            <button className="modal-close" onClick={() => setShowModal(false)}><FiX /></button>
                        </div>
                        <form onSubmit={handleSubmit} className="modal-form">
                            <div className="form-group">
                                <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                    <FiLayers style={{ color: 'var(--color-secondary)' }} /> Semester *
                                </label>
                                <select className="form-input" value={form.semester} onChange={e => setForm({ ...form, semester: e.target.value })} required>
                                    {[1, 2, 3, 4, 5, 6, 7, 8].map(s => <option key={s} value={s}>{s}</option>)}
                                </select>
                            </div>
                            <div className="form-group">
                                <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                    <FiBookOpen style={{ color: 'var(--color-secondary)' }} /> Subject Name *
                                </label>
                                <input type="text" className="form-input" value={form.subject_name}
                                    onChange={e => setForm({ ...form, subject_name: e.target.value })} required />
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                                <div className="form-group">
                                    <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                        <FiCalendar style={{ color: 'var(--color-secondary)' }} /> Exam Date *
                                    </label>
                                    <input type="date" className="form-input" value={form.exam_date}
                                        onChange={e => setForm({ ...form, exam_date: e.target.value })} required />
                                </div>
                                <div className="form-group">
                                    <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                        <FiClock style={{ color: 'var(--color-secondary)' }} /> Exam Time *
                                    </label>
                                    <input type="time" className="form-input" value={form.exam_time}
                                        onChange={e => setForm({ ...form, exam_time: e.target.value })} required />
                                </div>
                            </div>
                            <div className="modal-actions" style={{ marginTop: '32px' }}>
                                <button type="button" className="btn btn-secondary" style={{ border: '1px solid var(--color-border)' }} onClick={() => setShowModal(false)}>Cancel</button>
                                <button type="submit" className="btn btn-primary" style={{ padding: '0 32px' }}>
                                    {editId ? 'Save Changes' : 'Create Entry'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
