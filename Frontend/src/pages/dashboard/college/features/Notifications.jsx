import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../../context/AuthContext';
import api from '../../../../utils/api';
import NotificationItem from '../../../../components/NotificationItem';
import { FiBell, FiInbox, FiCheckCircle, FiStar, FiCpu, FiBriefcase } from 'react-icons/fi';
import { FaSchool } from 'react-icons/fa';

const TABS = [
    { key: 'college', label: 'College', Icon: FaSchool },
    { key: 'ai', label: 'AI Agent', Icon: FiCpu },
    { key: 'recruiter', label: 'Recruiter', Icon: FiBriefcase },
    { key: 'starred', label: 'Starred', Icon: FiStar },
    { key: 'read', label: 'Read', Icon: FiCheckCircle },
];

export default function Notifications() {
    const { user } = useAuth();
    const navigate = useNavigate();

    const [notifications, setNotifications] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [activeTab, setActiveTab] = useState('college');
    const [selectedIds, setSelectedIds] = useState(new Set());

    /* ── Fetch ──────────────────────────────────────────────────────────── */

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

    /* ── Categorized lists ─────────────────────────────────────────────── */

    const collegeList = useMemo(
        () => notifications.filter(n =>
            !n.is_read && (
                n.notification_type === 'COLLEGE_MESSAGE' ||
                ['COLLEGE_PRINCIPAL', 'HOD', 'FACULTY'].includes(n.sender_role) ||
                (n.meta_json?.sender_role && ['COLLEGE_PRINCIPAL', 'HOD', 'FACULTY'].includes(n.meta_json.sender_role))
            )
        ),
        [notifications]
    );

    const aiList = useMemo(
        () => notifications.filter(n =>
            !n.is_read && n.notification_type === 'AI_ASSIGNED'
        ),
        [notifications]
    );

    const recruiterList = useMemo(
        () => notifications.filter(n =>
            !n.is_read && (
                n.sender_role === 'RECRUITER' ||
                (n.notification_type === 'MESSAGE' && !['COLLEGE_PRINCIPAL', 'HOD', 'FACULTY'].includes(n.sender_role)) ||
                n.notification_type === 'ROUND2_INVITED' ||
                n.notification_type === 'HIRED'
            )
        ),
        [notifications]
    );

    const starredList = useMemo(
        () => notifications.filter(n => n.is_starred),
        [notifications]
    );

    const readList = useMemo(
        () => notifications.filter(n => n.is_read),
        [notifications]
    );

    const tabCounts = {
        college: collegeList.length,
        ai: aiList.length,
        recruiter: recruiterList.length,
        starred: starredList.length,
        read: readList.length,
    };

    const currentList = {
        college: collegeList,
        ai: aiList,
        recruiter: recruiterList,
        starred: starredList,
        read: readList,
    }[activeTab] || [];

    /* ── Actions ────────────────────────────────────────────────────────── */

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

    const markAsUnread = async (notificationId) => {
        try {
            await api.put(`/messages/notifications/${notificationId}/unread`);
            setNotifications(prev =>
                prev.map(n => n.id === notificationId ? { ...n, is_read: false, read_at: null } : n)
            );
        } catch (err) {
            console.error('Failed to mark as unread:', err);
        }
    };

    const toggleStar = async (notificationId) => {
        const notif = notifications.find(n => n.id === notificationId);
        if (!notif) return;
        const newStarred = !notif.is_starred;
        try {
            await api.put(`/messages/notifications/${notificationId}/star`, {
                is_starred: newStarred,
            });
            setNotifications(prev =>
                prev.map(n => n.id === notificationId ? { ...n, is_starred: newStarred } : n)
            );
        } catch (err) {
            console.error('Failed to toggle star:', err);
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
        const unreadIds = notifications.filter(n => !n.is_read).map(n => n.id);
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
        if (type === 'MESSAGE' || type === 'COLLEGE_MESSAGE') {
            // Auto-mark as read when viewing
            if (!notification.is_read) markAsRead(notification.id);
        }
    };

    /* ── Selection helpers ──────────────────────────────────────────────── */

    const toggleSelect = (id) => {
        setSelectedIds(prev => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    };

    /* ── Render ─────────────────────────────────────────────────────────── */

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
                    <p>Stay updated with messages, interviews, and more</p>
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
                        {TABS.map(tab => (
                            <button
                                key={tab.key}
                                className={`notif-tab ${activeTab === tab.key ? 'active' : ''}`}
                                onClick={() => { setActiveTab(tab.key); setSelectedIds(new Set()); }}
                            >
                                <tab.Icon style={{ marginRight: 6, verticalAlign: 'middle' }} size={14} />
                                {tab.label}
                                {tabCounts[tab.key] > 0 && (
                                    <span className="notif-tab-count">{tabCounts[tab.key]}</span>
                                )}
                            </button>
                        ))}
                    </div>

                    {!['starred', 'read'].includes(activeTab) && (
                        <button
                            className="notif-mark-read"
                            onClick={selectedIds.size > 0 ? markSelectedAsRead : markAllAsRead}
                            disabled={currentList.filter(n => !n.is_read).length === 0}
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
                            {activeTab === 'starred'
                                ? 'No starred messages'
                                : activeTab === 'read'
                                ? 'No read notifications'
                                : activeTab === 'college'
                                ? 'No college messages'
                                : activeTab === 'ai'
                                ? 'No AI notifications'
                                : 'No recruiter messages'
                            }
                        </h3>
                        <p>
                            {activeTab === 'starred'
                                ? 'Star important messages to find them here.'
                                : activeTab === 'read'
                                ? 'Read notifications will appear here.'
                                : 'New messages will appear here when received.'
                            }
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
                                    onMarkUnread={markAsUnread}
                                    onToggleStar={toggleStar}
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
