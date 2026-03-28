import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { FiBell, FiCheck, FiX, FiClock, FiBriefcase, FiAward, FiInfo } from 'react-icons/fi';

export default function Notifications() {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [notifications, setNotifications] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const fetchNotifications = async () => {
        try {
            setLoading(true);
            setError('');
            const res = await api.get('/messages/notifications');
            const data = res.data;
            const list = Array.isArray(data) ? data : (data?.notifications ?? []);
            setNotifications(Array.isArray(list) ? list : []);
        } catch (err) {
            setError(err?.response?.data?.detail || 'Failed to fetch notifications');
        } finally {
            setLoading(false);
        }
    };

    const markAsRead = async (notificationId) => {
        try {
            await api.post('/messages/notifications/mark-read', { notification_ids: [notificationId] });
            setNotifications(prev =>
                prev.map(n => n.id === notificationId ? { ...n, is_read: true } : n)
            );
        } catch (err) {
            console.error('Failed to mark as read:', err);
        }
    };

    const deleteNotification = async (notificationId) => {
        try {
            await api.delete(`/messages/notifications/${notificationId}`);
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
            case 'MESSAGE': return <FiInfo style={{ color: 'var(--color-primary)' }} />;
            case 'AI_ASSIGNED': return <FiClock style={{ color: 'var(--color-secondary)' }} />;
            case 'ROUND2_INVITED': return <FiBriefcase style={{ color: 'var(--color-warning)' }} />;
            case 'HIRED': return <FiAward style={{ color: 'var(--color-success)' }} />;
            default: return <FiInfo style={{ color: 'var(--color-text-muted)' }} />;
        }
    };

    const openRound2 = (pipelineId) => {
        if (!pipelineId) return;
        navigate(`/dashboard/round2/${pipelineId}`);
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
                                className={`notification-item ${!notification.is_read ? 'unread' : ''}`}
                                style={{
                                    padding: '20px 16px',
                                    borderBottom: '1px solid var(--color-border)',
                                    backgroundColor: notification.is_read ? 'transparent' : 'var(--color-bg-primary)',
                                    borderLeft: `3px solid ${notification.is_read ? 'transparent' : 'var(--color-primary)'}`,
                                    transition: 'background-color 0.2s',
                                    display: 'flex',
                                    flexDirection: 'column'
                                }}
                            >
                                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '16px' }}>
                                    <div style={{ 
                                        marginTop: '2px', 
                                        padding: '10px', 
                                        borderRadius: '50%', 
                                        background: 'var(--color-bg-secondary)',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center'
                                    }}>
                                        {getNotificationIcon(notification.notification_type || notification.type)}
                                    </div>

                                    <div style={{ flex: 1 }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                                            <h4 style={{ margin: 0, fontSize: '1.05rem', fontWeight: '500', color: 'var(--color-text-primary)' }}>
                                                {notification.title || notification.subject || 'Notification'}
                                            </h4>
                                            {getStatusBadge(notification.is_read)}
                                        </div>

                                        {notification.notification_type === 'AI_ASSIGNED' && notification.meta_json?.status ? (
                                            <div style={{
                                                margin: '12px 0',
                                                padding: '16px',
                                                borderRadius: '8px',
                                                border: `1px solid ${notification.meta_json.status === 'verified' ? 'var(--color-success)' : notification.meta_json.status === 'suspicious' ? 'var(--color-warning)' : 'var(--color-danger)'}`,
                                                background: 'var(--color-bg-main)',
                                            }}>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                                                    <span style={{
                                                        display: 'inline-flex', alignItems: 'center', gap: '4px',
                                                        padding: '4px 12px', borderRadius: '20px', fontSize: '0.8rem', fontWeight: 600,
                                                        background: notification.meta_json.status === 'verified' ? 'rgba(16,185,129,0.15)' : notification.meta_json.status === 'suspicious' ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.15)',
                                                        color: notification.meta_json.status === 'verified' ? 'var(--color-success)' : notification.meta_json.status === 'suspicious' ? 'var(--color-warning)' : 'var(--color-danger)',
                                                    }}>
                                                        {notification.meta_json.status === 'verified' ? '✓ Verified' : notification.meta_json.status === 'suspicious' ? '⚠ Suspicious' : '✗ Failed'}
                                                    </span>
                                                    <span style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
                                                        Score: {Math.round(notification.meta_json.score * 100)}% | Trust: {notification.meta_json.trust_score}
                                                    </span>
                                                </div>
                                                {notification.meta_json.issues?.length > 0 && (
                                                    <ul style={{ margin: '8px 0', paddingLeft: '20px', fontSize: '0.85rem', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                                                        {notification.meta_json.issues.slice(0, 3).map((issue, i) => (
                                                            <li key={i}>{issue}</li>
                                                        ))}
                                                    </ul>
                                                )}
                                                {notification.meta_json.recommendations?.length > 0 && (
                                                    <div style={{ marginTop: '10px', fontSize: '0.85rem', color: 'var(--color-text-primary)' }}>
                                                        <strong>Tip:</strong> {notification.meta_json.recommendations[0]}
                                                    </div>
                                                )}
                                            </div>
                                        ) : (
                                            <p style={{
                                                margin: '0 0 12px 0',
                                                fontSize: '0.95rem',
                                                color: 'var(--color-text-secondary)',
                                                lineHeight: '1.5'
                                            }}>
                                                {notification.message || notification.body || ''}
                                            </p>
                                        )}

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
                                                {(notification.notification_type === 'ROUND2_INVITED' || notification.type === 'ROUND2_INVITED') && (notification.meta_json?.pipeline_id) && (
                                                    <button
                                                        className="btn btn-sm btn-primary"
                                                        onClick={() => openRound2(notification.meta_json.pipeline_id)}
                                                        style={{ padding: '4px 8px', fontSize: '0.7rem' }}
                                                    >
                                                        Start Round 2
                                                    </button>
                                                )}
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

                                        {(notification.notification_type === 'ROUND2_INVITED' || notification.type === 'ROUND2_INVITED') && notification.meta_json?.round2_scheduled_at && (
                                            <div style={{ marginTop: '8px', fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
                                                <FiClock style={{ marginRight: '6px', verticalAlign: 'middle' }} />
                                                Scheduled: {new Date(notification.meta_json.round2_scheduled_at).toLocaleString()}
                                            </div>
                                        )}
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
