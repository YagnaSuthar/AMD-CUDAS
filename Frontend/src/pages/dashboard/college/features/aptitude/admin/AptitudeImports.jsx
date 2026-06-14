import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { FiUploadCloud, FiFileText, FiCheckCircle, FiAlertCircle } from 'react-icons/fi';
import { uploadImportFile } from '../../../../../../utils/aptitudeAdminApi';
import '../../../../../../style/aptitudeAdmin.css';

const ACCEPTED_FORMATS = ['json', 'csv', 'xlsx', 'pdf'];

export default function AptitudeImports() {
    const navigate = useNavigate();
    const fileInputRef = useRef(null);

    const [dragging, setDragging] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [progress, setProgress] = useState(0);

    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragging(true);
        } else if (e.type === 'dragleave') {
            setDragging(false);
        }
    };

    const handleDrop = async (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragging(false);

        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            await handleFile(e.dataTransfer.files[0]);
        }
    };

    const handleFileChange = async (e) => {
        if (e.target.files && e.target.files[0]) {
            await handleFile(e.target.files[0]);
        }
    };

    const handleFile = async (file) => {
        const ext = file.name.split('.').pop().toLowerCase();
        if (!ACCEPTED_FORMATS.includes(ext)) {
            toast.error(`Invalid file format. Only .${ACCEPTED_FORMATS.join(', .')} are supported.`);
            return;
        }

        setUploading(true);
        setProgress(10);

        // Simulate upload progress
        const interval = setInterval(() => {
            setProgress((p) => (p >= 80 ? p : p + 10));
        }, 150);

        try {
            const data = await uploadImportFile(file);
            clearInterval(interval);
            setProgress(100);
            toast.success('File uploaded and analyzed successfully!');
            setTimeout(() => {
                navigate(`/dashboard/admin/aptitude/imports/${data.id}`);
            }, 500);
        } catch (err) {
            clearInterval(interval);
            setUploading(false);
            setProgress(0);
            toast.error(err.response?.data?.detail || 'Failed to upload file');
        }
    };

    return (
        <div className="apt-admin-page">
            <div className="apt-page-header">
                <h1 className="gradient-text">Import Center</h1>
                <p>Bulk import question banks using multiple file formats.</p>
            </div>

            <div className="apt-form-card" style={{ padding: '40px' }}>
                <div
                    className={`apt-dropzone ${dragging ? 'drag-active' : ''}`}
                    onDragEnter={handleDrag}
                    onDragOver={handleDrag}
                    onDragLeave={handleDrag}
                    onDrop={handleDrop}
                    onClick={() => !uploading && fileInputRef.current?.click()}
                >
                    <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleFileChange}
                        accept=".json,.csv,.xlsx,.pdf"
                        style={{ display: 'none' }}
                        disabled={uploading}
                    />

                    <FiUploadCloud />
                    <h3>{uploading ? 'Processing File...' : 'Drag & Drop Question Bank File'}</h3>
                    <p>Or click to browse your local files</p>

                    <div className="formats">
                        {ACCEPTED_FORMATS.map((f) => <span key={f}>{f}</span>)}
                    </div>
                </div>

                {uploading && (
                    <div className="apt-upload-progress">
                        <div className="progress-bar">
                            <div className="progress-fill" style={{ width: `${progress}%` }}></div>
                        </div>
                        <span style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
                            Parsing question dataset... {progress}%
                        </span>
                    </div>
                )}

                <div style={{ marginTop: '36px' }}>
                    <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '14px' }}>
                        Import Formatting Specifications
                    </h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
                            <FiCheckCircle style={{ color: 'var(--color-success)', marginTop: '3px', flexShrink: 0 }} />
                            <span><strong>Supported Columns / Fields:</strong> <code>question</code>, <code>option_a</code>, <code>option_b</code>, <code>option_c</code>, <code>option_d</code>, <code>correct_answer</code> (must match one of options), <code>category</code>, <code>difficulty</code> (easy, medium, hard).</span>
                        </div>
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
                            <FiCheckCircle style={{ color: 'var(--color-success)', marginTop: '3px', flexShrink: 0 }} />
                            <span><strong>SHA-256 Duplication Filter:</strong> Duplicate questions with matching content (ignoring spaces/caps) will be automatically detected and flagged as duplicates to avoid polluting the database.</span>
                        </div>
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
                            <FiAlertCircle style={{ color: 'var(--color-warning)', marginTop: '3px', flexShrink: 0 }} />
                            <span><strong>PDF Scanning:</strong> For PDF files, the system parses text structure automatically. Review parsed questions in the next stage to fix minor text adjustments.</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
