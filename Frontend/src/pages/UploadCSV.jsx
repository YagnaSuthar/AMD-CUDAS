import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { CHILD_ROLE_MAP, ROLE_LABELS } from '../utils/roles';
import api from '../utils/api';
import { FiUploadCloud, FiDownload, FiCheckCircle, FiPlus, FiGrid } from 'react-icons/fi';
import { toast } from 'react-toastify';

export default function UploadCSV() {
    const { user } = useAuth();
    const [file, setFile] = useState(null);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState('');

    // Department states (Principal only)
    const [departments, setDepartments] = useState([]);
    const [newDept, setNewDept] = useState('');
    const [deptLoading, setDeptLoading] = useState(false);

    const isPrincipal = user.role === 'COLLEGE_PRINCIPAL';
    const targetRole = CHILD_ROLE_MAP[user.role];

    useEffect(() => {
        if (isPrincipal) {
            fetchDepartments();
        }
    }, [isPrincipal]);

    const fetchDepartments = async () => {
        try {
            const res = await api.get('/college/departments/list');
            setDepartments(res.data);
        } catch (err) {
            console.error('Failed to fetch departments:', err);
        }
    };

    const handleAddDepartment = async () => {
        if (!newDept.trim()) return;
        setDeptLoading(true);
        try {
            await api.post('/college/departments', { name: newDept });
            toast.success(`Department '${newDept}' added`);
            setNewDept('');
            fetchDepartments();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to add department');
        } finally {
            setDeptLoading(false);
        }
    };

    const handleDownloadTemplate = async () => {
        // ... existing code ...
        try {
            const res = await api.get(`/csv/template?target_role=${targetRole}`, {
                responseType: 'blob'
            });
            const url = window.URL.createObjectURL(new Blob([res.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `${targetRole.toLowerCase()}_template.csv`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (err) {
            setError('Failed to download template.');
        }
    };

    const handleFileChange = (e) => {
        setFile(e.target.files[0]);
        setError('');
        setResult(null);
    };

    const handleUpload = async () => {
        if (!file) {
            setError('Please select a file first.');
            return;
        }

        setLoading(true);
        setError('');
        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await api.post(`/csv/upload?target_role=${targetRole}`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            setResult(res.data);
            setFile(null);
        } catch (err) {
            setError(err.response?.data?.detail || 'Upload failed. Check your CSV structure.');
        } finally {
            setLoading(false);
        }
    };

    const handleDownloadCredentials = async () => {
        if (!result?.credentials) return;
        try {
            const res = await api.post('/csv/download-credentials', result.credentials, {
                responseType: 'blob'
            });
            const url = window.URL.createObjectURL(new Blob([res.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', 'generated_credentials.csv');
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (err) {
            setError('Failed to download credentials.');
        }
    };

    if (!targetRole) {
        return (
            <div className="dashboard-content">
                <div className="empty-state">
                    <h3>Permission Denied</h3>
                    <p>Your role ({ROLE_LABELS[user.role]}) cannot create child users via CSV.</p>
                </div>
            </div>
        );
    }

    const childLabel = ROLE_LABELS[targetRole] || targetRole;

    return (
        <div className="dashboard-content">
            <div className="page-header slide-in-left">
                <h1 className="gradient-text">Bulk Create {childLabel}s</h1>
                <p>Use CSV upload to automatically create accounts and generate passwords.</p>
            </div>

            {isPrincipal && (
                <div className="dashboard-card fade-in-up" style={{ marginBottom: '32px' }}>
                    <div className="card-header">
                        <FiGrid className="card-icon" />
                        <h3>Manage Departments</h3>
                    </div>
                    <div className="form-row" style={{ marginTop: '16px' }}>
                        <div className="form-group" style={{ flex: 1 }}>
                            <input
                                type="text"
                                className="form-input"
                                placeholder="Enter new department name (e.g. Computer Science)"
                                value={newDept}
                                onChange={(e) => setNewDept(e.target.value)}
                            />
                        </div>
                        <button
                            className="btn btn-primary"
                            onClick={handleAddDepartment}
                            disabled={deptLoading || !newDept.trim()}
                        >
                            <FiPlus /> Add Department
                        </button>
                    </div>

                    <div className="dept-chips" style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '20px' }}>
                        {departments.length === 0 ? (
                            <p className="text-muted" style={{ fontSize: '0.9rem' }}>No departments added yet.</p>
                        ) : (
                            departments.map(d => (
                                <span key={d.id} className="status-badge status-badge-approved" style={{ fontSize: '0.85rem', padding: '6px 12px' }}>
                                    {d.name}
                                </span>
                            ))
                        )}
                    </div>
                </div>
            )}

            <div className="actions-row fade-in-up">
                <button onClick={handleDownloadTemplate} className="action-btn action-btn-outline">
                    <FiDownload /> Download {childLabel} CSV Template
                </button>
            </div>

            {error && <div className="alert alert-error" style={{ marginBottom: '24px' }}>{error}</div>}

            <div className="dashboard-card fade-in-up fade-in-delay-1">
                <div className="form-group" style={{ marginBottom: '24px' }}>
                    <label className="upload-zone" htmlFor="csv-upload">
                        <FiUploadCloud className="upload-zone-icon" />
                        <div style={{ marginBottom: '8px', fontFamily: 'var(--font-heading)', fontWeight: '600' }}>
                            {file ? file.name : `Select .csv file to upload`}
                        </div>
                        <p>Click or drag and drop your CSV file here.</p>
                        <input
                            id="csv-upload"
                            type="file"
                            accept=".csv"
                            onChange={handleFileChange}
                            style={{ display: 'none' }}
                        />
                    </label>
                </div>

                <button
                    onClick={handleUpload}
                    disabled={!file || loading}
                    className="btn btn-primary"
                    style={{ width: '100%' }}
                >
                    {loading ? 'Processing Array...' : `Upload & Create Accounts`}
                </button>
            </div>

            {result && result.credentials && (
                <div className="dashboard-card fade-in-up" style={{ backgroundColor: 'rgba(34, 197, 94, 0.05)', borderColor: 'var(--color-success)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
                        <FiCheckCircle style={{ color: 'var(--color-success)', fontSize: '1.5rem' }} />
                        <h3 style={{ margin: 0, color: 'var(--color-success)' }}>Success!</h3>
                    </div>
                    <p style={{ marginBottom: '24px' }}>{result.message}</p>

                    <button onClick={handleDownloadCredentials} className="action-btn action-btn-success">
                        <FiDownload /> Download Passwords (CSV)
                    </button>
                    <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginTop: '8px' }}>
                        Make sure to download these credentials now. Raw passwords are not stored in the database!
                    </p>
                </div>
            )}
        </div>
    );
}
