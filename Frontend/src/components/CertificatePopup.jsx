import { FiX, FiAward, FiCheckCircle, FiClock, FiFile } from 'react-icons/fi';

export default function CertificatePopup({ cert, onClose }) {
    if (!cert) return null;

    const fileName = cert.file_name || '';
    const ext = fileName.split('.').pop()?.toLowerCase() || '';
    const isImage = ['jpg', 'jpeg', 'png', 'webp'].includes(ext);
    const isPDF = ext === 'pdf';
    const fileUrl = `/certificates/${fileName}`;

    return (
        <div className="popup-overlay" onClick={onClose}>
            <div className="popup-card" onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div className="popup-header">
                    <div className="popup-header-left">
                        <div className="popup-icon-wrap">
                            <FiAward size={20} />
                        </div>
                        <h3>Certificate Details</h3>
                    </div>
                    <button className="popup-close" onClick={onClose} title="Close">
                        <FiX size={20} />
                    </button>
                </div>

                {/* Body */}
                <div className="popup-body">
                    {/* Title */}
                    <div className="popup-field">
                        <label>Certificate Title</label>
                        <p className="popup-field-value">{cert.title}</p>
                    </div>

                    {/* Description */}
                    {cert.description && (
                        <div className="popup-field">
                            <label>Description</label>
                            <p className="popup-field-value popup-desc">{cert.description}</p>
                        </div>
                    )}

                    {/* Meta row */}
                    <div className="popup-meta-row">
                        <div className="popup-meta-item">
                            <span className={`status-badge ${cert.is_verified ? 'status-badge-approved' : 'status-badge-pending'}`}>
                                {cert.is_verified ? (
                                    <><FiCheckCircle size={12} style={{ marginRight: 4 }} /> Verified</>
                                ) : (
                                    <><FiClock size={12} style={{ marginRight: 4 }} /> Pending</>
                                )}
                            </span>
                        </div>
                        {cert.points > 0 && (
                            <div className="popup-meta-item">
                                <span className="cert-points">+{cert.points} pts</span>
                            </div>
                        )}
                        {cert.uploaded_at && (
                            <div className="popup-meta-item">
                                <span className="popup-date">
                                    <FiClock size={12} />
                                    {new Date(cert.uploaded_at).toLocaleDateString('en-US', {
                                        month: 'short', day: 'numeric', year: 'numeric'
                                    })}
                                </span>
                            </div>
                        )}
                    </div>

                    {/* File Preview */}
                    <div className="popup-preview-section">
                        <label>File Preview</label>
                        {isImage ? (
                            <div className="popup-image-wrap">
                                <img src={fileUrl} alt={cert.title} />
                            </div>
                        ) : isPDF ? (
                            <div className="popup-pdf-wrap">
                                <iframe
                                    src={fileUrl}
                                    title={cert.title}
                                    className="popup-pdf-iframe"
                                />
                            </div>
                        ) : (
                            <div className="popup-no-preview">
                                <FiFile size={32} />
                                <p>Preview not available for this file type.</p>
                                <a href={fileUrl} target="_blank" rel="noopener noreferrer" className="popup-download-link">
                                    Open File →
                                </a>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
