import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { FiBell, FiCheck, FiX } from 'react-icons/fi';
import SkeletonListItem from './common/skeleton/SkeletonListItem';

export default function Notifications() {
    const { user } = useAuth();
    const hasNotifications = ['STUDENT', 'COLLEGE_PRINCIPAL', 'HOD', 'FACULTY'].includes(user?.role);

    const [open, setOpen] = useState(false);
    const [notifications, setNotifications] = useState([]);
    const [unreadCount, setUnreadCount] = useState(0);
    const [loading, setLoading] = useState(false);
    const dropdownRef = useRef(null);

    const fetchNotifications = async () => {
        if (!hasNotifications) return;
        try {
            setLoading(true);
            const res = await api.get('/messages/notifications');
            setNotifications(res.data.notifications || []);
            setUnreadCount(res.data.unread_count || 0);
        } catch (err) {
            console.error('Failed to fetch notifications', err);
        } finally {
            setLoading(false);
        }
    };

    const markAsRead = async (notificationIds) => {
        if (!isStudent || notificationIds.length === 0) return;
        try {
            await api.post('/messages/notifications/mark-read', { notification_ids: notificationIds });
            // Optimistically update UI
            setNotifications((prev) =>
                prev.map((n) =>
                    notificationIds.includes(n.id) ? { ...n, is_read: true } : n
                )
            );
            setUnreadCount((prev) => Math.max(0, prev - notificationIds.length));
        } catch (err) {
            console.error('Failed to mark notifications as read', err);
        }
    };

    const markAllAsRead = () => {
        const unreadIds = notifications.filter((n) => !n.is_read).map((n) => n.id);
        if (unreadIds.length > 0) markAsRead(unreadIds);
    };

    useEffect(() => {
        if (isStudent) fetchNotifications();
    }, [isStudent]);

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    if (!isStudent) return null;

    return (
        <div className="notifications-wrapper" ref={dropdownRef}>
            <button
                className="icon-button notifications-bell"
                onClick={() => setOpen(!open)}
                aria-label="Notifications"
            >
                <FiBell size={20} />
                {unreadCount > 0 && <span className="badge badge-danger">{unreadCount}</span>}
            </button>

            {open && (
                <div className="notifications-dropdown">
                    <div className="notifications-header">
                        <h5>Notifications</h5>
                        {notifications.some((n) => !n.is_read) && (
                            <button className="btn-link" onClick={markAllAsRead}>
                                Mark all read
                            </button>
                        )}
                    </div>
                    <div className="notifications-list">
                        {loading ? (
                            <div>
                                {Array.from({ length: 3 }).map((_, i) => (
                                    <SkeletonListItem key={i} style={{ borderBottom: '1px solid var(--color-border)' }} />
                                ))}
                            </div>
                        ) : notifications.length === 0 ? (
                            <p className="notifications-empty">No notifications</p>
                        ) : (
                            notifications.map((notif) => (
                                <div
                                    key={notif.id}
                                    className={`notification-item ${!notif.is_read ? 'unread' : ''}`}
                                >
                                    <div className="notification-content">
                                        <div className="notification-title">{notif.title}</div>
                                        <div className="notification-message">{notif.message}</div>
                                        <div className="notification-time">
                                            {new Date(notif.created_at).toLocaleString()}
                                        </div>
                                    </div>
                                    <div className="notification-actions">
                                        {!notif.is_read && (
                                            <button
                                                className="btn-icon"
                                                onClick={() => markAsRead([notif.id])}
                                                title="Mark as read"
                                            >
                                                <FiCheck />
                                            </button>
                                        )}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
