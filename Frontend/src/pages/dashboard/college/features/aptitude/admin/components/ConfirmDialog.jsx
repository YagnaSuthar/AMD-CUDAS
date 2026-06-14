import { FiX } from 'react-icons/fi';

export default function ConfirmDialog({
    open,
    title = 'Confirm Action',
    message,
    confirmLabel = 'Confirm',
    danger = false,
    loading = false,
    onCancel,
    onConfirm,
}) {
    if (!open) return null;

    return (
        <div className="apt-modal-overlay" onClick={onCancel}>
            <div className="apt-modal" onClick={(event) => event.stopPropagation()}>
                <div className="apt-modal-header">
                    <h3>{title}</h3>
                    <button className="apt-action-btn" type="button" onClick={onCancel} aria-label="Close">
                        <FiX />
                    </button>
                </div>
                <div className="apt-modal-body">
                    <p>{message}</p>
                </div>
                <div className="apt-modal-footer">
                    <button className="btn btn-secondary apt-btn-sm" type="button" onClick={onCancel} disabled={loading}>
                        Cancel
                    </button>
                    <button
                        className={`btn ${danger ? 'apt-btn-danger' : 'btn-primary'} apt-btn-sm`}
                        type="button"
                        onClick={onConfirm}
                        disabled={loading}
                    >
                        {loading ? 'Working...' : confirmLabel}
                    </button>
                </div>
            </div>
        </div>
    );
}
