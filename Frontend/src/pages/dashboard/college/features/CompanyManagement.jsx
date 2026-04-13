import { useState, useEffect } from 'react';
import { useAuth } from '../../../../context/AuthContext';
import api from '../../../../utils/api';
import { FiCheckCircle, FiXCircle, FiBriefcase } from 'react-icons/fi';
import { toast } from 'react-toastify';
import SkeletonText from '../../../../components/common/skeleton/SkeletonText';
import SkeletonTableRow from '../../../../components/common/skeleton/SkeletonTableRow';

export default function CompanyManagement() {
    const { user } = useAuth();
    const [companies, setCompanies] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        fetchCompanies();
    }, []);

    const fetchCompanies = async () => {
        try {
            setLoading(true);
            const res = await api.get('/admin/companies');
            setCompanies(res.data);
        } catch (err) {
            setError('Failed to fetch companies.');
            toast.error('Failed to load companies');
        } finally {
            setLoading(false);
        }
    };

    const handleAction = async (id, action, companyName) => {
        try {
            await api.put(`/admin/${action}-company/${id}`);
            toast.success(`Company '${companyName}' ${action === 'verify' ? 'approved' : 'rejected'}`);
            fetchCompanies();
        } catch (err) {
            toast.error(`Failed to ${action} company`);
        }
    };

    if (loading) {
        return (
            <div className="dashboard-content fade-in">
                <div className="page-header slide-in-left">
                    <SkeletonText variant="title" style={{ width: '250px' }} />
                    <SkeletonText variant="subtitle" style={{ width: '400px' }} />
                </div>
                <div className="data-table-container fade-in-up">
                    <div className="data-table-header">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <SkeletonText variant="title" style={{ width: '150px', marginBottom: 0 }} />
                        </div>
                    </div>
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Company Name</th>
                                <th>Admin Details</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {Array.from({ length: 5 }).map((_, i) => (
                                <SkeletonTableRow key={i} columns={4} />
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        );
    }

    return (
        <div className="dashboard-content fade-in">
            <div className="page-header slide-in-left">
                <h1 className="gradient-text">Manage Companies</h1>
                <p>Review and approve company registrations for recruiters.</p>
            </div>

            {error && <div className="alert alert-error">{error}</div>}

            <div className="data-table-container fade-in-up">
                <div className="data-table-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <FiBriefcase size={20} color="var(--color-primary-500)" />
                        <h3>Registered Companies</h3>
                    </div>
                </div>

                {companies.length === 0 ? (
                    <div className="empty-state">
                        <p>No companies found in the system.</p>
                    </div>
                ) : (
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Company Name</th>
                                <th>Admin Details</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {companies.map((item) => (
                                <tr key={item.id}>
                                    <td style={{ fontWeight: '600' }}>{item.name}</td>
                                    <td>
                                        <div style={{ fontWeight: '500' }}>{item.admin_name}</div>
                                        <div style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>{item.admin_email}</div>
                                    </td>
                                    <td>
                                        <span className={`status-badge status-badge-${item.status}`}>
                                            {item.status.charAt(0).toUpperCase() + item.status.slice(1)}
                                        </span>
                                    </td>
                                    <td>
                                        {item.status === 'pending' && (
                                            <div style={{ display: 'flex', gap: '10px' }}>
                                                <button
                                                    onClick={() => handleAction(item.id, 'verify', item.name)}
                                                    className="action-btn action-btn-success"
                                                    title="Approve"
                                                >
                                                    <FiCheckCircle />
                                                </button>
                                                <button
                                                    onClick={() => handleAction(item.id, 'reject', item.name)}
                                                    className="action-btn action-btn-danger"
                                                    title="Reject"
                                                >
                                                    <FiXCircle />
                                                </button>
                                            </div>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
}
