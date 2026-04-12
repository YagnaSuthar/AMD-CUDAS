import { FiX, FiCode, FiGithub, FiCheckCircle, FiClock, FiAlertTriangle, FiXCircle } from 'react-icons/fi';

export default function ProjectPopup({ project, onClose, onDelete }) {
    if (!project) return null;

    const p = project;

    const getStatusInfo = () => {
        switch (p.verification_status) {
            case 'verified':
                return { label: '✓ Verified', cls: 'status-badge-approved', Icon: FiCheckCircle };
            case 'failed':
                return { label: '✗ Failed', cls: 'status-badge-rejected', Icon: FiXCircle };
            case 'suspicious':
                return { label: '⚠ Suspicious', cls: 'status-badge-pending', Icon: FiAlertTriangle };
            default:
                return { label: '⏳ Pending', cls: 'status-badge-pending', Icon: FiClock };
        }
    };

    const status = getStatusInfo();

    return (
        <div className="popup-overlay" onClick={onClose}>
            <div className="popup-card" onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div className="popup-header">
                    <div className="popup-header-left">
                        <div className="popup-icon-wrap popup-icon-project">
                            <FiCode size={20} />
                        </div>
                        <h3>Project Details</h3>
                    </div>
                    <button className="popup-close" onClick={onClose} title="Close">
                        <FiX size={20} />
                    </button>
                </div>

                {/* Body */}
                <div className="popup-body">
                    {/* Project Name */}
                    <div className="popup-field">
                        <label>Project Name</label>
                        <p className="popup-field-value">{p.project_name}</p>
                    </div>

                    {/* Description */}
                    {p.description && (
                        <div className="popup-field">
                            <label>Description</label>
                            <p className="popup-field-value popup-desc">{p.description}</p>
                        </div>
                    )}

                    {/* Tech Stack */}
                    {p.tech_stack && (
                        <div className="popup-field">
                            <label>Tech Stack</label>
                            <div className="popup-tech-tags">
                                {p.tech_stack.split(',').map((t, i) => (
                                    <span key={i} className="popup-tech-tag">{t.trim()}</span>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* GitHub Link */}
                    {p.github_url && (
                        <div className="popup-field">
                            <label>GitHub Repository</label>
                            <a
                                href={p.github_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="popup-github-link"
                            >
                                <FiGithub size={16} />
                                {p.github_url}
                            </a>
                        </div>
                    )}

                    {/* Status + Score */}
                    <div className="popup-meta-row">
                        <div className="popup-meta-item">
                            <span className={`status-badge ${status.cls}`}>
                                {status.label}
                            </span>
                        </div>
                        {p.verification_score != null && (
                            <div className="popup-meta-item">
                                <span className="popup-score" style={{
                                    color: p.verification_score >= 0.7 ? 'var(--color-success)' :
                                           p.verification_score >= 0.4 ? 'var(--color-warning)' :
                                           'var(--color-error)'
                                }}>
                                    Score: {Math.round(p.verification_score * 100)}%
                                </span>
                            </div>
                        )}
                    </div>

                    {/* Verification Details */}
                    {p.verification_details && (
                        <div className="popup-field">
                            <label>Verification Details</label>
                            <p className="popup-field-value popup-desc">{p.verification_details}</p>
                        </div>
                    )}
                </div>

                {/* Footer */}
                {onDelete && (
                    <div className="popup-footer">
                        <button className="popup-delete-btn" onClick={() => { onDelete(p.id); onClose(); }}>
                            Delete Project
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
