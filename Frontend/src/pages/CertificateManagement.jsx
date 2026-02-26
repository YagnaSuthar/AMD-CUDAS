import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { FiUpload, FiAward, FiCheckCircle, FiClock, FiFile } from 'react-icons/fi';
import { toast } from 'react-toastify';

export default function CertificateManagement() {
    const { user } = useAuth();
    const [certs, setCerts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [title, setTitle] = useState('');
    const [file, setFile] = useState(null);

    useEffect(() => { fetchCerts(); }, []);

    const fetchCerts = async () => {
        try {
            setLoading(true);
            const res = await api.get('/college/student/certificates');
            setCerts(res.data);
        } catch (err) { console.error(err); }
        finally { setLoading(false); }
    };

    const handleUpload = async (e) => {
        e.preventDefault();
        if (!title || !file) { toast.error('Title and file are required'); return; }
        setUploading(true);
        try {
            const formData = new FormData();
            formData.append('title', title);
            formData.append('file', file);
            await api.post('/college/student/certificates', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            toast.success('Certificate uploaded successfully');
            setTitle('');
            setFile(null);
            fetchCerts();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Upload failed');
        } finally { setUploading(false); }
    };

    const totalPoints = certs.reduce((sum, c) => sum + c.points, 0);
    const verifiedCount = certs.filter(c => c.is_verified).length;

    if (loading) return <div className="spinner" style={{ margin: '40px auto' }}></div>;

    return (
        <div className="dashboard-content fade-in">
            <div className="page-header slide-in-left">
                <h1 className="gradient-text">Certificates & Skills</h1>
                <p>Upload certificates and track verification status</p>
            </div>

            {/* Stats */}
            <div className="stats-grid fade-in-up" style={{ marginBottom: '24px' }}>
                <div className="stat-card">
                    <div className="stat-card-header">
                        <span className="stat-card-label">Total Certificates</span>
                        <div className="stat-card-icon" style={{ background: 'var(--gradient-primary)' }}><FiFile /></div>
                    </div>
                    <div className="stat-card-value">{certs.length}</div>
                </div>
                <div className="stat-card">
                    <div className="stat-card-header">
                        <span className="stat-card-label">Verified</span>
                        <div className="stat-card-icon" style={{ background: 'var(--color-success)' }}><FiCheckCircle /></div>
                    </div>
                    <div className="stat-card-value">{verifiedCount}</div>
                </div>
                <div className="stat-card">
                    <div className="stat-card-header">
                        <span className="stat-card-label">Total Points</span>
                        <div className="stat-card-icon" style={{ background: 'var(--gradient-secondary)' }}><FiAward /></div>
                    </div>
                    <div className="stat-card-value">{totalPoints}</div>
                </div>
            </div>

            {/* Upload Form */}
            <div className="dashboard-card fade-in-up fade-in-delay-1">
                <h3><FiUpload style={{ marginRight: 8 }} /> Upload Certificate</h3>
                <form onSubmit={handleUpload} className="cert-upload-form">
                    <div className="form-group">
                        <label>Certificate Title *</label>
                        <input type="text" className="form-input" value={title}
                            onChange={e => setTitle(e.target.value)} placeholder="e.g. AWS Cloud Certification" required />
                    </div>
                    <div className="form-group">
                        <label>Certificate File *</label>
                        <div className="file-input-wrapper">
                            <input type="file" id="cert-file" className="file-input-hidden"
                                onChange={e => setFile(e.target.files[0])}
                                accept=".pdf,.jpg,.jpeg,.png,.webp" required />
                            <label htmlFor="cert-file" className="file-input-label">
                                <FiUpload />
                                {file ? file.name : 'Choose file (PDF, JPG, PNG)'}
                            </label>
                        </div>
                    </div>
                    <button type="submit" className="btn btn-primary" disabled={uploading}>
                        {uploading ? 'Uploading...' : 'Upload Certificate'}
                    </button>
                </form>
            </div>

            {/* Certificates List */}
            <div className="cert-grid fade-in-up fade-in-delay-2">
                {certs.length === 0 ? (
                    <div className="empty-state">
                        <FiAward className="empty-state-icon" />
                        <h3>No Certificates Yet</h3>
                        <p>Upload your first certificate to get started.</p>
                    </div>
                ) : (
                    certs.map((c, i) => (
                        <div key={c.id} className="cert-card" style={{ animationDelay: `${i * 0.05}s` }}>
                            <div className="cert-card-icon">
                                <FiAward />
                            </div>
                            <div className="cert-card-body">
                                <h4>{c.title}</h4>
                                <div className="cert-card-meta">
                                    <span className={`status-badge ${c.is_verified ? 'status-badge-approved' : 'status-badge-pending'}`}>
                                        {c.is_verified ? '✓ Verified' : '⏳ Pending'}
                                    </span>
                                    {c.points > 0 && (
                                        <span className="cert-points">+{c.points} pts</span>
                                    )}
                                </div>
                                <a href={`/certificates/${c.file_name}`} target="_blank" rel="noopener noreferrer"
                                    className="cert-view-link">View File →</a>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
