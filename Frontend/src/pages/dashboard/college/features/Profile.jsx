import { useState, useEffect } from 'react';
import { useAuth } from '../../../../context/AuthContext';
import { ROLE_LABELS } from '../../../../utils/roles';
import api from '../../../../utils/api';
import { FiUser, FiMail, FiPhone, FiBriefcase, FiSave, FiShield, FiBookOpen, FiHash, FiTarget, FiEdit2, FiX, FiGithub } from 'react-icons/fi';
import { toast } from 'react-toastify';
import SkeletonText from '../../../../components/common/skeleton/SkeletonText';
import SkeletonAvatar from '../../../../components/common/skeleton/SkeletonAvatar';
import SkeletonButton from '../../../../components/common/skeleton/SkeletonButton';

export default function Profile() {
    const { user, fetchUser } = useAuth();
    const [phoneNumber, setPhoneNumber] = useState('');
    const [githubUsername, setGithubUsername] = useState('');
    const [goal, setGoal] = useState('');
    const [isEditingGoal, setIsEditingGoal] = useState(false);
    const [tempGoal, setTempGoal] = useState('');
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
            setGithubUsername(res.data.github_username || '');
            setGoal(res.data.goal || '');
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

    const handleSaveGithub = async () => {
        setLoading(true);
        try {
            await api.put('/auth/profile', { github_username: githubUsername });
            toast.success('GitHub username updated successfully!');
            await fetchUser();
            await loadProfile();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to update GitHub username');
        } finally {
            setLoading(false);
        }
    };

    const handleSaveGoal = async () => {
        if (!tempGoal.trim()) return;
        
        setLoading(true);
        try {
            await api.put('/auth/profile', { goal: tempGoal });
            setGoal(tempGoal);
            setIsEditingGoal(false);
            toast.success('Career goal updated successfully!');
            await fetchUser();
            await loadProfile();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to update goal');
        } finally {
            setLoading(false);
        }
    };

    const startEditingGoal = () => {
        setTempGoal(goal);
        setIsEditingGoal(true);
    };

    const cancelEditingGoal = () => {
        setTempGoal('');
        setIsEditingGoal(false);
    };

    if (!profileData) {
        return (
            <div className="dashboard-content fade-in">
                <div className="page-header">
                    <SkeletonText variant="title" style={{ width: '250px' }} />
                    <SkeletonText variant="subtitle" style={{ width: '350px' }} />
                </div>
                <div className="profile-page-grid">
                    <div className="profile-card">
                        <div className="profile-avatar-section" style={{ alignItems: 'center', display: 'flex', flexDirection: 'column' }}>
                            <SkeletonAvatar size="lg" style={{ marginBottom: '16px' }} />
                            <SkeletonText variant="title" style={{ width: '150px', marginBottom: '8px' }} />
                            <SkeletonButton style={{ width: '100px', height: '24px', borderRadius: '12px' }} />
                        </div>
                    </div>
                    <div className="profile-details-card">
                        <SkeletonText variant="title" style={{ width: '200px', marginBottom: '24px' }} />
                        {Array.from({ length: 5 }).map((_, i) => (
                            <div key={i} className="profile-field" style={{ display: 'flex', gap: '16px', marginBottom: '20px' }}>
                                <SkeletonAvatar size="sm" />
                                <div style={{ flex: 1 }}>
                                    <SkeletonText variant="subtitle" style={{ width: '100px', marginBottom: '4px' }} />
                                    <SkeletonText style={{ width: '250px' }} />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        );
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

                    {data.enrollment_number && (
                        <div className="profile-field">
                            <div className="profile-field-icon"><FiHash /></div>
                            <div className="profile-field-content">
                                <label>Enrollment Number</label>
                                <span>{data.enrollment_number}</span>
                            </div>
                        </div>
                    )}

                    {data.role === 'STUDENT' && (
                        <div className="profile-field">
                            <div className="profile-field-icon"><FiTarget /></div>
                            <div className="profile-field-content">
                                <label>Career Goal</label>
                                {isEditingGoal ? (
                                    <div className="profile-goal-edit">
                                        <textarea
                                            className="profile-input"
                                            value={tempGoal}
                                            onChange={(e) => setTempGoal(e.target.value)}
                                            placeholder="What do you want to achieve in your career?"
                                            style={{
                                                width: '100%',
                                                minHeight: '80px',
                                                resize: 'vertical',
                                                marginBottom: '10px'
                                            }}
                                        />
                                        <div style={{ display: 'flex', gap: '8px' }}>
                                            <button
                                                onClick={handleSaveGoal}
                                                disabled={loading || !tempGoal.trim()}
                                                className="btn btn-primary profile-save-btn"
                                            >
                                                <FiSave />
                                                {loading ? 'Saving...' : 'Save'}
                                            </button>
                                            <button
                                                onClick={cancelEditingGoal}
                                                className="btn btn-secondary"
                                                style={{ padding: '8px 12px' }}
                                            >
                                                <FiX />
                                                Cancel
                                            </button>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="profile-goal-display">
                                        <span>{goal || 'No career goal set yet'}</span>
                                        <button
                                            onClick={startEditingGoal}
                                            className="btn btn-secondary btn-sm"
                                            style={{ marginLeft: '10px' }}
                                        >
                                            <FiEdit2 />
                                        </button>
                                    </div>
                                )}
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

                    <div className="profile-field profile-field-editable fade-in-up fade-in-delay-3" style={{ marginTop: '20px' }}>
                        <div className="profile-field-icon" style={{ background: 'var(--gradient-secondary)' }}><FiGithub /></div>
                        <div className="profile-field-content">
                            <label>GitHub Username</label>
                            <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginBottom: '8px' }}>
                                Required for Project Verification Agent
                            </p>
                            <div className="profile-phone-edit">
                                <input
                                    type="text"
                                    className="profile-input"
                                    value={githubUsername}
                                    onChange={(e) => setGithubUsername(e.target.value)}
                                    placeholder="e.g. torvalds"
                                />
                                <button
                                    onClick={handleSaveGithub}
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
