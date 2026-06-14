import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { FiArrowLeft, FiCheck, FiX, FiInfo, FiAlertTriangle } from 'react-icons/fi';
import { fetchImportJob, confirmImport } from '../../../../../../utils/aptitudeAdminApi';
import SkeletonCard from '../../../../../../components/common/skeleton/SkeletonCard';
import '../../../../../../style/aptitudeAdmin.css';

export default function AptitudeImportReview() {
    const { jobId } = useParams();
    const navigate = useNavigate();

    const [job, setJob] = useState(null);
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [confirming, setConfirming] = useState(false);
    const [showConfirmModal, setShowConfirmModal] = useState(false);

    // Filters for display
    const [activeTab, setActiveTab] = useState('all'); // 'all', 'valid', 'invalid'

    useEffect(() => {
        loadJobDetails();
    }, [jobId]);

    const loadJobDetails = async () => {
        setLoading(true);
        try {
            const data = await fetchImportJob(jobId);
            setJob(data.job);
            setItems(data.items || []);
        } catch {
            toast.error('Failed to load import job details');
            navigate('/dashboard/admin/aptitude/imports');
        } finally {
            setLoading(false);
        }
    };

    const handleConfirmImport = async () => {
        setConfirming(true);
        try {
            const res = await confirmImport(jobId);
            toast.success(`Import complete! Inserted ${res.inserted_questions} questions, skipped ${res.skipped_duplicates} duplicates.`);
            navigate('/dashboard/admin/aptitude/questions');
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to confirm import');
        } finally {
            setConfirming(false);
            setShowConfirmModal(false);
        }
    };

    const filteredItems = items.filter((item) => {
        if (activeTab === 'valid') return item.status === 'valid';
        if (activeTab === 'invalid') return item.status === 'invalid';
        return true;
    });

    if (loading) {
        return (
            <div className="apt-admin-page">
                <div className="apt-page-header"><h1 className="gradient-text">Analyzing Import Dataset...</h1></div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                    <SkeletonCard style={{ height: '300px' }} />
                    <SkeletonCard style={{ height: '300px' }} />
                </div>
            </div>
        );
    }

    const totalValid = items.filter((i) => i.status === 'valid').length;
    const totalInvalid = items.filter((i) => i.status === 'invalid').length;

    return (
        <div className="apt-admin-page">
            <div className="apt-page-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <button className="apt-action-btn" onClick={() => navigate('/dashboard/admin/aptitude/imports')}>
                        <FiArrowLeft />
                    </button>
                    <div>
                        <h1 className="gradient-text">Review Import Batch</h1>
                        <p>File: <code>{job.filename}</code> • Parsed using {job.source_type} parser</p>
                    </div>
                </div>
            </div>

            {/* Summary Cards */}
            <div className="apt-stats-row">
                <div className="apt-stat-card">
                    <div className="stat-label">Total Extracted</div>
                    <div className="stat-value">{items.length}</div>
                </div>
                <div className="apt-stat-card">
                    <div className="stat-label">Valid Questions</div>
                    <div className="stat-value" style={{ color: 'var(--color-success)' }}>{totalValid}</div>
                </div>
                <div className="apt-stat-card">
                    <div className="stat-label">Failed Validation</div>
                    <div className="stat-value" style={{ color: 'var(--color-error)' }}>{totalInvalid}</div>
                </div>
            </div>

            {/* Selection Tabs */}
            <div className="apt-toolbar">
                <button
                    className={`btn ${activeTab === 'all' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ padding: '8px 16px', fontSize: '0.82rem' }}
                    onClick={() => setActiveTab('all')}
                >
                    All Items ({items.length})
                </button>
                <button
                    className={`btn ${activeTab === 'valid' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ padding: '8px 16px', fontSize: '0.82rem' }}
                    onClick={() => setActiveTab('valid')}
                >
                    Valid Previews ({totalValid})
                </button>
                <button
                    className={`btn ${activeTab === 'invalid' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ padding: '8px 16px', fontSize: '0.82rem' }}
                    onClick={() => setActiveTab('invalid')}
                >
                    Invalid Previews ({totalInvalid})
                </button>

                <div className="apt-toolbar-spacer" />

                <button
                    className="btn btn-secondary"
                    style={{ padding: '8px 16px', fontSize: '0.82rem' }}
                    onClick={() => navigate('/dashboard/admin/aptitude/imports')}
                >
                    <FiX /> Cancel Import
                </button>
                <button
                    className="btn btn-primary"
                    style={{ padding: '8px 18px', fontSize: '0.85rem' }}
                    disabled={totalValid === 0}
                    onClick={() => setShowConfirmModal(true)}
                >
                    <FiCheck /> Approve Import
                </button>
            </div>

            {/* List of Preview Cards */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '16px' }}>
                {filteredItems.length === 0 ? (
                    <div className="apt-empty-state" style={{ background: 'var(--color-bg-card)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)' }}>
                        <FiInfo />
                        <h3>No items in this filter</h3>
                        <p>Try toggling other preview filters above.</p>
                    </div>
                ) : (
                    filteredItems.map((item) => {
                        const parsed = item.parsed_question || {};
                        const raw = item.raw_data || {};
                        const questionText = parsed.question || raw.question || '—';
                        const options = parsed.options || raw.options || [];
                        const correct = parsed.correct_answer || raw.correct_answer || '—';

                        return (
                            <div key={item.id} className={`apt-import-card ${item.status === 'invalid' ? 'invalid' : 'valid'}`}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
                                    <div className="card-question">{questionText}</div>
                                    <span className={`apt-badge apt-badge-${item.status === 'valid' ? 'valid' : 'invalid'}`}>
                                        {item.status}
                                    </span>
                                </div>

                                <div className="card-meta">
                                    <span>Domain: <strong>{parsed.domain || '—'}</strong></span>
                                    <span>Category: <strong>{parsed.category || '—'}</strong></span>
                                    <span>Difficulty: <strong>{parsed.difficulty || '—'}</strong></span>
                                </div>

                                {options.length > 0 && (
                                    <div className="card-options">
                                        {options.map((opt, idx) => (
                                            <div key={idx} className={`option-item ${opt === correct ? 'correct' : ''}`}>
                                                {String.fromCharCode(65 + idx)}. {opt}
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {parsed.explanation && (
                                    <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', background: 'var(--color-bg-main)', padding: '6px 12px', borderRadius: '4px', marginTop: '6px' }}>
                                        <strong>Explanation:</strong> {parsed.explanation}
                                    </div>
                                )}

                                {item.status === 'invalid' && item.validation_errors && (
                                    <div className="card-errors">
                                        <div style={{ display: 'flex', gap: '6px', alignItems: 'center', color: 'var(--color-error)', fontSize: '0.82rem', fontWeight: 600, marginBottom: '4px' }}>
                                            <FiAlertTriangle />
                                            <span>Validation Failures</span>
                                        </div>
                                        <ul style={{ paddingLeft: '20px', margin: 0 }}>
                                            {item.validation_errors.map((err, idx) => (
                                                <li key={idx}>{err.message}</li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>
                        );
                    })
                )}
            </div>

            {/* Approval Confirmation Modal */}
            {showConfirmModal && (
                <div className="apt-modal-overlay" onClick={() => setShowConfirmModal(false)}>
                    <div className="apt-modal" onClick={(e) => e.stopPropagation()}>
                        <div className="apt-modal-header">
                            <h3>Confirm Bulk Import</h3>
                        </div>
                        <div className="apt-modal-body">
                            <p>Are you sure you want to approve this import? This will write all <strong>{totalValid} valid questions</strong> directly to the database.</p>
                            {totalInvalid > 0 && (
                                <p style={{ color: 'var(--color-error)', marginTop: '8px', fontSize: '0.82rem' }}>
                                    Note: {totalInvalid} invalid questions will be skipped.
                                </p>
                            )}
                        </div>
                        <div className="apt-modal-footer">
                            <button
                                className="btn btn-secondary"
                                style={{ padding: '8px 18px', fontSize: '0.85rem' }}
                                onClick={() => setShowConfirmModal(false)}
                            >
                                Cancel
                            </button>
                            <button
                                className="btn btn-primary"
                                style={{ padding: '8px 18px', fontSize: '0.85rem' }}
                                disabled={confirming}
                                onClick={handleConfirmImport}
                            >
                                {confirming ? 'Saving Batch...' : 'Approve & Import'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
