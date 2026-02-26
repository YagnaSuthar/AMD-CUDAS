import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { ROLE_LABELS } from '../utils/roles';
import api from '../utils/api';
import { FiUser, FiMail, FiPhone, FiBriefcase, FiSave, FiShield, FiBookOpen, FiHash } from 'react-icons/fi';
import { toast } from 'react-toastify';

export default function Profile() {
    const { user, fetchUser } = useAuth();
    const [phoneNumber, setPhoneNumber] = useState('');
    const [loading, setLoading] = useState(false);
    const [profileData, setProfileData] = useState(null);

    useEffect(() => {
        loadProfile();
    }, []);

    const loadProfile = async () => {
        try {
            const res = await api.get('/auth/me');
            setProfileData(res.data);
            setPhoneNumber(res.data.phone_number || '');
        } catch (err) {
            toast.error('Failed to load profile');
        }
    };

    const handleSavePhone = async () => {
        setLoading(true);
        try {
            await api.put('/auth/profile', { phone_number: phoneNumber });
            toast.success('Phone number updated successfully!');
            await fetchUser();
            await loadProfile();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to update profile');
        } finally {
            setLoading(false);
        }
    };

    if (!profileData) {
        return <div className="spinner" style={{ margin: '40px auto' }}></div>;
    }

    const data = profileData;

    return (
        <div className="dashboard-content fade-in">
            <div className="page-header slide-in-left">
                <h1 className="gradient-text">My Profile</h1>
                <p>View and update your personal information.</p>
            </div>

            <div className="profile-page-grid">
                {/* Profile Card */}
                <div className="profile-card fade-in-up">
                    <div className="profile-avatar-section">
                        <div className="profile-avatar-large">
                            {data.name?.charAt(0)?.toUpperCase() || 'U'}
                        </div>
                        <h2 className="profile-name">{data.name}</h2>
                        <span className="profile-role-badge">
                            <FiShield style={{ fontSize: '0.75rem' }} />
                            {ROLE_LABELS[data.role] || data.role}
                        </span>
                    </div>
                </div>

                {/* Details Card */}
                <div className="profile-details-card fade-in-up fade-in-delay-1">
                    <h3 className="profile-section-title">Personal Information</h3>

                    <div className="profile-field">
                        <div className="profile-field-icon"><FiUser /></div>
                        <div className="profile-field-content">
                            <label>Full Name</label>
                            <span>{data.name}</span>
                        </div>
                    </div>

                    <div className="profile-field">
                        <div className="profile-field-icon"><FiMail /></div>
                        <div className="profile-field-content">
                            <label>Email Address</label>
                            <span>{data.email}</span>
                        </div>
                    </div>

                    <div className="profile-field">
                        <div className="profile-field-icon"><FiShield /></div>
                        <div className="profile-field-content">
                            <label>Role</label>
                            <span>{ROLE_LABELS[data.role] || data.role}</span>
                        </div>
                    </div>

                    {data.department && (
                        <div className="profile-field">
                            <div className="profile-field-icon"><FiBriefcase /></div>
                            <div className="profile-field-content">
                                <label>Department</label>
                                <span>{data.department}</span>
                            </div>
                        </div>
                    )}

                    {data.semester && (
                        <div className="profile-field">
                            <div className="profile-field-icon"><FiBookOpen /></div>
                            <div className="profile-field-content">
                                <label>Semester</label>
                                <span>{data.semester}</span>
                            </div>
                        </div>
                    )}

                    {data.roll_number && (
                        <div className="profile-field">
                            <div className="profile-field-icon"><FiHash /></div>
                            <div className="profile-field-content">
                                <label>Roll Number</label>
                                <span>{data.roll_number}</span>
                            </div>
                        </div>
                    )}

                    <div className="profile-field profile-field-editable">
                        <div className="profile-field-icon"><FiPhone /></div>
                        <div className="profile-field-content">
                            <label>Phone Number</label>
                            <div className="profile-phone-edit">
                                <input
                                    type="tel"
                                    className="profile-input"
                                    value={phoneNumber}
                                    onChange={(e) => setPhoneNumber(e.target.value)}
                                    placeholder="Enter your phone number"
                                />
                                <button
                                    onClick={handleSavePhone}
                                    disabled={loading}
                                    className="btn btn-primary profile-save-btn"
                                >
                                    <FiSave />
                                    {loading ? 'Saving...' : 'Save'}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
