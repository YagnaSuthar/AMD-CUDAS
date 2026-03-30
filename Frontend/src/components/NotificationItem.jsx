import {
    FiCheck, FiX, FiClock, FiMessageSquare,
    FiArrowRight, FiTrendingUp, FiCpu
} from 'react-icons/fi';
import { FaRobot } from 'react-icons/fa';

/**
 * Determine notification visual type from the raw notification_type / type field.
 * Returns { category, avatarClass, typeBadge, Icon, actionLabel, actionClass }
 */
function getNotifMeta(notification) {
    const type = notification.notification_type || notification.type || '';

    switch (type) {
        case 'MESSAGE':
            return {
                category: 'message',
                avatarClass: '',           // will use person avatar / initials
                typeBadge: 'Message',
                Icon: FiMessageSquare,
                actionLabel: 'Reply',
                actionClass: 'btn-reply',
            };

        case 'AI_ASSIGNED':
            return {
                category: 'ai',
                avatarClass: 'ai',
                typeBadge: 'AI Interview',
                Icon: FaRobot,
                actionLabel: 'Check the effect',
                actionClass: 'btn-cta',
            };

        case 'ROUND2_INVITED':
            return {
                category: 'round2',
                avatarClass: 'system',
                typeBadge: 'Round 2',
                Icon: FiArrowRight,
                actionLabel: 'Go to Workspace',
                actionClass: 'btn-go',
            };

        case 'HIRED':
            return {
                category: 'hired',
                avatarClass: 'analytics',
                typeBadge: 'Hired',
                Icon: FiTrendingUp,
                actionLabel: 'Go to Dashboard',
                actionClass: 'btn-dashboard',
            };

        default:
            return {
                category: 'system',
                avatarClass: 'system',
                typeBadge: null,
                Icon: FiMessageSquare,
                actionLabel: null,
                actionClass: 'btn-cta',
            };
    }
}

/**
 * Extract display-friendly sender name from notification fields.
 */
function getSenderName(notification) {
    if (notification.sender_name) return notification.sender_name;
    if (notification.title) return notification.title;
    if (notification.subject) return notification.subject;
    return 'System';
}

/**
 * Build initials from a name string (up to 2 chars).
 */
function initials(name) {
    if (!name) return '?';
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return parts[0].slice(0, 2).toUpperCase();
}

/**
 * Pretty relative timestamp.
 */
function relativeTime(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now - d;
    const mins = Math.floor(diffMs / 60000);
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}min ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days}d ago`;

    return d.toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
    });
}

function fullTimestamp(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    const time = d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
    const date = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    return `${time}, ${date}`;
}

export default function NotificationItem({
    notification,
    checked,
    onCheck,
    onMarkRead,
    onDelete,
    onAction,
}) {
    const meta = getNotifMeta(notification);
    const senderName = getSenderName(notification);
    const messageText = notification.message || notification.body || '';
    const isUnread = !notification.is_read;
    const isAI = meta.category === 'ai';
    const isPersonMessage = meta.category === 'message';

    // For AI notifications, show a robot icon avatar.
    // For person messages, show initials or profile image.
    // For system / promo / analytics, show an icon avatar.

    const renderAvatar = () => {
        if (isAI) {
            return (
                <div className="notif-avatar">
                    <div className="notif-avatar-icon ai">
                        <FaRobot />
                    </div>
                </div>
            );
        }

        if (isPersonMessage && notification.sender_avatar) {
            return (
                <div className="notif-avatar">
                    <img src={notification.sender_avatar} alt={senderName} />
                </div>
            );
        }

        if (isPersonMessage) {
            return (
                <div className="notif-avatar">
                    <div className="notif-avatar-initials">
                        {initials(senderName)}
                    </div>
                </div>
            );
        }

        // System / promo / analytics — icon circle
        return (
            <div className="notif-avatar">
                <div className={`notif-avatar-icon ${meta.avatarClass}`}>
                    <meta.Icon />
                </div>
            </div>
        );
    };

    const renderAction = () => {
        // Round 2 special action
        if (meta.category === 'round2' && notification.meta_json?.pipeline_id) {
            return (
                <button
                    className={`notif-action-btn ${meta.actionClass}`}
                    onClick={() => onAction && onAction(notification)}
                >
                    Start Round 2
                    <FiArrowRight />
                </button>
            );
        }

        if (meta.actionLabel) {
            return (
                <button
                    className={`notif-action-btn ${meta.actionClass}`}
                    onClick={() => onAction && onAction(notification)}
                >
                    {meta.actionLabel}
                </button>
            );
        }
        return null;
    };

    return (
        <div className={`notif-item ${isUnread ? 'unread' : ''} fade-in-up`}>
            {/* Checkbox */}
            <div className="notif-checkbox-wrap">
                <input
                    type="checkbox"
                    className="notif-checkbox"
                    checked={checked}
                    onChange={() => onCheck && onCheck(notification.id)}
                />
            </div>

            {/* Avatar */}
            {renderAvatar()}

            {/* Content */}
            <div className="notif-content">
                <div className="notif-sender">
                    {senderName}
                    {meta.typeBadge && (
                        <span className={`notif-type-badge ${meta.category}`}>
                            {meta.typeBadge}
                        </span>
                    )}
                </div>

                <div className="notif-message">{messageText}</div>

                <div className="notif-timestamp">
                    <FiClock size={12} />
                    <span title={fullTimestamp(notification.created_at)}>
                        {relativeTime(notification.created_at)}
                        {' · '}
                        {fullTimestamp(notification.created_at)}
                    </span>
                </div>

                {/* Message preview box for MESSAGE type */}
                {isPersonMessage && notification.preview && (
                    <div className="notif-preview-box">
                        <span className="notif-preview-text">
                            {notification.preview}
                        </span>
                    </div>
                )}

                {/* Scheduled info for Round 2 */}
                {meta.category === 'round2' && notification.meta_json?.round2_scheduled_at && (
                    <div className="notif-scheduled">
                        <FiClock size={14} />
                        Scheduled: {new Date(notification.meta_json.round2_scheduled_at).toLocaleString()}
                    </div>
                )}
            </div>

            {/* Right side: Action + Utils */}
            <div className="notif-action-area">
                {renderAction()}

                <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                    {isUnread && (
                        <button
                            className="notif-icon-btn mark-read"
                            title="Mark as read"
                            onClick={() => onMarkRead && onMarkRead(notification.id)}
                        >
                            <FiCheck />
                        </button>
                    )}
                    <button
                        className="notif-icon-btn delete"
                        title="Delete"
                        onClick={() => onDelete && onDelete(notification.id)}
                    >
                        <FiX />
                    </button>

                    {/* Unread dot */}
                    {isUnread && <div className="notif-unread-dot" />}
                </div>
            </div>
        </div>
    );
}
