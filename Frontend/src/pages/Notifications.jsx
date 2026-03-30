import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import NotificationItem from '../components/NotificationItem';
import { FiBell, FiInbox, FiCheckCircle } from 'react-icons/fi';

export default function Notifications() {
    const { user } = useAuth();
    const navigate = useNavigate();

    const [notifications, setNotifications] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [activeTab, setActiveTab] = useState('inbox');   // 'inbox' | 'read'
    const [selectedIds, setSelectedIds] = useState(new Set());

    /* ── Fetch ──────────────────────────────────────────────────────── */

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

    useEffect(() => {
        fetchNotifications();
    }, []);

    /* ── Derived lists ──────────────────────────────────────────────── */

    const inboxList = useMemo(
        () => notifications.filter(n => !n.is_read),
        [notifications]
    );

    const readList = useMemo(
        () => notifications.filter(n => n.is_read),
        [notifications]
    );

    const currentList = activeTab === 'inbox' ? inboxList : readList;

    /* ── Actions ────────────────────────────────────────────────────── */

    const markAsRead = async (notificationId) => {
        try {
            await api.post('/messages/notifications/mark-read', {
                notification_ids: [notificationId],
            });
            setNotifications(prev =>
                prev.map(n => n.id === notificationId ? { ...n, is_read: true } : n)
            );
            setSelectedIds(prev => {
                const next = new Set(prev);
                next.delete(notificationId);
                return next;
            });
        } catch (err) {
            console.error('Failed to mark as read:', err);
        }
    };

    const markSelectedAsRead = async () => {
        const ids = [...selectedIds].filter(id =>
            notifications.find(n => n.id === id && !n.is_read)
        );
        if (ids.length === 0) return;
        try {
            await api.post('/messages/notifications/mark-read', {
                notification_ids: ids,
            });
            setNotifications(prev =>
                prev.map(n => ids.includes(n.id) ? { ...n, is_read: true } : n)
            );
            setSelectedIds(new Set());
        } catch (err) {
            console.error('Failed to mark selected as read:', err);
        }
    };

    const markAllAsRead = async () => {
        const unreadIds = inboxList.map(n => n.id);
        if (unreadIds.length === 0) return;
        try {
            await api.post('/messages/notifications/mark-read', {
                notification_ids: unreadIds,
            });
            setNotifications(prev =>
                prev.map(n => unreadIds.includes(n.id) ? { ...n, is_read: true } : n)
            );
            setSelectedIds(new Set());
        } catch (err) {
            console.error('Failed to mark all as read:', err);
        }
    };

    const deleteNotification = async (notificationId) => {
        try {
            await api.delete(`/messages/notifications/${notificationId}`);
            setNotifications(prev => prev.filter(n => n.id !== notificationId));
            setSelectedIds(prev => {
                const next = new Set(prev);
                next.delete(notificationId);
                return next;
            });
        } catch (err) {
            console.error('Failed to delete notification:', err);
        }
    };

    const handleAction = (notification) => {
        const type = notification.notification_type || notification.type || '';
        if (type === 'ROUND2_INVITED' && notification.meta_json?.pipeline_id) {
            navigate(`/dashboard/round2/${notification.meta_json.pipeline_id}`);
        }
        if (type === 'MESSAGE') {
            navigate('/dashboard/messages');
        }
    };

    /* ── Selection helpers ──────────────────────────────────────────── */

    const toggleSelect = (id) => {
        setSelectedIds(prev => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    };

    /* ── Render ─────────────────────────────────────────────────────── */

    const renderSkeleton = () => (
        <div className="notif-list-container">
            {[1, 2, 3, 4].map(i => (
                <div className="notif-skeleton" key={i}>
                    <div className="notif-skeleton-checkbox" />
                    <div className="notif-skeleton-avatar" />
                    <div className="notif-skeleton-content">
                        <div className="notif-skeleton-line medium" />
                        <div className="notif-skeleton-line long" />
                        <div className="notif-skeleton-line short" />
                    </div>
                </div>
            ))}
        </div>
    );

    return (
        <div className="dashboard-content">
            <div className="notif-page">

                {/* Page Header */}
                <div className="page-header slide-in-left">
                    <h1 className="gradient-text">Notifications</h1>
                    <p>Stay updated with your interview status and feedback</p>
                </div>

                {/* Error */}
                {error && (
                    <div className="alert alert-error" style={{ marginBottom: '16px' }}>
                        {error}
                    </div>
                )}

                {/* Tabs Bar */}
                <div className="notif-tabs-bar fade-in-up">
                    <div className="notif-tabs">
                        <button
                            className={`notif-tab ${activeTab === 'inbox' ? 'active' : ''}`}
                            onClick={() => { setActiveTab('inbox'); setSelectedIds(new Set()); }}
                        >
                            <FiInbox style={{ marginRight: 6, verticalAlign: 'middle' }} />
                            Inbox
                            {inboxList.length > 0 && (
                                <span className="notif-tab-count">{inboxList.length}</span>
                            )}
                        </button>
                        <button
                            className={`notif-tab ${activeTab === 'read' ? 'active' : ''}`}
                            onClick={() => { setActiveTab('read'); setSelectedIds(new Set()); }}
                        >
                            <FiCheckCircle style={{ marginRight: 6, verticalAlign: 'middle' }} />
                            Read
                            {readList.length > 0 && (
                                <span className="notif-tab-count">{readList.length}</span>
                            )}
                        </button>
                    </div>

                    {activeTab === 'inbox' && (
                        <button
                            className="notif-mark-read"
                            onClick={selectedIds.size > 0 ? markSelectedAsRead : markAllAsRead}
                            disabled={inboxList.length === 0}
                        >
                            {selectedIds.size > 0
                                ? `Mark ${selectedIds.size} as read`
                                : 'Mark all as read'
                            }
                        </button>
                    )}
                </div>

                {/* List */}
                {loading ? (
                    renderSkeleton()
                ) : currentList.length === 0 ? (
                    <div className="notif-empty fade-in-up">
                        <div className="notif-empty-icon">
                            <FiBell />
                        </div>
                        <h3>
                            {activeTab === 'inbox'
                                ? 'All caught up!'
                                : 'No read notifications'}
                        </h3>
                        <p>
                            {activeTab === 'inbox'
                                ? "You don't have any unread notifications. Check back later for updates."
                                : 'Read notifications will appear here.'}
                        </p>
                    </div>
                ) : (
                    <div className="notif-list-container fade-in-up">
                        <div className="notif-list">
                            {currentList.map(notification => (
                                <NotificationItem
                                    key={notification.id}
                                    notification={notification}
                                    checked={selectedIds.has(notification.id)}
                                    onCheck={toggleSelect}
                                    onMarkRead={markAsRead}
                                    onDelete={deleteNotification}
                                    onAction={handleAction}
                                />
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
