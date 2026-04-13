import { useState, useEffect } from 'react';
import { useAuth } from '../../../../context/AuthContext';
import { ROLE_LABELS, CHILD_ROLE_MAP } from '../../../../utils/roles';
import api from '../../../../utils/api';
import { FiTrash2, FiCheckCircle, FiXCircle, FiPlus, FiX, FiUserPlus, FiSearch } from 'react-icons/fi';
import { toast } from 'react-toastify';
import SkeletonText from '../../../../components/common/skeleton/SkeletonText';
import SkeletonTableRow from '../../../../components/common/skeleton/SkeletonTableRow';

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
    const [addForm, setAddForm] = useState({ name: '', email: '', department: '', enrollment_number: '' });
    const [addLoading, setAddLoading] = useState(false);
    const [departments, setDepartments] = useState([]);
    
    // Details modal state
    const [showDetailsModal, setShowDetailsModal] = useState(false);
    const [selectedUser, setSelectedUser] = useState(null);
    const [userDetails, setUserDetails] = useState({ subjects: [], mentors: [] });
    const [detailsLoading, setDetailsLoading] = useState(false);

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

    const fetchUserDetails = async (usr) => {
        setSelectedUser(usr);
        setShowDetailsModal(true);
        setDetailsLoading(true);
        try {
            const [subRes, mentRes] = await Promise.all([
                api.get(`/api/subject/faculty/${usr.id}`),
                api.get(`/college/mentor/faculty/${usr.id}`)
            ]);
            setUserDetails({
                subjects: subRes.data || [],
                mentors: mentRes.data || []
            });
        } catch (err) {
            console.error('Failed to fetch faculty details', err);
            toast.error('Failed to load faculty details');
        } finally {
            setDetailsLoading(false);
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
            setAddForm({ name: '', email: '', department: '', enrollment_number: '' });
            fetchData();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to add user');
        } finally {
            setAddLoading(false);
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
                        <SkeletonText variant="title" style={{ width: '150px' }} />
                    </div>
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
                                {Array.from({ length: 5 }).map((_, i) => (
                                    <SkeletonTableRow key={i} columns={7} />
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        );
    }

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
                                                    {usr.enrollment_number && (
                                                        <span className="user-meta">Enrollment No: {usr.enrollment_number}</span>
                                                    )}
                                                </div>
                                            </div>
                                        </td>
                                        <td>
                                            <span className="cell-email">{usr.email}</span>
                                        </td>
                                        <td>
                                            <span className="cell-department">
                                                {usr.department || <span className="text-muted">â€”</span>}
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
                                                {usr.phone_number || <span className="text-muted">â€”</span>}
                                            </span>
                                        </td>
                                        <td>
                                            <div style={{ display: 'flex', gap: '8px' }}>
                                                {(user.role === 'HOD' || user.role === 'COLLEGE_PRINCIPAL') && usr.role === 'FACULTY' && (
                                                    <button
                                                        onClick={() => fetchUserDetails(usr)}
                                                        className="action-btn action-btn-primary"
                                                        title="View Details"
                                                    >
                                                        Details
                                                    </button>
                                                )}
                                                <button
                                                    onClick={() => handleDeleteUser(usr.id)}
                                                    className="action-btn action-btn-danger"
                                                    title="Delete User"
                                                >
                                                    <FiTrash2 />
                                                </button>
                                            </div>
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
                            {targetRole === 'STUDENT' && (
                                <div className="form-group">
                                    <label htmlFor="add-enrollment-number">Enrollment Number *</label>
                                    <input
                                        id="add-enrollment-number"
                                        type="text"
                                        className="form-input"
                                        value={addForm.enrollment_number}
                                        onChange={(e) => setAddForm({ ...addForm, enrollment_number: e.target.value })}
                                        placeholder="Enter unique enrollment number"
                                        required
                                    />
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

            {/* Faculty Details Modal */}
            {showDetailsModal && selectedUser && (
                <div className="modal-overlay" onClick={() => setShowDetailsModal(false)}>
                    <div className="modal-content fade-in-up" style={{ maxWidth: '500px' }} onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3> Faculty Details</h3>
                            <button className="modal-close" onClick={() => setShowDetailsModal(false)}><FiX /></button>
                        </div>
                        
                        <div className="modal-body" style={{ padding: '20px' }}>
                            <div style={{ marginBottom: '24px', textAlign: 'center' }}>
                                <div className="user-avatar" style={{ width: '64px', height: '64px', fontSize: '1.5rem', margin: '0 auto 12px' }}>
                                    {selectedUser.name?.charAt(0)?.toUpperCase()}
                                </div>
                                <h2 style={{ fontSize: '1.4rem', fontWeight: 700, margin: 0 }}>{selectedUser.name}</h2>
                                <p style={{ color: 'var(--color-text-muted)' }}>{selectedUser.email}</p>
                            </div>

                            {detailsLoading ? (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', padding: '10px 0' }}>
                                    <SkeletonCard style={{ height: '80px' }} />
                                    <SkeletonCard style={{ height: '80px' }} />
                                </div>
                            ) : (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                                    {/* SUBJECTS */}
                                    <div>
                                        <h4 style={{ fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '1px', color: 'var(--color-primary)', marginBottom: '12px', borderBottom: '1px solid var(--color-border)', pb: '8px' }}>
                                            Assigned Subjects
                                        </h4>
                                        {userDetails.subjects.length > 0 ? (
                                            <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                                {userDetails.subjects.map((sub, i) => (
                                                    <li key={i} style={{ padding: '10px 14px', background: 'var(--color-bg-alt)', borderRadius: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                        <span style={{ fontWeight: 600 }}>{sub.subject_name}</span>
                                                        <span className="status-badge" style={{ fontSize: '0.75rem' }}>Sem {sub.semester}</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        ) : (
                                            <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem', fontStyle: 'italic' }}>No subjects assigned yet.</p>
                                        )}
                                    </div>

                                    {/* MENTOR */}
                                    <div>
                                        <h4 style={{ fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '1px', color: 'var(--color-primary)', marginBottom: '12px', borderBottom: '1px solid var(--color-border)', pb: '8px' }}>
                                            Mentor Assignments
                                        </h4>
                                        {userDetails.mentors.length > 0 ? (
                                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                                                {userDetails.mentors.map((m, i) => (
                                                    <span key={i} className="status-badge status-badge-approved">
                                                        Semester {m.semester}
                                                    </span>
                                                ))}
                                            </div>
                                        ) : (
                                            <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem', fontStyle: 'italic' }}>No mentor assignments yet.</p>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>

                        <div className="modal-footer" style={{ borderTop: '1px solid var(--color-border)', padding: '16px 20px', textAlign: 'right' }}>
                            <button className="btn btn-secondary" onClick={() => setShowDetailsModal(false)}>Close</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
