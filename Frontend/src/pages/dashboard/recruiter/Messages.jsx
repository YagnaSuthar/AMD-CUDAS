import { useEffect, useState } from 'react';
import { useAuth } from '../../../context/AuthContext';
import api from '../../../utils/api';
import { FiSend, FiInbox, FiMail, FiClock, FiCheck, FiUser, FiMessageSquare } from 'react-icons/fi';
import SkeletonText from '../../../components/common/skeleton/SkeletonText';
import SkeletonAvatar from '../../../components/common/skeleton/SkeletonAvatar';

export default function Messages() {
    const { user } = useAuth();
    const isRecruiter = user?.role === 'RECRUITER';

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const [messages, setMessages] = useState([]);
    const [subject, setSubject] = useState('');
    const [body, setBody] = useState('');
    const [recipientEmail, setRecipientEmail] = useState('');

    // College message state
    const [collegeSubject, setCollegeSubject] = useState('');
    const [collegeBody, setCollegeBody] = useState('');
    const [collegePrincipalEmail, setCollegePrincipalEmail] = useState('');

    const [activeTab, setActiveTab] = useState('student');
    const [sendingStudent, setSendingStudent] = useState(false);
    const [sendingCollege, setSendingCollege] = useState(false);

    const canSend = isRecruiter;

    const fetchMessages = async () => {
        try {
            setError('');
            setLoading(true);
            const res = await api.get('/messages/');
            setMessages(res.data || []);
        } catch (err) {
            setError('Failed to load messages');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (isRecruiter) fetchMessages();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isRecruiter]);

    const onSendStudent = async (e) => {
        e.preventDefault();
        if (!canSend || !recipientEmail || !subject.trim() || !body.trim()) return;

        try {
            setError('');
            setSendingStudent(true);
            await api.post('/messages/send', {
                recipient_email: recipientEmail,
                subject: subject.trim(),
                body: body.trim(),
            });
            setSubject('');
            setBody('');
            setRecipientEmail('');
            await fetchMessages();
        } catch (err) {
            setError(err?.response?.data?.detail || err?.message || 'Failed to send message');
        } finally {
            setSendingStudent(false);
        }
    };

    const onSendCollege = async (e) => {
        e.preventDefault();
        if (!canSend || !collegePrincipalEmail || !collegeSubject.trim() || !collegeBody.trim()) return;

        try {
            setError('');
            setSendingCollege(true);
            await api.post('/messages/send', {
                recipient_email: collegePrincipalEmail,
                subject: collegeSubject.trim(),
                body: collegeBody.trim(),
            });
            setCollegeSubject('');
            setCollegeBody('');
            setCollegePrincipalEmail('');
            await fetchMessages();
        } catch (err) {
            setError(err?.response?.data?.detail || err?.message || 'Failed to send message to college');
        } finally {
            setSendingCollege(false);
        }
    };

    if (!isRecruiter) {
        return (
            <div className="dashboard-page">
                <div className="page-header slide-in-left">
                    <h1 className="gradient-text">Messages</h1>
                </div>
                <div className="empty-state">
                    <FiInbox size={48} />
                    <p>Only recruiters can send messages.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="dashboard-content">
            <div className="page-header slide-in-left">
                <h1 className="gradient-text">Messages</h1>
                <p style={{ color: 'var(--color-text-secondary)' }}>
                    Send messages to students and colleges
                </p>
            </div>

            {error && (
                <div className="alert alert-error fade-in" style={{ marginBottom: '16px' }}>
                    {error}
                </div>
            )}

            <div className="messages-grid">
                {/* Left Panel â€” Compose */}
                <div className="messages-compose-panel fade-in-up">
                    {/* Tab Switcher */}
                    <div className="msg-tab-switcher">
                        <button
                            className={`msg-tab ${activeTab === 'student' ? 'msg-tab-active' : ''}`}
                            onClick={() => setActiveTab('student')}
                        >
                            <FiUser size={16} />
                            <span>To Student</span>
                        </button>
                        <button
                            className={`msg-tab ${activeTab === 'college' ? 'msg-tab-active' : ''}`}
                            onClick={() => setActiveTab('college')}
                        >
                            <FiMessageSquare size={16} />
                            <span>To College</span>
                        </button>
                    </div>

                    {/* Student Message Form */}
                    {activeTab === 'student' && (
                        <form onSubmit={onSendStudent} className="msg-compose-form fade-in">
                            <div className="msg-compose-header">
                                <div className="msg-compose-icon">
                                    <FiMail size={20} />
                                </div>
                                <div>
                                    <h3>Send to Student</h3>
                                    <p>Message will appear in the student's inbox</p>
                                </div>
                            </div>

                            <div className="msg-field">
                                <label>Student Email</label>
                                <div className="msg-input-wrapper">
                                    <FiUser className="msg-input-icon" />
                                    <input
                                        type="email"
                                        value={recipientEmail}
                                        onChange={(e) => setRecipientEmail(e.target.value)}
                                        placeholder="Enter student email"
                                        required
                                    />
                                </div>
                            </div>

                            <div className="msg-field">
                                <label>Subject</label>
                                <div className="msg-input-wrapper">
                                    <FiMail className="msg-input-icon" />
                                    <input
                                        type="text"
                                        value={subject}
                                        onChange={(e) => setSubject(e.target.value)}
                                        placeholder="Message subject"
                                        required
                                    />
                                </div>
                            </div>

                            <div className="msg-field">
                                <label>Message</label>
                                <textarea
                                    value={body}
                                    onChange={(e) => setBody(e.target.value)}
                                    placeholder="Type your message here..."
                                    rows={5}
                                    required
                                />
                            </div>

                            <button
                                type="submit"
                                className="msg-send-btn"
                                disabled={sendingStudent || !recipientEmail || !subject.trim() || !body.trim()}
                            >
                                <FiSend size={16} />
                                {sendingStudent ? 'Sending...' : 'Send Message'}
                            </button>
                        </form>
                    )}

                    {/* College Message Form */}
                    {activeTab === 'college' && (
                        <form onSubmit={onSendCollege} className="msg-compose-form fade-in">
                            <div className="msg-compose-header">
                                <div className="msg-compose-icon" style={{ background: 'var(--gradient-secondary, linear-gradient(135deg, #a87ef0, #7c3aed))' }}>
                                    <FiMessageSquare size={20} />
                                </div>
                                <div>
                                    <h3>Send to College</h3>
                                    <p>Message will appear in the principal's dashboard</p>
                                </div>
                            </div>

                            <div className="msg-field">
                                <label>Principal Email</label>
                                <div className="msg-input-wrapper">
                                    <FiUser className="msg-input-icon" />
                                    <input
                                        type="email"
                                        value={collegePrincipalEmail}
                                        onChange={(e) => setCollegePrincipalEmail(e.target.value)}
                                        placeholder="Enter principal's email"
                                        required
                                    />
                                </div>
                            </div>

                            <div className="msg-field">
                                <label>Subject</label>
                                <div className="msg-input-wrapper">
                                    <FiMail className="msg-input-icon" />
                                    <input
                                        type="text"
                                        value={collegeSubject}
                                        onChange={(e) => setCollegeSubject(e.target.value)}
                                        placeholder="Message subject"
                                        required
                                    />
                                </div>
                            </div>

                            <div className="msg-field">
                                <label>Message</label>
                                <textarea
                                    value={collegeBody}
                                    onChange={(e) => setCollegeBody(e.target.value)}
                                    placeholder="Type your message to the college..."
                                    rows={5}
                                    required
                                />
                            </div>

                            <button
                                type="submit"
                                className="msg-send-btn msg-send-btn-college"
                                disabled={sendingCollege || !collegePrincipalEmail || !collegeSubject.trim() || !collegeBody.trim()}
                            >
                                <FiSend size={16} />
                                {sendingCollege ? 'Sending...' : 'Send to College'}
                            </button>
                        </form>
                    )}
                </div>

                {/* Right Panel â€” Sent Messages */}
                <div className="messages-sent-panel fade-in-up fade-in-delay-2">
                    <div className="msg-sent-header">
                        <h3>
                            <FiInbox size={18} />
                            Sent Messages
                        </h3>
                        <span className="msg-count">{messages.length}</span>
                    </div>

                    <div className="msg-list">
                        {loading ? (
                            <div>
                                {Array.from({ length: 4 }).map((_, i) => (
                                   <div key={i} className="msg-card skeleton-card">
                                        <div className="msg-card-top">
                                            <SkeletonAvatar size="sm" />
                                            <div className="msg-card-info" style={{ flex: 1 }}>
                                                <SkeletonText variant="title" style={{ width: '100px', marginBottom: '8px' }} />
                                                <SkeletonText style={{ width: '200px' }} />
                                            </div>
                                            <SkeletonText style={{ width: '60px', height: '20px' }} />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : messages.length === 0 ? (
                            <div className="msg-empty">
                                <FiInbox size={40} />
                                <p>No messages sent yet</p>
                                <span>Your sent messages will appear here</span>
                            </div>
                        ) : (
                            messages.map((msg, idx) => (
                                <div
                                    key={msg.id}
                                    className="msg-card"
                                    style={{ animationDelay: `${idx * 0.06}s` }}
                                >
                                    <div className="msg-card-top">
                                        <div className="msg-avatar">
                                            {(msg.recipient_id || '?').charAt(0).toUpperCase()}
                                        </div>
                                        <div className="msg-card-info">
                                            <div className="msg-card-to">{msg.recipient_id}</div>
                                            <div className="msg-card-subject">{msg.subject}</div>
                                        </div>
                                        <span className={`msg-status ${msg.is_read ? 'msg-status-read' : 'msg-status-unread'}`}>
                                            {msg.is_read ? <FiCheck size={12} /> : <FiClock size={12} />}
                                            {msg.is_read ? 'Read' : 'Unread'}
                                        </span>
                                    </div>
                                    <div className="msg-card-time">
                                        <FiClock size={12} />
                                        {new Date(msg.created_at).toLocaleString()}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
