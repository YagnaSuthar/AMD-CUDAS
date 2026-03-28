import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { FiUpload, FiAward, FiCheckCircle, FiClock, FiFile, FiGithub, FiCode, FiAlertCircle, FiX } from 'react-icons/fi';
import { toast } from 'react-toastify';

export default function CertificateManagement() {
    const { user } = useAuth();
    const [certs, setCerts] = useState([]);
    const [projects, setProjects] = useState([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [file, setFile] = useState(null);

    const [githubUrl, setGithubUrl] = useState('');
    const [projectTitle, setProjectTitle] = useState('');
    const [projectDescription, setProjectDescription] = useState('');
    const [projectTechStack, setProjectTechStack] = useState('');
    const [verifyingProject, setVerifyingProject] = useState(false);
    const [verificationResult, setVerificationResult] = useState(null);

    // Modal state for viewing project details
    const [selectedProject, setSelectedProject] = useState(null);

    useEffect(() => { fetchCerts(); }, []);

    const fetchCerts = async () => {
        try {
            setLoading(true);
            const [certRes, projRes] = await Promise.all([
                api.get('/college/student/certificates'),
                api.get('/college/student/projects')
            ]);
            setCerts(certRes.data);
            setProjects(projRes.data);
        } catch (err) { console.error(err); }
        finally { setLoading(false); }
    };

    const isValidGithubUrl = (url) => {
        if (!url) return true; // empty is valid (optional field)
        return /^https?:\/\/(www\.)?github\.com\/[^/]+\/[^/]+/i.test(url.trim());
    };

    const handleUpload = async (e) => {
        e.preventDefault();

        // Validate: at least one input required
        if (!file && !githubUrl.trim()) {
            toast.error('Please upload a certificate file or enter a GitHub URL');
            return;
        }

        // Validate: certificate needs a title + file
        if (file && !title) {
            toast.error('Title is required for certificate upload');
            return;
        }

        // Validate: Project needs a title
        if (githubUrl.trim() && !projectTitle.trim()) {
            toast.error('Project Name is required when submitting a GitHub project');
            return;
        }

        // Validate: GitHub URL format
        if (githubUrl.trim() && !isValidGithubUrl(githubUrl)) {
            toast.error('Please enter a valid GitHub URL (e.g. https://github.com/user/repo)');
            return;
        }

        setUploading(true);
        try {
            // First submit to backend saving (using the single /certificates endpoint)
            const formData = new FormData();
            
            // If file is provided, submit the certificate
            if (file) {
                formData.append('title', title);
                if (description) formData.append('description', description);
                formData.append('file', file);
            }
            
            // If github URL is provided, append its details (api handles optional file/url logic)
            if (githubUrl.trim()) {
                // If NO file is provided, use the project title/desc for the form
                if (!file) {
                    formData.append('title', projectTitle);
                    if (projectDescription) formData.append('description', projectDescription);
                }
                
                formData.append('github_url', githubUrl.trim());
                if (projectTechStack) formData.append('tech_stack', projectTechStack);
            }

            await api.post('/college/student/certificates', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            
            if (file) toast.success('Certificate uploaded successfully');
            if (githubUrl.trim() && !file) toast.success('Project submitted successfully');

            // If GitHub URL is provided, trigger project verification asynchronously
            if (githubUrl.trim()) {
                setVerifyingProject(true);
                try {
                    const verifyFormData = new FormData();
                    verifyFormData.append('link', githubUrl.trim());
                    verifyFormData.append('project_description', projectDescription);
                    verifyFormData.append('tech_stack', projectTechStack);
                    
                    const verifyRes = await api.post('/verify', verifyFormData, {
                        headers: { 'Content-Type': 'multipart/form-data' }
                    });
                    setVerificationResult(verifyRes.data);
                    
                    const status = verifyRes.data?.status || 'unknown';
                    const score = verifyRes.data?.confidence_score || 0;
                    if (status === 'verified') {
                        toast.success(`Project verified! Score: ${(score * 100).toFixed(0)}%`);
                    } else if (status === 'suspicious') {
                        toast.warning(`Project flagged as suspicious. Score: ${(score * 100).toFixed(0)}%`);
                    } else {
                        toast.error(`Project verification failed. Score: ${(score * 100).toFixed(0)}%`);
                    }
                } catch (verifyErr) {
                    console.error('Project verification error:', verifyErr);
                    toast.warning('Project submitted. AI Verification may take a moment.');
                } finally {
                    setVerifyingProject(false);
                }
            }

            // Reset states
            if (file) {
                setTitle('');
                setDescription('');
                setFile(null);
            }
            if (githubUrl.trim()) {
                setProjectTitle('');
                setProjectDescription('');
                setProjectTechStack('');
                setGithubUrl('');
            }
            fetchCerts();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Upload failed');
        } finally { setUploading(false); }
    };

    const handleDownloadPortfolio = async () => {
        try {
            toast.info('Generating portfolio PDF...');
            // Dynamic import to keep initial bundle size small
            const { jsPDF } = await import('jspdf');
            const autoTable = (await import('jspdf-autotable')).default;

            const doc = new jsPDF();
            const pageWidth = doc.internal.pageSize.getWidth();
            const pageHeight = doc.internal.pageSize.getHeight();

            // --- Title Page ---
            doc.setFontSize(24);
            doc.setTextColor(100, 50, 200);
            doc.text('Certificate Portfolio', pageWidth / 2, 40, { align: 'center' });

            doc.setFontSize(14);
            doc.setTextColor(50, 50, 50);
            doc.text(`Generated on: ${new Date().toLocaleDateString()}`, pageWidth / 2, 55, { align: 'center' });

            doc.text(`Total Certificates: ${certs.length}`, pageWidth / 2, 70, { align: 'center' });
            const totalPts = certs.reduce((sum, c) => sum + (c.points || 0), 0);
            doc.text(`Total Points: ${totalPts}`, pageWidth / 2, 80, { align: 'center' });

            // --- Summary Table ---
            const tableData = certs.map((c, i) => [
                i + 1,
                c.title,
                (c.description && String(c.description).trim()) ? String(c.description).trim() : 'N/A',
                c.is_verified ? 'Yes' : 'No',
                c.points || 0,
                new Date(c.uploaded_at).toLocaleDateString()
            ]);

            autoTable(doc, {
                startY: 100,
                head: [['#', 'Title', 'Description', 'Verified', 'Points', 'Date']],
                body: tableData,
                theme: 'striped',
                headStyles: { fillColor: [168, 126, 240] },
                styles: { fontSize: 10, cellPadding: 4, overflow: 'linebreak' },
                columnStyles: {
                    0: { cellWidth: 10 },
                    1: { cellWidth: 42 },
                    2: { cellWidth: 78 },
                    3: { cellWidth: 20 },
                    4: { cellWidth: 15 },
                    5: { cellWidth: 25 }
                }
            });

            const normalizeImgTypeForJsPdf = (ext) => {
                const e = (ext || '').toLowerCase();
                if (e === 'jpg') return 'JPEG';
                return e.toUpperCase();
            };

            const addImagePage = async ({ title, meta, dataUrl, imgType }) => {
                doc.addPage();

                doc.setFontSize(16);
                doc.setTextColor(50, 50, 50);
                doc.text(title, 14, 20);
                doc.setFontSize(10);
                doc.text(meta, 14, 28);

                const maxWidth = pageWidth - 28;
                const maxImgHeight = pageHeight - 50;

                const img = new Image();
                img.src = dataUrl;
                await new Promise((resolve) => { img.onload = resolve; });

                let imgWidth = img.width;
                let imgHeight = img.height;
                const ratio = imgWidth / imgHeight;

                if (imgWidth > maxWidth) {
                    imgWidth = maxWidth;
                    imgHeight = imgWidth / ratio;
                }
                if (imgHeight > maxImgHeight) {
                    imgHeight = maxImgHeight;
                    imgWidth = imgHeight * ratio;
                }

                const xOffset = (pageWidth - imgWidth) / 2;
                doc.addImage(dataUrl, imgType, xOffset, 40, imgWidth, imgHeight);
            };

            // --- Append Image Certificates ---
            for (const cert of certs) {
                const fileName = cert.file_name || '';
                const ext = fileName.split('.').pop()?.toLowerCase() || '';
                const url = `/certificates/${fileName}`;

                const meta = `Verified: ${cert.is_verified ? 'Yes' : 'No'} | Points: ${cert.points || 0}`;

                if (/(jpg|jpeg|png|webp)$/i.test(ext)) {
                    try {
                        const imgRes = await fetch(url);
                        if (!imgRes.ok) continue;
                        const blob = await imgRes.blob();
                        const dataUrl = await new Promise((resolve) => {
                            const reader = new FileReader();
                            reader.onloadend = () => resolve(reader.result);
                            reader.readAsDataURL(blob);
                        });

                        await addImagePage({
                            title: cert.title,
                            meta,
                            dataUrl,
                            imgType: normalizeImgTypeForJsPdf(ext),
                        });
                    } catch (err) {
                        console.error(`Failed to inline image ${fileName}`, err);
                    }
                }

                if (/pdf$/i.test(ext)) {
                    try {
                        const pdfRes = await fetch(url);
                        if (!pdfRes.ok) continue;
                        const pdfBytes = await pdfRes.arrayBuffer();

                        const pdfjsLib = await import('pdfjs-dist/legacy/build/pdf');
                        const workerModule = await import('pdfjs-dist/legacy/build/pdf.worker?url');
                        pdfjsLib.GlobalWorkerOptions.workerSrc = workerModule.default;

                        const pdf = await pdfjsLib.getDocument({ data: pdfBytes }).promise;
                        const maxPages = Math.min(pdf.numPages, 12);

                        for (let pageNum = 1; pageNum <= maxPages; pageNum++) {
                            const page = await pdf.getPage(pageNum);
                            const viewport = page.getViewport({ scale: 1.6 });

                            const canvas = document.createElement('canvas');
                            const ctx = canvas.getContext('2d');
                            canvas.width = Math.floor(viewport.width);
                            canvas.height = Math.floor(viewport.height);

                            await page.render({ canvasContext: ctx, viewport }).promise;
                            const dataUrl = canvas.toDataURL('image/png');

                            await addImagePage({
                                title: `${cert.title} (Page ${pageNum}/${pdf.numPages})`,
                                meta,
                                dataUrl,
                                imgType: 'PNG',
                            });
                        }

                        if (pdf.numPages > maxPages) {
                            doc.addPage();
                            doc.setFontSize(12);
                            doc.setTextColor(50, 50, 50);
                            doc.text(`${cert.title}: showing first ${maxPages} pages (of ${pdf.numPages})`, 14, 20);
                        }
                    } catch (err) {
                        console.error(`Failed to inline PDF ${fileName}`, err);
                    }
                }
            }

            // --- Download ---
            doc.save('Student_Certificate_Portfolio.pdf');
            toast.success('Portfolio downloaded successfully!');

        } catch (error) {
            console.error('Portfolio generation error:', error);
            toast.error('Failed to generate portfolio. Please try again.');
        }
    };

    const totalPoints = certs.reduce((sum, c) => sum + c.points, 0);
    const verifiedCount = certs.filter(c => c.is_verified).length;

    if (loading) return <div className="spinner" style={{ margin: '40px auto' }}></div>;

    return (
        <div className="dashboard-content fade-in">
            <div className="page-header slide-in-left">
                <h1 className="gradient-text">Certificates & Projects</h1>
                <p>Upload certificates and GitHub projects for AI-powered verification</p>
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

            {/* Upload Section — Two Side-by-Side Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '24px' }} className="fade-in-up fade-in-delay-1">

                {/* Card 1: Upload Certificate */}
                <div className="cert-upload-card">
                    <div className="cert-upload-card-header">
                        <div className="cert-upload-card-icon">
                            <FiUpload size={22} />
                        </div>
                        <div>
                            <h3>Upload Certificate</h3>
                            <p>Add certifications to build your profile</p>
                        </div>
                    </div>

                    <form onSubmit={handleUpload} className="cert-upload-form-inner">
                        {/* Drop Zone */}
                        <label htmlFor="cert-file" className={`cert-drop-zone ${file ? 'cert-drop-zone-active' : ''}`}>
                            <input
                                type="file"
                                id="cert-file"
                                className="file-input-hidden"
                                onChange={e => setFile(e.target.files[0])}
                                accept=".pdf,.jpg,.jpeg,.png,.webp"
                            />
                            {file ? (
                                <div className="cert-file-preview">
                                    <div className="cert-file-icon-done">
                                        <FiCheckCircle size={28} />
                                    </div>
                                    <span className="cert-file-name">{file.name}</span>
                                    <span className="cert-file-size">
                                        {(file.size / 1024).toFixed(1)} KB
                                    </span>
                                    <span className="cert-file-change">Click to change file</span>
                                </div>
                            ) : (
                                <div className="cert-drop-content">
                                    <div className="cert-drop-icon-ring">
                                        <FiUpload size={24} />
                                    </div>
                                    <span className="cert-drop-title">Drop file here or click</span>
                                    <div className="cert-drop-types">
                                        <span className="cert-type-badge">PDF</span>
                                        <span className="cert-type-badge">JPG</span>
                                        <span className="cert-type-badge">PNG</span>
                                    </div>
                                </div>
                            )}
                        </label>

                        {/* Title + Description */}
                        <div className="cert-upload-fields">
                            <div className="cert-upload-field">
                                <label>Certificate Title {file ? '*' : ''}</label>
                                <div className="cert-title-input-wrap">
                                    <FiAward className="cert-title-icon" />
                                    <input
                                        type="text"
                                        value={title}
                                        onChange={e => setTitle(e.target.value)}
                                        placeholder="e.g. AWS Cloud Certification"
                                    />
                                </div>
                            </div>

                            <div className="cert-upload-field">
                                <label>Description (Optional)</label>
                                <div className="cert-title-input-wrap">
                                    <textarea
                                        value={description}
                                        onChange={e => setDescription(e.target.value)}
                                        placeholder="Briefly describe..."
                                        rows="2"
                                        style={{
                                            width: '100%',
                                            padding: '10px 14px',
                                            border: '1px solid var(--color-border)',
                                            borderRadius: 'var(--radius-sm)',
                                            background: 'var(--color-bg-main)',
                                            color: 'var(--color-text-primary)',
                                            fontFamily: 'var(--font-body)',
                                            fontSize: '0.85rem',
                                            resize: 'vertical',
                                            transition: 'border-color 0.2s ease, box-shadow 0.2s ease'
                                        }}
                                    />
                                </div>
                            </div>
                        </div>

                        {/* Only show submit if this card has content OR github card has content */}
                        {(file || githubUrl.trim()) && (
                            <button
                                type="submit"
                                className="cert-upload-btn"
                                disabled={uploading || verifyingProject}
                                style={{ marginTop: '12px' }}
                            >
                                {uploading || verifyingProject ? (
                                    <>
                                        <div className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }}></div>
                                        {verifyingProject ? 'Verifying...' : 'Uploading...'}
                                    </>
                                ) : (
                                    <>
                                        <FiUpload size={16} />
                                        Submit
                                    </>
                                )}
                            </button>
                        )}
                    </form>
                </div>

                {/* Card 2: Upload GitHub Project */}
                <div className="cert-upload-card">
                    <div className="cert-upload-card-header">
                        <div className="cert-upload-card-icon" style={{ background: 'linear-gradient(135deg, #24292e, #586069)' }}>
                            <FiGithub size={22} />
                        </div>
                        <div>
                            <h3>Upload Project</h3>
                            <p>Add GitHub project for AI verification</p>
                        </div>
                    </div>

                    <div className="cert-upload-form-inner">
                        <div className="cert-upload-fields">
                            <div className="cert-upload-field">
                                <label>Project Name *</label>
                                <div className="cert-title-input-wrap">
                                    <FiCode className="cert-title-icon" />
                                    <input
                                        type="text"
                                        value={projectTitle}
                                        onChange={e => setProjectTitle(e.target.value)}
                                        placeholder="e.g. E-Commerce Backend"
                                    />
                                </div>
                            </div>

                            <div className="cert-upload-field">
                                <label>Description (Optional)</label>
                                <div className="cert-title-input-wrap">
                                    <textarea
                                        value={projectDescription}
                                        onChange={e => setProjectDescription(e.target.value)}
                                        placeholder="Briefly describe the project..."
                                        rows="2"
                                        style={{
                                            width: '100%',
                                            padding: '10px 14px',
                                            border: '1px solid var(--color-border)',
                                            borderRadius: 'var(--radius-sm)',
                                            background: 'var(--color-bg-main)',
                                            color: 'var(--color-text-primary)',
                                            fontFamily: 'var(--font-body)',
                                            fontSize: '0.85rem',
                                            resize: 'vertical',
                                            transition: 'border-color 0.2s ease, box-shadow 0.2s ease'
                                        }}
                                    />
                                </div>
                            </div>

                            <div className="cert-upload-field">
                                <label>GitHub Repository URL *</label>
                                <div className="cert-title-input-wrap">
                                    <FiGithub className="cert-title-icon" />
                                    <input
                                        type="url"
                                        value={githubUrl}
                                        onChange={e => {
                                            setGithubUrl(e.target.value);
                                            setVerificationResult(null);
                                        }}
                                        placeholder="https://github.com/user/project"
                                    />
                                </div>
                                {githubUrl && !isValidGithubUrl(githubUrl) && (
                                    <p style={{ color: 'var(--color-danger)', fontSize: '0.8rem', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                        <FiAlertCircle size={12} /> Must be a valid GitHub repository URL
                                    </p>
                                )}
                            </div>

                            <div className="cert-upload-field">
                                <label>Tech Stack (Optional)</label>
                                <div className="cert-title-input-wrap">
                                    <FiCode className="cert-title-icon" />
                                    <input
                                        type="text"
                                        value={projectTechStack}
                                        onChange={e => setProjectTechStack(e.target.value)}
                                        placeholder="e.g. React, Node.js, PostgreSQL"
                                    />
                                </div>
                            </div>
                        </div>

                        {/* Verification Result Card */}
                        {verificationResult && (
                            <div style={{
                                margin: '12px 0',
                                padding: '14px 16px',
                                borderRadius: 'var(--radius-sm)',
                                border: `1px solid ${verificationResult.status === 'verified' ? 'var(--color-success)' : verificationResult.status === 'suspicious' ? 'var(--color-warning)' : 'var(--color-danger)'}`,
                                background: 'var(--color-bg-main)',
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                                    <span style={{
                                        display: 'inline-flex', alignItems: 'center', gap: '4px',
                                        padding: '3px 10px', borderRadius: '20px', fontSize: '0.78rem', fontWeight: 600,
                                        background: verificationResult.status === 'verified' ? 'rgba(16,185,129,0.15)' : verificationResult.status === 'suspicious' ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.15)',
                                        color: verificationResult.status === 'verified' ? 'var(--color-success)' : verificationResult.status === 'suspicious' ? 'var(--color-warning)' : 'var(--color-danger)',
                                    }}>
                                        {verificationResult.status === 'verified' ? '✓ Verified' : verificationResult.status === 'suspicious' ? '⚠ Suspicious' : '✗ Failed'}
                                    </span>
                                    <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                                        Score: {(verificationResult.confidence_score * 100).toFixed(0)}% | Trust: {verificationResult.trust_score}
                                    </span>
                                </div>
                                {verificationResult.issues?.length > 0 && (
                                    <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                                        {verificationResult.issues.slice(0, 3).map((issue, i) => (
                                            <li key={i}>{issue}</li>
                                        ))}
                                    </ul>
                                )}
                                {verificationResult.recommendations?.length > 0 && (
                                    <div style={{ marginTop: '6px', fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>
                                        <strong>Tip:</strong> {verificationResult.recommendations[0]}
                                    </div>
                                )}
                            </div>
                        )}

                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 0', fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>
                            <FiCode size={12} />
                            <span>AI verifies repo existence, tech stack, and project authenticity</span>
                        </div>

                        {/* Submit button for Project Card */}
                        {(githubUrl.trim()) && (
                            <button
                                type="button"
                                className="cert-upload-btn"
                                onClick={handleUpload}
                                disabled={uploading || verifyingProject}
                                style={{ marginTop: '12px' }}
                            >
                                {uploading || verifyingProject ? (
                                    <>
                                        <div className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }}></div>
                                        {verifyingProject ? 'Verifying...' : 'Uploading...'}
                                    </>
                                ) : (
                                    <>
                                        <FiUpload size={16} />
                                        Submit Project
                                    </>
                                )}
                            </button>
                        )}
                    </div>
                </div>
            </div>

            {/* Certificates List Header & Portfolio Button */}
            <div className="data-table-header fade-in-up fade-in-delay-2" style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ margin: 0 }}>My Certificates <span className="table-count">({certs.length})</span></h3>
                {certs.length > 0 && (
                    <button
                        className="btn btn-secondary btn-sm"
                        onClick={handleDownloadPortfolio}
                        style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
                    >
                        <FiFile />
                        Download Portfolio
                    </button>
                )}
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

            {/* Projects List Header */}
            <div className="data-table-header fade-in-up fade-in-delay-3" style={{ marginTop: '32px', marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ margin: 0 }}>My Projects <span className="table-count">({projects.length})</span></h3>
            </div>

            {/* Projects List */}
            <div className="cert-grid fade-in-up fade-in-delay-3">
                {projects.length === 0 ? (
                    <div className="empty-state">
                        <FiCode className="empty-state-icon" />
                        <h3>No Projects Yet</h3>
                        <p>Upload your first GitHub project to get started.</p>
                    </div>
                ) : (
                    projects.map((p, i) => (
                        <div 
                            key={p.id} 
                            className="cert-card" 
                            style={{ animationDelay: `${i * 0.05}s`, cursor: 'pointer' }}
                            onClick={() => setSelectedProject(p)}
                        >
                            <div className="cert-card-icon" style={{ background: 'linear-gradient(135deg, #24292e, #586069)' }}>
                                <FiGithub />
                            </div>
                            <div className="cert-card-body">
                                <h4>{p.project_name}</h4>
                                <div className="cert-card-meta">
                                    <span className={`status-badge ${p.verification_status === 'verified' ? 'status-badge-approved' : p.verification_status === 'suspicious' ? 'status-badge-pending' : 'status-badge-rejected'}`} style={{
                                        background: p.verification_status === 'suspicious' ? 'rgba(245,158,11,0.15)' : p.verification_status === 'rejected' ? 'rgba(239,68,68,0.15)' : undefined,
                                        color: p.verification_status === 'suspicious' ? 'var(--color-warning)' : p.verification_status === 'rejected' ? 'var(--color-danger)' : undefined
                                    }}>
                                        {p.verification_status === 'verified' ? '✓ Verified' : p.verification_status === 'suspicious' ? '⚠ Suspicious' : p.verification_status === 'rejected' ? '✗ Failed' : '⏳ Pending'}
                                    </span>
                                </div>
                                <a href={p.github_url} target="_blank" rel="noopener noreferrer"
                                    className="cert-view-link">View Repository →</a>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Project Details Modal */}
            {selectedProject && (
                <div style={{
                    position: 'fixed',
                    top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.5)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 1000,
                    padding: '20px'
                }} onClick={() => setSelectedProject(null)} className="fade-in">
                    <div style={{
                        background: 'var(--color-bg-base)',
                        borderRadius: '16px',
                        padding: '30px',
                        maxWidth: '500px',
                        width: '100%',
                        boxShadow: '0 20px 40px rgba(0,0,0,0.2)',
                        border: '1px solid var(--color-border)',
                        position: 'relative'
                    }} onClick={e => e.stopPropagation()}>
                        <button 
                            onClick={() => setSelectedProject(null)}
                            style={{
                                position: 'absolute', top: '16px', right: '16px',
                                background: 'transparent', border: 'none',
                                color: 'var(--color-text-muted)', cursor: 'pointer',
                                padding: '4px', display: 'flex'
                            }}
                        >
                            <FiX size={20} />
                        </button>
                        
                        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '20px' }}>
                            <div className="cert-card-icon" style={{ 
                                background: 'linear-gradient(135deg, #24292e, #586069)', 
                                margin: 0, width: '48px', height: '48px',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                borderRadius: '12px', color: 'white'
                            }}>
                                <FiGithub size={24} />
                            </div>
                            <div>
                                <h2 style={{ margin: 0, fontSize: '1.4rem' }}>{selectedProject.project_name}</h2>
                                <span className={`status-badge ${selectedProject.verification_status === 'verified' ? 'status-badge-approved' : selectedProject.verification_status === 'suspicious' ? 'status-badge-pending' : 'status-badge-rejected'}`} style={{
                                    background: selectedProject.verification_status === 'suspicious' ? 'rgba(245,158,11,0.15)' : selectedProject.verification_status === 'rejected' ? 'rgba(239,68,68,0.15)' : undefined,
                                    color: selectedProject.verification_status === 'suspicious' ? 'var(--color-warning)' : selectedProject.verification_status === 'rejected' ? 'var(--color-danger)' : undefined,
                                    marginTop: '6px', display: 'inline-flex'
                                }}>
                                    {selectedProject.verification_status === 'verified' ? '✓ Verified' : selectedProject.verification_status === 'suspicious' ? '⚠ Suspicious' : selectedProject.verification_status === 'rejected' ? '✗ Failed' : '⏳ Pending'}
                                </span>
                            </div>
                        </div>

                        {selectedProject.description && (
                            <div style={{ marginBottom: '20px' }}>
                                <h4 style={{ margin: '0 0 8px 0', color: 'var(--color-text-secondary)', fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Description</h4>
                                <p style={{ margin: 0, fontSize: '0.95rem', lineHeight: 1.5, color: 'var(--color-text-primary)' }}>
                                    {selectedProject.description}
                                </p>
                            </div>
                        )}

                        {selectedProject.tech_stack && (
                            <div style={{ marginBottom: '24px' }}>
                                <h4 style={{ margin: '0 0 8px 0', color: 'var(--color-text-secondary)', fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Tech Stack</h4>
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                                    {selectedProject.tech_stack.split(',').map((tech, idx) => (
                                        <span key={idx} style={{
                                            background: 'var(--color-bg-main)',
                                            border: '1px solid var(--color-border)',
                                            padding: '4px 10px',
                                            borderRadius: '20px',
                                            fontSize: '0.85rem',
                                            color: 'var(--color-text-primary)'
                                        }}>
                                            {tech.trim()}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}

                        <a 
                            href={selectedProject.github_url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="btn btn-primary"
                            style={{ width: '100%', display: 'flex', justifyContent: 'center', gap: '8px', padding: '12px' }}
                        >
                            <FiGithub />
                            Open Repository
                        </a>
                    </div>
                </div>
            )}
        </div>
    );
}
