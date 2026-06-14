import { FiAlertCircle, FiCheckCircle, FiFileText } from 'react-icons/fi';
import StatusBadge from './StatusBadge';

export default function ImportSummaryCard({ job }) {
    if (!job) return null;

    return (
        <div className="apt-summary-grid">
            <div className="apt-stat-card">
                <span className="stat-icon blue"><FiFileText /></span>
                <span className="stat-label">File</span>
                <span className="stat-value apt-stat-text">{job.filename}</span>
            </div>
            <div className="apt-stat-card">
                <span className="stat-icon green"><FiCheckCircle /></span>
                <span className="stat-label">Valid Questions</span>
                <span className="stat-value">{job.valid_questions || 0}</span>
            </div>
            <div className="apt-stat-card">
                <span className="stat-icon red"><FiAlertCircle /></span>
                <span className="stat-label">Invalid Questions</span>
                <span className="stat-value">{job.invalid_questions || 0}</span>
            </div>
            <div className="apt-stat-card">
                <span className="stat-label">Status</span>
                <StatusBadge value={job.status} />
                <span className="apt-muted">{job.source_type}</span>
            </div>
        </div>
    );
}
