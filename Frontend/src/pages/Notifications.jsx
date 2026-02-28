import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { FiBell, FiCheck, FiX, FiClock, FiBriefcase, FiAward, FiInfo } from 'react-icons/fi';

export default function Notifications() {
    const { user } = useAuth();
    const [notifications, setNotifications] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const fetchNotifications = async () => {
        try {
            setLoading(true);
            setError('');
            const res = await api.get('/messages/notifications');
            setNotifications(res.data || []);
        } catch (err) {
            setError(err?.response?.data?.detail || 'Failed to fetch notifications');
        } finally {
            setLoading(false);
        }
    };

    const markAsRead = async (notificationId) => {
        try {
            await api.put(`/notifications/${notificationId}/read`);
            setNotifications(prev =>
                prev.map(n => n.id === notificationId ? { ...n, is_read: true } : n)
            );
        } catch (err) {
            console.error('Failed to mark as read:', err);
        }
    };

    const deleteNotification = async (notificationId) => {
        try {
            await api.delete(`/notifications/${notificationId}`);
            setNotifications(prev => prev.filter(n => n.id !== notificationId));
        } catch (err) {
            console.error('Failed to delete notification:', err);
        }
    };

    useEffect(() => {
        fetchNotifications();
    }, []);

    const getNotificationIcon = (type) => {
        switch (type) {
            case 'INTERVIEW_UPDATE': return <FiBriefcase style={{ color: 'var(--color-primary)' }} />;
            case 'AI_INTERVIEW_ASSIGNED': return <FiClock style={{ color: 'var(--color-secondary)' }} />;
            case 'HIRED': return <FiAward style={{ color: 'var(--color-success)' }} />;
            case 'REJECTED': return <FiX style={{ color: 'var(--color-error)' }} />;
            default: return <FiInfo style={{ color: 'var(--color-text-muted)' }} />;
        }
    };

    const getStatusBadge = (isRead) => {
        return isRead ? (
            <span style={{
                padding: '2px 8px',
                borderRadius: '12px',
                fontSize: '0.7rem',
                backgroundColor: 'var(--color-bg-secondary)',
                color: 'var(--color-text-muted)'
            }}>
                Read
            </span>
        ) : (
            <span style={{
                padding: '2px 8px',
                borderRadius: '12px',
                fontSize: '0.7rem',
                backgroundColor: 'var(--color-primary)',
                color: '#fff',
                fontWeight: '600'
            }}>
                New
            </span>
        );
    };

    if (loading) {
        return (
            <div className="dashboard-content">
                <div className="page-header slide-in-left">
                    <h1 className="gradient-text">Notifications</h1>
                    <p>Stay updated with your interview status and feedback</p>
                </div>
                <div className="spinner" style={{ margin: '40px auto' }}></div>
            </div>
        );
    }

    return (
        <div className="dashboard-content">
            <div className="page-header slide-in-left">
                <h1 className="gradient-text">Notifications</h1>
                <p>Stay updated with your interview status and feedback</p>
            </div>

            {error && (
                <div className="alert alert-error" style={{ marginBottom: '16px' }}>
                    {error}
                </div>
            )}

            <div className="dashboard-card fade-in-up">
                <div className="data-table-header">
                    <h3>
                        All Notifications <span className="table-count">({notifications.length})</span>
                    </h3>
                    <button
                        className="btn btn-secondary btn-sm"
                        onClick={fetchNotifications}
                    >
                        Refresh
                    </button>
                </div>

                {notifications.length === 0 ? (
                    <div className="empty-state">
                        <FiBell size={48} style={{ marginBottom: '16px', opacity: 0.5 }} />
                        <h3>No Notifications</h3>
                        <p style={{ color: 'var(--color-text-muted)' }}>
                            You don't have any notifications yet. Check back later for updates on your interviews.
                        </p>
                    </div>
                ) : (
                    <div style={{ display: 'grid', gap: '12px' }}>
                        {notifications.map((notification) => (
                            <div
                                key={notification.id}
                                className={`notification-card ${!notification.is_read ? 'unread' : ''}`}
                                style={{
                                    padding: '16px',
                                    border: `1px solid ${notification.is_read ? 'var(--color-border)' : 'var(--color-primary)'}`,
                                    borderRadius: '8px',
                                    backgroundColor: notification.is_read ? 'var(--color-bg-card)' : 'var(--color-bg-primary)',
                                    borderLeftWidth: '4px',
                                    borderLeftColor: notification.is_read ? 'var(--color-border)' : 'var(--color-primary)'
                                }}
                            >
                                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                                    <div style={{ marginTop: '2px' }}>
                                        {getNotificationIcon(notification.type)}
                                    </div>

                                    <div style={{ flex: 1 }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                                            <h4 style={{ margin: 0, fontSize: '1rem', fontWeight: '600' }}>
                                                {notification.subject}
                                            </h4>
                                            {getStatusBadge(notification.is_read)}
                                        </div>

                                        <p style={{
                                            margin: '0 0 8px 0',
                                            color: 'var(--color-text-secondary)',
                                            lineHeight: '1.5'
                                        }}>
                                            {notification.body}
                                        </p>

                                        <div style={{
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                            alignItems: 'center',
                                            fontSize: '0.8rem',
                                            color: 'var(--color-text-muted)'
                                        }}>
                                            <span>
                                                {new Date(notification.created_at).toLocaleDateString()} at {new Date(notification.created_at).toLocaleTimeString()}
                                            </span>

                                            <div style={{ display: 'flex', gap: '8px' }}>
                                                {!notification.is_read && (
                                                    <button
                                                        className="btn btn-sm btn-secondary"
                                                        onClick={() => markAsRead(notification.id)}
                                                        style={{ padding: '4px 8px', fontSize: '0.7rem' }}
                                                    >
                                                        <FiCheck style={{ marginRight: '4px' }} />
                                                        Mark Read
                                                    </button>
                                                )}
                                                <button
                                                    className="btn btn-sm btn-error"
                                                    onClick={() => deleteNotification(notification.id)}
                                                    style={{ padding: '4px 8px', fontSize: '0.7rem' }}
                                                >
                                                    <FiX style={{ marginRight: '4px' }} />
                                                    Delete
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
