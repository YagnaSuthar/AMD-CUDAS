import { useState, useEffect } from 'react';
import { useAuth } from '../../../../context/AuthContext';
import api from '../../../../utils/api';
import ComposeMessageModal from '../../../../components/ComposeMessageModal';
import {
    FiPlus, FiSend, FiUsers, FiClock, FiCheckCircle,
    FiInbox, FiMessageSquare, FiCalendar
} from 'react-icons/fi';
import SkeletonText from '../../../../components/common/skeleton/SkeletonText';

export default function CollegeMessages() {
    const { user } = useAuth();
    const [messages, setMessages] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [composeOpen, setComposeOpen] = useState(false);

    const fetchSentMessages = async () => {
        try {
            setLoading(true);
            setError('');
            const res = await api.get('/messages/sent');
            setMessages(res.data || []);
        } catch (err) {
            setError(err?.response?.data?.detail || 'Failed to load messages');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSentMessages();
    }, []);

    const handleSent = () => {
        fetchSentMessages();
    };

    const getRoleLabel = (role) => {
        const map = {
            'STUDENT': 'Students',
            'FACULTY': 'Faculty',
            'HOD': 'HODs',
            'COLLEGE_PRINCIPAL': 'Principal',
        };
        return map[role] || role;
    };

    const relativeTime = (dateStr) => {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        const now = new Date();
        const diffMs = now - d;
        const mins = Math.floor(diffMs / 60000);
        if (mins < 1) return 'Just now';
        if (mins < 60) return `${mins}m ago`;
        const hours = Math.floor(mins / 60);
        if (hours < 24) return `${hours}h ago`;
        const days = Math.floor(hours / 24);
        if (days === 1) return 'Yesterday';
        if (days < 7) return `${days}d ago`;
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    };

    return (
        <div className="dashboard-content">
            {/* Header */}
            <div className="college-msg-header slide-in-left">
                <div>
                    <h1 className="gradient-text">Messages</h1>
                    <p style={{ color: 'var(--color-text-secondary)', marginTop: 4 }}>
                        Send messages to students, faculty, and other roles
                    </p>
                </div>
                <button className="college-msg-new-btn" onClick={() => setComposeOpen(true)}>
                    <FiPlus size={18} />
                    New Message
                </button>
            </div>

            {error && (
                <div className="alert alert-error fade-in" style={{ marginBottom: 16 }}>
                    {error}
                </div>
            )}

            {/* Sent Messages */}
            <div className="fade-in-up">
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginBottom: 16,
                }}>
                    <h3 style={{
                        fontFamily: 'var(--font-heading)',
                        fontSize: '0.95rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                        color: 'var(--color-text-primary)',
                    }}>
                        <FiInbox size={18} />
                        Sent Messages
                        <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            minWidth: 28,
                            height: 24,
                            padding: '0 8px',
                            borderRadius: 'var(--radius-full)',
                            background: 'rgba(0, 188, 212, 0.12)',
                            color: 'var(--color-secondary)',
                            fontSize: '0.75rem',
                            fontWeight: 700,
                            fontFamily: 'var(--font-heading)',
                        }}>
                            {messages.length}
                        </span>
                    </h3>
                </div>

                {loading ? (
                    <div className="college-msg-list">
                        {Array.from({ length: 3 }).map((_, i) => (
                            <div key={i} className="college-msg-card" style={{ opacity: 1 }}>
                                <div className="college-msg-card-top">
                                    <SkeletonText variant="title" style={{ width: 200 }} />
                                    <SkeletonText style={{ width: 80 }} />
                                </div>
                                <SkeletonText style={{ width: '90%', marginTop: 8 }} />
                                <SkeletonText style={{ width: '60%', marginTop: 4 }} />
                            </div>
                        ))}
                    </div>
                ) : messages.length === 0 ? (
                    <div style={{
                        textAlign: 'center',
                        padding: '60px 24px',
                        color: 'var(--color-text-muted)',
                    }}>
                        <FiMessageSquare size={48} style={{ marginBottom: 16, opacity: 0.4 }} />
                        <p style={{ fontSize: '1rem', fontWeight: 500, color: 'var(--color-text-secondary)' }}>
                            No messages sent yet
                        </p>
                        <p style={{ fontSize: '0.85rem', marginTop: 4 }}>
                            Click "+ New Message" to compose your first message
                        </p>
                    </div>
                ) : (
                    <div className="college-msg-list">
                        {messages.map((msg, idx) => (
                            <div
                                key={msg.id}
                                className="college-msg-card"
                                style={{ animationDelay: `${idx * 0.06}s` }}
                            >
                                <div className="college-msg-card-top">
                                    <div className="college-msg-card-subject">{msg.subject}</div>
                                    <div className="college-msg-card-meta">
                                        {msg.receiver_role && (
                                            <span className="college-msg-card-role">
                                                → {getRoleLabel(msg.receiver_role)}
                                            </span>
                                        )}
                                        <span className="college-msg-card-time">
                                            <FiClock size={12} />
                                            {relativeTime(msg.created_at)}
                                        </span>
                                    </div>
                                </div>

                                <div
                                    className="college-msg-card-body"
                                    dangerouslySetInnerHTML={{ __html: msg.body }}
                                />

                                <div className="college-msg-card-stats">
                                    <div className="college-msg-stat">
                                        <FiUsers size={14} />
                                        Sent to: <span className="stat-val">{msg.recipient_count}</span>
                                    </div>
                                    {msg.semester_id && (
                                        <div className="college-msg-stat">
                                            <FiCalendar size={14} />
                                            Semester: <span className="stat-val">{msg.semester_id}</span>
                                        </div>
                                    )}
                                    <div className="college-msg-stat">
                                        <FiCheckCircle size={14} />
                                        Read: <span className="stat-val">{msg.read_count}</span> / {msg.recipient_count}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Compose Modal */}
            <ComposeMessageModal
                isOpen={composeOpen}
                onClose={() => setComposeOpen(false)}
                onSent={handleSent}
            />
        </div>
    );
}
