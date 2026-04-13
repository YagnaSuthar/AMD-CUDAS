import { useState, useEffect } from 'react';
import { useAuth } from '../../../../context/AuthContext';
import { CHILD_ROLE_MAP, ROLE_LABELS } from '../../../../utils/roles';
import api from '../../../../utils/api';
import { FiUploadCloud, FiDownload, FiCheckCircle, FiPlus, FiGrid, FiLoader } from 'react-icons/fi';
import { toast } from 'react-toastify';
import SkeletonText from '../../../../components/common/skeleton/SkeletonText';
import SkeletonCard from '../../../../components/common/skeleton/SkeletonCard';

/* ── Processing Steps Config ─────────────────────────────────────────── */
const PROCESSING_STEPS = [
    { label: 'Validating CSV structure', duration: 1500 },
    { label: 'Creating user accounts', duration: 3000 },
    { label: 'Generating credentials', duration: 2000 },
    { label: 'Finalizing records', duration: 1500 },
];

export default function UploadCSV() {
    const { user } = useAuth();
    const [file, setFile] = useState(null);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState('');
    const [processingStep, setProcessingStep] = useState(0);

    // Department states (Principal only)
    const [departments, setDepartments] = useState([]);
    const [newDept, setNewDept] = useState('');
    const [deptLoading, setDeptLoading] = useState(false);

    const isPrincipal = user.role === 'COLLEGE_PRINCIPAL';
    const targetRole = CHILD_ROLE_MAP[user.role];

    // Animate through processing steps while loading
    useEffect(() => {
        if (!loading) {
            setProcessingStep(0);
            return;
        }
        let step = 0;
        setProcessingStep(0);
        const interval = setInterval(() => {
            step++;
            if (step < PROCESSING_STEPS.length) {
                setProcessingStep(step);
            } else {
                // Loop back or stay at last
                clearInterval(interval);
            }
        }, 2000);
        return () => clearInterval(interval);
    }, [loading]);

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

    /* ── Processing Skeleton UI ──────────────────────────────────────── */
    if (loading) {
        return (
            <div className="dashboard-content">
                <div className="page-header slide-in-left">
                    <h1 className="gradient-text">Processing Upload…</h1>
                    <p>Please wait while we process your CSV file.</p>
                </div>

                {/* Processing Status Card */}
                <div className="dashboard-card fade-in-up" style={{ padding: '40px', textAlign: 'center' }}>
                    {/* Pulsing Loader Icon */}
                    <div style={{
                        width: '80px', height: '80px', borderRadius: '50%',
                        background: 'var(--gradient-primary)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        margin: '0 auto 28px',
                        animation: 'csvPulse 2s ease-in-out infinite',
                        boxShadow: '0 0 40px rgba(0, 188, 212, 0.3)'
                    }}>
                        <FiLoader style={{ fontSize: '2rem', color: '#fff', animation: 'csvSpin 1.5s linear infinite' }} />
                    </div>

                    <h3 style={{ margin: '0 0 8px', fontSize: '1.3rem', color: 'var(--color-text-primary)' }}>
                        {PROCESSING_STEPS[processingStep]?.label || 'Processing…'}
                    </h3>
                    <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem', marginBottom: '36px' }}>
                        Step {processingStep + 1} of {PROCESSING_STEPS.length}
                    </p>

                    {/* Progress Steps */}
                    <div style={{
                        display: 'flex', justifyContent: 'center', gap: '0',
                        maxWidth: '500px', margin: '0 auto 32px', alignItems: 'center'
                    }}>
                        {PROCESSING_STEPS.map((step, i) => (
                            <div key={i} style={{ display: 'flex', alignItems: 'center', flex: i < PROCESSING_STEPS.length - 1 ? 1 : 'none' }}>
                                {/* Step Circle */}
                                <div style={{
                                    width: '36px', height: '36px', borderRadius: '50%', flexShrink: 0,
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    fontSize: '0.8rem', fontWeight: 700,
                                    background: i <= processingStep ? 'var(--gradient-primary)' : 'var(--color-bg-main)',
                                    color: i <= processingStep ? '#fff' : 'var(--color-text-muted)',
                                    border: i <= processingStep ? 'none' : '2px solid var(--color-border)',
                                    transition: 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)',
                                    boxShadow: i === processingStep ? '0 0 16px rgba(0, 188, 212, 0.4)' : 'none'
                                }}>
                                    {i < processingStep ? <FiCheckCircle style={{ fontSize: '1rem' }} /> : i + 1}
                                </div>
                                {/* Connector Line */}
                                {i < PROCESSING_STEPS.length - 1 && (
                                    <div style={{
                                        flex: 1, height: '3px', borderRadius: '2px',
                                        background: i < processingStep
                                            ? 'var(--color-secondary)'
                                            : 'var(--color-border)',
                                        transition: 'background 0.5s ease',
                                        margin: '0 4px'
                                    }} />
                                )}
                            </div>
                        ))}
                    </div>

                    {/* Step Labels */}
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: `repeat(${PROCESSING_STEPS.length}, 1fr)`,
                        maxWidth: '500px', margin: '0 auto 36px',
                        gap: '8px'
                    }}>
                        {PROCESSING_STEPS.map((step, i) => (
                            <span key={i} style={{
                                fontSize: '0.72rem', fontWeight: i === processingStep ? 700 : 500,
                                color: i <= processingStep ? 'var(--color-secondary)' : 'var(--color-text-muted)',
                                transition: 'all 0.3s ease',
                                textAlign: 'center'
                            }}>
                                {step.label}
                            </span>
                        ))}
                    </div>
                </div>

                {/* Skeleton placeholders for the result area */}
                <div style={{ marginTop: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <SkeletonCard style={{ height: '80px' }} />
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
                        <SkeletonCard style={{ height: '60px' }} />
                        <SkeletonCard style={{ height: '60px' }} />
                        <SkeletonCard style={{ height: '60px' }} />
                    </div>
                    <SkeletonCard style={{ height: '120px' }} />
                </div>

                {/* Inline keyframes */}
                <style>{`
                    @keyframes csvPulse {
                        0%, 100% { transform: scale(1); box-shadow: 0 0 40px rgba(0, 188, 212, 0.3); }
                        50% { transform: scale(1.08); box-shadow: 0 0 60px rgba(0, 188, 212, 0.5); }
                    }
                    @keyframes csvSpin {
                        from { transform: rotate(0deg); }
                        to { transform: rotate(360deg); }
                    }
                `}</style>
            </div>
        );
    }

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
                    Upload & Create Accounts
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
