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
    const [description, setDescription] = useState('');
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
            if (description) formData.append('description', description);
            formData.append('file', file);
            await api.post('/college/student/certificates', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            toast.success('Certificate uploaded successfully');
            setTitle('');
            setDescription('');
            setFile(null);
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

            {/* Upload Form — Premium Design */}
            <div className="cert-upload-card fade-in-up fade-in-delay-1">
                <div className="cert-upload-card-header">
                    <div className="cert-upload-card-icon">
                        <FiUpload size={22} />
                    </div>
                    <div>
                        <h3>Upload Certificate</h3>
                        <p>Add your certifications to build your profile</p>
                    </div>
                </div>

                <form onSubmit={handleUpload} className="cert-upload-form-inner">
                    <div className="cert-upload-grid">
                        {/* Left — Drop Zone */}
                        <label htmlFor="cert-file" className={`cert-drop-zone ${file ? 'cert-drop-zone-active' : ''}`}>
                            <input
                                type="file"
                                id="cert-file"
                                className="file-input-hidden"
                                onChange={e => setFile(e.target.files[0])}
                                accept=".pdf,.jpg,.jpeg,.png,.webp"
                                required
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
                                    <span className="cert-drop-title">Drop file here or click to browse</span>
                                    <div className="cert-drop-types">
                                        <span className="cert-type-badge">PDF</span>
                                        <span className="cert-type-badge">JPG</span>
                                        <span className="cert-type-badge">PNG</span>
                                        <span className="cert-type-badge">WEBP</span>
                                    </div>
                                </div>
                            )}
                        </label>

                        {/* Right — Title + Submit */}
                        <div className="cert-upload-fields">
                            <div className="cert-upload-field">
                                <label>Certificate Title *</label>
                                <div className="cert-title-input-wrap">
                                    <FiAward className="cert-title-icon" />
                                    <input
                                        type="text"
                                        value={title}
                                        onChange={e => setTitle(e.target.value)}
                                        placeholder="e.g. AWS Cloud Certification"
                                        required
                                    />
                                </div>
                            </div>

                            <div className="cert-upload-field">
                                <label>Description (Optional)</label>
                                <div className="cert-title-input-wrap">
                                    <textarea
                                        value={description}
                                        onChange={e => setDescription(e.target.value)}
                                        placeholder="Briefly describe what you learned..."
                                        rows="3"
                                        style={{
                                            width: '100%',
                                            padding: '12px 14px',
                                            border: '1px solid var(--color-border)',
                                            borderRadius: 'var(--radius-sm)',
                                            background: 'var(--color-bg-main)',
                                            color: 'var(--color-text-primary)',
                                            fontFamily: 'var(--font-body)',
                                            fontSize: '0.9rem',
                                            resize: 'vertical',
                                            transition: 'border-color 0.2s ease, box-shadow 0.2s ease'
                                        }}
                                    />
                                </div>
                            </div>

                            <button
                                type="submit"
                                className="cert-upload-btn"
                                disabled={uploading || !title || !file}
                            >
                                {uploading ? (
                                    <>
                                        <div className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }}></div>
                                        Uploading...
                                    </>
                                ) : (
                                    <>
                                        <FiUpload size={16} />
                                        Upload Certificate
                                    </>
                                )}
                            </button>

                            <p className="cert-upload-hint">
                                <FiCheckCircle size={12} />
                                Certificates are verified by your college faculty
                            </p>
                        </div>
                    </div>
                </form>
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
        </div>
    );
}
