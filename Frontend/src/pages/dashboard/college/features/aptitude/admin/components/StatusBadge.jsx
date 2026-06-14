const LABELS = {
    draft: 'Draft',
    approved: 'Approved',
    archived: 'Archived',
    deleted: 'Deleted',
    easy: 'Easy',
    medium: 'Medium',
    hard: 'Hard',
    pending: 'Pending',
    completed: 'Completed',
    failed: 'Failed',
    valid: 'Valid',
    invalid: 'Invalid',
    imported: 'Imported',
};

export default function StatusBadge({ value }) {
    const normalized = String(value || 'draft').toLowerCase();
    return (
        <span className={`apt-badge apt-badge-${normalized}`}>
            {LABELS[normalized] || normalized.replaceAll('_', ' ')}
        </span>
    );
}
