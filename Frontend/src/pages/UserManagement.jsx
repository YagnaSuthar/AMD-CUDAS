import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { ROLE_LABELS, CHILD_ROLE_MAP } from '../utils/roles';
import api from '../utils/api';
import { FiTrash2, FiCheckCircle, FiXCircle } from 'react-icons/fi';
import { toast } from 'react-toastify';

export default function UserManagement({ allUsers = false, colleges = false }) {
    const { user } = useAuth();
    const [dataList, setDataList] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    // Depending on props/roles, fetch different arrays
    useEffect(() => {
        fetchData();
    }, [allUsers, colleges, user.role]);

    const fetchData = async () => {
        try {
            setLoading(true);
            if (colleges && user.role === 'CUDAS_ADMIN') {
                const res = await api.get('/admin/colleges');
                setDataList(res.data);
            } else if (allUsers) {
                const res = await api.get('/college/all-users');
                setDataList(res.data);
            } else {
                const res = await api.get('/college/users');
                setDataList(res.data);
            }
        } catch (err) {
            setError('Failed to fetch data list.');
        } finally {
            setLoading(false);
        }
    };

    const handleCollegeAction = async (id, action) => {
        try {
            await api.put(`/admin/${action}-college/${id}`);
            toast.success(`College ${action === 'verify' ? 'approved' : 'rejected'}`);
            fetchData();
        } catch (err) {
            toast.error(`Action failed: ${err.response?.data?.detail || 'Unknown error'}`);
        }
    };

    const handleDeleteUser = async (id) => {
        if (!window.confirm('Are you sure you want to delete this user? This action cannot be undone.')) return;
        try {
            await api.delete(`/college/users/${id}`);
            toast.success('User deleted successfully');
            fetchData();
        } catch (err) {
            toast.error(`Deletion failed: ${err.response?.data?.detail || 'Unknown error'}`);
        }
    };

    if (loading) return <div className="spinner" style={{ margin: '40px auto' }}></div>;

    // --- RENDERING ADMIN COLLEGE LIST ---
    if (colleges && user.role === 'CUDAS_ADMIN') {
        return (
            <div className="dashboard-content fade-in">
                <div className="page-header slide-in-left">
                    <h1 className="gradient-text">Manage Colleges</h1>
                    <p>Approve or reject college registrations.</p>
                </div>

                {error && <div className="alert alert-error">{error}</div>}

                <div className="data-table-container fade-in-up">
                    <div className="data-table-header"><h3>Registered Colleges</h3></div>
                    {dataList.length === 0 ? (
                        <div className="empty-state"><p>No colleges found.</p></div>
                    ) : (
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>College Name</th>
                                    <th>Principal</th>
                                    <th>Status</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {dataList.map((item) => (
                                    <tr key={item.id}>
                                        <td style={{ fontWeight: '500' }}>{item.name}</td>
                                        <td>
                                            <div>{item.principal_name}</div>
                                            <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>{item.principal_email}</div>
                                        </td>
                                        <td>
                                            <span className={`status-badge status-badge-${item.status}`}>
                                                {item.status}
                                            </span>
                                        </td>
                                        <td>
                                            {item.status === 'pending' && (
                                                <div style={{ display: 'flex', gap: '8px' }}>
                                                    <button onClick={() => handleCollegeAction(item.id, 'verify')} className="action-btn action-btn-success" title="Approve">
                                                        <FiCheckCircle />
                                                    </button>
                                                    <button onClick={() => handleCollegeAction(item.id, 'reject')} className="action-btn action-btn-danger" title="Reject">
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

    // --- RENDERING USER LIST ---
    const targetRole = CHILD_ROLE_MAP[user.role] || 'Users';
    // If current user is principal, targetRole is HOD
    const isPrincipal = user.role === 'COLLEGE_PRINCIPAL';
    const pageTitle = isPrincipal ? 'HOD Management' : (allUsers ? 'All Subordinate Users' : `Manage ${ROLE_LABELS[targetRole] || targetRole}s`);

    return (
        <div className="dashboard-content fade-in">
            <div className="page-header slide-in-left">
                <h1 className="gradient-text">{pageTitle}</h1>
                <p>View and manage all users assigned under your hierarchy.</p>
            </div>

            {error && <div className="alert alert-error">{error}</div>}

            <div className="data-table-container fade-in-up">
                <div className="data-table-header">
                    <h3>User Directory ({dataList.length})</h3>
                </div>
                {dataList.length === 0 ? (
                    <div className="empty-state"><p>No users found under your hierarchy.</p></div>
                ) : (
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Role</th>
                                <th>Contact</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {dataList.map((usr) => (
                                <tr key={usr.id}>
                                    <td style={{ fontWeight: '500' }}>
                                        {usr.name}
                                        {(usr.department || usr.roll_number) && (
                                            <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                                                {usr.department && `${usr.department} `}
                                                {usr.roll_number && `| Roll: ${usr.roll_number}`}
                                            </div>
                                        )}
                                    </td>
                                    <td>
                                        <span className="status-badge" style={{ background: 'var(--color-primary-300)', color: 'var(--color-text-primary)' }}>
                                            {ROLE_LABELS[usr.role] || usr.role}
                                        </span>
                                    </td>
                                    <td>{usr.email}</td>
                                    <td>
                                        <span className={`status-badge ${usr.is_verified ? 'status-badge-approved' : 'status-badge-pending'}`}>
                                            {usr.is_verified ? 'Verified' : 'Pending'}
                                        </span>
                                    </td>
                                    <td>
                                        <button
                                            onClick={() => handleDeleteUser(usr.id)}
                                            className="action-btn action-btn-danger"
                                            title="Delete User"
                                        >
                                            <FiTrash2 />
                                        </button>
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
