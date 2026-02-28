import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { FiSend, FiInbox, FiUser } from 'react-icons/fi';

export default function Messages() {
    const { user } = useAuth();
    const isRecruiter = user?.role === 'RECRUITER';

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const [messages, setMessages] = useState([]);
    const [subject, setSubject] = useState('');
    const [body, setBody] = useState('');
    const [recipientId, setRecipientId] = useState('');

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

    const onSend = async (e) => {
        e.preventDefault();
        if (!canSend || !recipientId || !subject.trim() || !body.trim()) return;

        try {
            setError('');
            await api.post('/messages/send', {
                recipient_id: recipientId,
                subject: subject.trim(),
                body: body.trim(),
            });
            setSubject('');
            setBody('');
            setRecipientId('');
            await fetchMessages();
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to send message');
        }
    };

    if (!isRecruiter) {
        return (
            <div className="dashboard-page">
                <div className="page-header">
                    <h2>Messages</h2>
                </div>
                <div className="empty-state">
                    <FiInbox size={48} />
                    <p>Only recruiters can send messages.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="dashboard-page">
            <div className="page-header">
                <h2>Messages</h2>
                <p>Send messages to students</p>
            </div>

            {error && <div className="alert alert-danger">{error}</div>}

            <div className="card">
                <div className="card-header">
                    <h4>Send New Message</h4>
                </div>
                <form onSubmit={onSend} className="card-body">
                    <div className="form-group">
                        <label className="form-label">Student ID (UUID)</label>
                        <input
                            type="text"
                            className="form-input"
                            value={recipientId}
                            onChange={(e) => setRecipientId(e.target.value)}
                            placeholder="Enter student UUID"
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Subject</label>
                        <input
                            type="text"
                            className="form-input"
                            value={subject}
                            onChange={(e) => setSubject(e.target.value)}
                            placeholder="Message subject"
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Message</label>
                        <textarea
                            className="form-input"
                            rows={5}
                            value={body}
                            onChange={(e) => setBody(e.target.value)}
                            placeholder="Type your message here..."
                            required
                        />
                    </div>
                    <button type="submit" className="btn btn-primary">
                        <FiSend /> Send Message
                    </button>
                </form>
            </div>

            <div className="card" style={{ marginTop: '2rem' }}>
                <div className="card-header">
                    <h4>Sent Messages</h4>
                </div>
                <div className="card-body">
                    {loading ? (
                        <p>Loading...</p>
                    ) : messages.length === 0 ? (
                        <p>No messages sent yet.</p>
                    ) : (
                        <div className="table-responsive">
                            <table className="table">
                                <thead>
                                    <tr>
                                        <th>To</th>
                                        <th>Subject</th>
                                        <th>Sent At</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {messages.map((msg) => (
                                        <tr key={msg.id}>
                                            <td>{msg.recipient_id}</td>
                                            <td>{msg.subject}</td>
                                            <td>{new Date(msg.created_at).toLocaleString()}</td>
                                            <td>
                                                <span className={`badge ${msg.is_read ? 'badge-success' : 'badge-secondary'}`}>
                                                    {msg.is_read ? 'Read' : 'Unread'}
                                                </span>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
