import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { ROLE_LABELS, CHILD_ROLE_MAP } from '../utils/roles';
import api from '../utils/api';
import { FiTrash2, FiCheckCircle, FiXCircle, FiPlus, FiX, FiUserPlus, FiSearch } from 'react-icons/fi';
import { toast } from 'react-toastify';

const TABLE_TITLES = {
    HOD: 'HOD Table',
    FACULTY: 'Faculty Table',
    STUDENT: 'Student Table',
    RECRUITER: 'Recruiter Table',
};

export default function UserManagement({ allUsers = false, colleges = false }) {
    const { user } = useAuth();
    const [dataList, setDataList] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [searchTerm, setSearchTerm] = useState('');

    // Add user modal state
    const [showAddModal, setShowAddModal] = useState(false);
    const [addForm, setAddForm] = useState({ name: '', email: '', department: '' });
    const [addLoading, setAddLoading] = useState(false);
    const [departments, setDepartments] = useState([]);

    // Depending on props/roles, fetch different arrays
    useEffect(() => {
        fetchData();
        if (user.role === 'COLLEGE_PRINCIPAL') {
            fetchDepartments();
        }
    }, [allUsers, colleges, user.role]);

    const fetchDepartments = async () => {
        try {
            const res = await api.get('/college/departments/list');
            setDepartments(res.data);
        } catch (err) {
            console.error('Failed to fetch departments:', err);
        }
    };

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

    const handleAddUser = async (e) => {
        e.preventDefault();
        if (!addForm.name || !addForm.email) {
            toast.error('Name and email are required');
            return;
        }
        setAddLoading(true);
        try {
            const res = await api.post('/college/add-user', addForm);
            toast.success(res.data.message);
            setShowAddModal(false);
            setAddForm({ name: '', email: '', department: '' });
            fetchData();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to add user');
        } finally {
            setAddLoading(false);
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
                    <div className="data-table-header">
                        <h3>Registered Colleges</h3>
                    </div>
                    {dataList.length === 0 ? (
                        <div className="empty-state"><p>No colleges found.</p></div>
                    ) : (
                        <div className="table-scroll-wrapper">
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
                        </div>
                    )}
                </div>
            </div>
        );
    }

    // --- RENDERING USER LIST ---
    const targetRole = CHILD_ROLE_MAP[user.role] || 'Users';
    const tableTitle = TABLE_TITLES[targetRole] || `${ROLE_LABELS[targetRole] || targetRole} Table`;
    const isPrincipal = user.role === 'COLLEGE_PRINCIPAL';
    const pageTitle = allUsers ? 'All Subordinate Users' : tableTitle;
    const pageSubtitle = allUsers
        ? 'View all users in your hierarchy.'
        : `Manage ${ROLE_LABELS[targetRole] || targetRole}s under your supervision.`;

    // Filter by search term
    const filteredList = dataList.filter(usr => {
        if (!searchTerm) return true;
        const term = searchTerm.toLowerCase();
        return (
            usr.name?.toLowerCase().includes(term) ||
            usr.email?.toLowerCase().includes(term) ||
            usr.department?.toLowerCase().includes(term) ||
            usr.phone_number?.toLowerCase().includes(term)
        );
    });

    return (
        <div className="dashboard-content fade-in">
            <div className="page-header slide-in-left">
                <h1 className="gradient-text">{pageTitle}</h1>
                <p>{pageSubtitle}</p>
            </div>

            {error && <div className="alert alert-error">{error}</div>}

            <div className="data-table-container fade-in-up">
                <div className="data-table-header">
                    <h3>{tableTitle} <span className="table-count">({filteredList.length})</span></h3>
                    <div className="table-header-actions">
                        <div className="table-search">
                            <FiSearch className="table-search-icon" />
                            <input
                                type="text"
                                placeholder="Search by name, email, department..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                className="table-search-input"
                            />
                        </div>
                        {!allUsers && (
                            <button
                                className="btn btn-primary add-user-btn"
                                onClick={() => setShowAddModal(true)}
                            >
                                <FiPlus /> Add {ROLE_LABELS[targetRole] || targetRole}
                            </button>
                        )}
                    </div>
                </div>

                {filteredList.length === 0 ? (
                    <div className="empty-state">
                        <FiUserPlus className="empty-state-icon" />
                        <h3>No {ROLE_LABELS[targetRole] || targetRole}s Found</h3>
                        <p>
                            {searchTerm
                                ? 'No results match your search criteria.'
                                : `No ${(ROLE_LABELS[targetRole] || targetRole).toLowerCase()}s have been added yet. Click the "+Add" button to get started.`
                            }
                        </p>
                    </div>
                ) : (
                    <div className="table-scroll-wrapper">
                        <table className="data-table enhanced-table">
                            <thead>
                                <tr>
                                    <th>Name</th>
                                    <th>Email</th>
                                    <th>Department</th>
                                    <th>Role</th>
                                    <th>Status</th>
                                    <th>Phone</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredList.map((usr, idx) => (
                                    <tr key={usr.id} className={idx % 2 === 0 ? 'row-even' : 'row-odd'}>
                                        <td>
                                            <div className="user-cell">
                                                <div className="user-avatar">
                                                    {usr.name?.charAt(0)?.toUpperCase() || '?'}
                                                </div>
                                                <div className="user-info">
                                                    <span className="user-name">{usr.name}</span>
                                                    {usr.roll_number && (
                                                        <span className="user-meta">Roll: {usr.roll_number}</span>
                                                    )}
                                                </div>
                                            </div>
                                        </td>
                                        <td>
                                            <span className="cell-email">{usr.email}</span>
                                        </td>
                                        <td>
                                            <span className="cell-department">
                                                {usr.department || <span className="text-muted">—</span>}
                                            </span>
                                        </td>
                                        <td>
                                            <span className="role-badge">
                                                {ROLE_LABELS[usr.role] || usr.role}
                                            </span>
                                        </td>
                                        <td>
                                            <span className={`status-badge ${usr.is_verified ? 'status-badge-approved' : 'status-badge-pending'}`}>
                                                {usr.is_verified ? 'Active' : 'Pending'}
                                            </span>
                                        </td>
                                        <td>
                                            <span className="cell-phone">
                                                {usr.phone_number || <span className="text-muted">—</span>}
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
                    </div>
                )}
            </div>

            {/* Add User Modal */}
            {showAddModal && (
                <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
                    <div className="modal-content fade-in-up" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3>
                                <FiUserPlus style={{ marginRight: '8px' }} />
                                Add New {ROLE_LABELS[targetRole] || targetRole}
                            </h3>
                            <button className="modal-close" onClick={() => setShowAddModal(false)}>
                                <FiX />
                            </button>
                        </div>
                        <form onSubmit={handleAddUser} className="modal-form">
                            <div className="form-group">
                                <label htmlFor="add-name">Full Name *</label>
                                <input
                                    id="add-name"
                                    type="text"
                                    className="form-input"
                                    value={addForm.name}
                                    onChange={(e) => setAddForm({ ...addForm, name: e.target.value })}
                                    placeholder="Enter full name"
                                    required
                                />
                            </div>
                            <div className="form-group">
                                <label htmlFor="add-email">Email Address *</label>
                                <input
                                    id="add-email"
                                    type="email"
                                    className="form-input"
                                    value={addForm.email}
                                    onChange={(e) => setAddForm({ ...addForm, email: e.target.value })}
                                    placeholder="Enter email address"
                                    required
                                />
                            </div>
                            {isPrincipal && (
                                <div className="form-group">
                                    <label htmlFor="add-department">Department *</label>
                                    <select
                                        id="add-department"
                                        className="form-input"
                                        value={addForm.department}
                                        onChange={(e) => setAddForm({ ...addForm, department: e.target.value })}
                                        required
                                    >
                                        <option value="">Select Department</option>
                                        {departments.map((d) => (
                                            <option key={d.id} value={d.name}>{d.name}</option>
                                        ))}
                                    </select>
                                </div>
                            )}
                            <div className="modal-actions">
                                <button
                                    type="button"
                                    className="btn btn-secondary"
                                    onClick={() => setShowAddModal(false)}
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="btn btn-primary"
                                    disabled={addLoading}
                                >
                                    <FiPlus />
                                    {addLoading ? 'Adding...' : `Add ${ROLE_LABELS[targetRole] || targetRole}`}
                                </button>
                            </div>
                            <p className="modal-note">
                                The user will receive an email with instructions to set their password.
                            </p>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
