import { useState, useEffect, useRef, useCallback } from 'react';
import api from '../utils/api';
import {
    FiX, FiUsers, FiUser, FiChevronRight, FiChevronLeft,
    FiSend, FiSearch, FiClock, FiPaperclip, FiSave,
    FiBold, FiItalic, FiUnderline, FiLink, FiList, FiImage
} from 'react-icons/fi';
import { FaGraduationCap, FaChalkboardTeacher, FaUserTie, FaSchool } from 'react-icons/fa';

const ROLE_OPTIONS = [
    { key: 'STUDENT', label: 'Student', desc: 'Send to semester or specific students', Icon: FaGraduationCap },
    { key: 'FACULTY', label: 'Faculty', desc: 'Send to faculty members', Icon: FaChalkboardTeacher },
    { key: 'HOD', label: 'HOD', desc: 'Send to Head of Department', Icon: FaUserTie },
    { key: 'COLLEGE_PRINCIPAL', label: 'Principal', desc: 'Send to College Principal', Icon: FaSchool },
];

const SEMESTERS = [1, 2, 3, 4, 5, 6, 7, 8];

export default function ComposeMessageModal({ isOpen, onClose, onSent }) {
    // Steps: 1=role, 2=recipients, 3=compose
    const [step, setStep] = useState(1);

    // Step 1
    const [selectedRole, setSelectedRole] = useState('');

    // Step 2
    const [selectedSemester, setSelectedSemester] = useState(null);
    const [sendToAll, setSendToAll] = useState(true);
    const [recipients, setRecipients] = useState([]);
    const [selectedRecipients, setSelectedRecipients] = useState([]);
    const [searchTerm, setSearchTerm] = useState('');
    const [loadingRecipients, setLoadingRecipients] = useState(false);

    // Step 3
    const [subject, setSubject] = useState('');
    const [sending, setSending] = useState(false);
    const [error, setError] = useState('');
    const editorRef = useRef(null);

    // Reset on open/close
    useEffect(() => {
        if (isOpen) {
            setStep(1);
            setSelectedRole('');
            setSelectedSemester(null);
            setSendToAll(true);
            setRecipients([]);
            setSelectedRecipients([]);
            setSearchTerm('');
            setSubject('');
            setSending(false);
            setError('');
        }
    }, [isOpen]);

    // Fetch recipients
    const fetchRecipients = useCallback(async (role, semester, search) => {
        try {
            setLoadingRecipients(true);
            let url = `/messages/recipients?role=${role}`;
            if (semester) url += `&semester=${semester}`;
            if (search) url += `&search=${encodeURIComponent(search)}`;
            const res = await api.get(url);
            setRecipients(res.data.recipients || []);
        } catch (err) {
            console.error('Failed to fetch recipients:', err);
            setRecipients([]);
        } finally {
            setLoadingRecipients(false);
        }
    }, []);

    // Auto-fetch when step 2 params change
    useEffect(() => {
        if (step === 2 && selectedRole) {
            if (selectedRole === 'STUDENT' && selectedSemester) {
                fetchRecipients('STUDENT', selectedSemester, searchTerm);
            } else if (selectedRole !== 'STUDENT') {
                fetchRecipients(selectedRole, null, searchTerm);
            }
        }
    }, [step, selectedRole, selectedSemester, searchTerm, fetchRecipients]);

    const toggleRecipient = (id) => {
        setSelectedRecipients(prev =>
            prev.includes(id) ? prev.filter(r => r !== id) : [...prev, id]
        );
    };

    const canProceedStep1 = !!selectedRole;
    const canProceedStep2 = () => {
        if (selectedRole === 'STUDENT') {
            if (!selectedSemester) return false;
            return sendToAll || selectedRecipients.length > 0;
        }
        return sendToAll || selectedRecipients.length > 0;
    };

    const goToStep2 = () => {
        if (canProceedStep1) setStep(2);
    };
    const goToStep3 = () => {
        if (canProceedStep2()) setStep(3);
    };

    const getToChips = () => {
        if (sendToAll && selectedRole === 'STUDENT' && selectedSemester) {
            return [{ label: `All Students — Semester ${selectedSemester}`, bulk: true }];
        }
        if (sendToAll && selectedRole !== 'STUDENT') {
            const roleLabel = ROLE_OPTIONS.find(r => r.key === selectedRole)?.label || selectedRole;
            return [{ label: `All ${roleLabel}s`, bulk: true }];
        }
        return selectedRecipients.map(id => {
            const r = recipients.find(rec => rec.id === id);
            return { label: r ? `${r.name}` : id, id, bulk: false };
        });
    };

    const removeChip = (id) => {
        setSelectedRecipients(prev => prev.filter(r => r !== id));
    };

    // Toolbar actions
    const execCmd = (cmd, value) => {
        document.execCommand(cmd, false, value || null);
        editorRef.current?.focus();
    };

    const handleSend = async () => {
        const body = editorRef.current?.innerHTML || '';
        if (!subject.trim()) {
            setError('Subject is required');
            return;
        }
        if (!body.trim() || body.trim() === '<br>') {
            setError('Message body is required');
            return;
        }

        setSending(true);
        setError('');

        try {
            const payload = {
                recipient_role: selectedRole,
                subject: subject.trim(),
                body: body,
            };

            if (selectedRole === 'STUDENT' && selectedSemester) {
                payload.semester = selectedSemester;
            }

            if (!sendToAll && selectedRecipients.length > 0) {
                payload.recipient_ids = selectedRecipients;
            }

            await api.post('/messages/compose', payload);
            onSent && onSent();
            onClose();
        } catch (err) {
            setError(err?.response?.data?.detail || err?.message || 'Failed to send message');
        } finally {
            setSending(false);
        }
    };

    const handleInsertLink = () => {
        const url = prompt('Enter URL:');
        if (url) execCmd('createLink', url);
    };

    if (!isOpen) return null;

    return (
        <div className="compose-overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
            <div className="compose-modal">
                {/* Header */}
                <div className="compose-header">
                    <h3>
                        <FiSend size={18} />
                        New message
                    </h3>
                    <button className="compose-close-btn" onClick={onClose} aria-label="Close">
                        <FiX />
                    </button>
                </div>

                {/* Step Indicator */}
                <div className="compose-steps">
                    <div className={`compose-step ${step === 1 ? 'active' : step > 1 ? 'completed' : ''}`}>
                        <span className="compose-step-num">1</span>
                        Role
                    </div>
                    <div className={`compose-step-divider ${step > 1 ? 'completed' : ''}`} />
                    <div className={`compose-step ${step === 2 ? 'active' : step > 2 ? 'completed' : ''}`}>
                        <span className="compose-step-num">2</span>
                        Recipients
                    </div>
                    <div className={`compose-step-divider ${step > 2 ? 'completed' : ''}`} />
                    <div className={`compose-step ${step === 3 ? 'active' : ''}`}>
                        <span className="compose-step-num">3</span>
                        Compose
                    </div>
                </div>

                {/* Body */}
                <div className="compose-body">
                    {/* ── Step 1: Role Selection ── */}
                    {step === 1 && (
                        <div className="compose-step-content" key="step1">
                            <div className="compose-section-label">Select recipient type</div>
                            <div className="compose-role-grid">
                                {ROLE_OPTIONS.map(opt => (
                                    <div
                                        key={opt.key}
                                        className={`compose-role-card ${selectedRole === opt.key ? 'selected' : ''}`}
                                        onClick={() => setSelectedRole(opt.key)}
                                    >
                                        <div className="compose-role-icon">
                                            <opt.Icon />
                                        </div>
                                        <h4>{opt.label}</h4>
                                        <p>{opt.desc}</p>
                                    </div>
                                ))}
                            </div>
                            <div className="compose-nav-btns">
                                <div />
                                <button
                                    className="compose-next-btn"
                                    disabled={!canProceedStep1}
                                    onClick={goToStep2}
                                >
                                    Next <FiChevronRight />
                                </button>
                            </div>
                        </div>
                    )}

                    {/* ── Step 2: Recipients ── */}
                    {step === 2 && (
                        <div className="compose-step-content" key="step2">
                            {/* Semester selection for students */}
                            {selectedRole === 'STUDENT' && (
                                <>
                                    <div className="compose-section-label">Select semester</div>
                                    <div className="compose-semester-grid">
                                        {SEMESTERS.map(sem => (
                                            <div
                                                key={sem}
                                                className={`compose-sem-chip ${selectedSemester === sem ? 'selected' : ''}`}
                                                onClick={() => { setSelectedSemester(sem); setSelectedRecipients([]); }}
                                            >
                                                Sem {sem}
                                            </div>
                                        ))}
                                    </div>
                                </>
                            )}

                            {/* Send to all toggle */}
                            {((selectedRole === 'STUDENT' && selectedSemester) || selectedRole !== 'STUDENT') && (
                                <>
                                    <div className="compose-send-all-toggle">
                                        <input
                                            type="checkbox"
                                            id="sendToAll"
                                            checked={sendToAll}
                                            onChange={(e) => {
                                                setSendToAll(e.target.checked);
                                                if (e.target.checked) setSelectedRecipients([]);
                                            }}
                                        />
                                        <label htmlFor="sendToAll">
                                            {selectedRole === 'STUDENT'
                                                ? `Send to ALL students in Semester ${selectedSemester}`
                                                : `Send to ALL ${ROLE_OPTIONS.find(r => r.key === selectedRole)?.label || selectedRole}s`
                                            }
                                        </label>
                                    </div>

                                    {/* Individual selection */}
                                    {!sendToAll && (
                                        <>
                                            <div className="compose-recipient-search-wrap">
                                                <input
                                                    className="compose-recipient-search"
                                                    type="text"
                                                    placeholder="Search by name or email..."
                                                    value={searchTerm}
                                                    onChange={(e) => setSearchTerm(e.target.value)}
                                                />
                                            </div>

                                            {selectedRecipients.length > 0 && (
                                                <div className="compose-selected-count">
                                                    {selectedRecipients.length} recipient(s) selected
                                                </div>
                                            )}

                                            <div className="compose-recipient-list">
                                                {loadingRecipients ? (
                                                    <div style={{ padding: 20, textAlign: 'center', color: 'var(--color-text-muted)' }}>
                                                        Loading...
                                                    </div>
                                                ) : recipients.length === 0 ? (
                                                    <div style={{ padding: 20, textAlign: 'center', color: 'var(--color-text-muted)' }}>
                                                        No recipients found
                                                    </div>
                                                ) : (
                                                    recipients.map(r => (
                                                        <div
                                                            key={r.id}
                                                            className={`compose-recipient-item ${selectedRecipients.includes(r.id) ? 'selected' : ''}`}
                                                            onClick={() => toggleRecipient(r.id)}
                                                        >
                                                            <input
                                                                type="checkbox"
                                                                checked={selectedRecipients.includes(r.id)}
                                                                readOnly
                                                            />
                                                            <div>
                                                                <div className="r-name">{r.name}</div>
                                                                <div className="r-email">{r.email}</div>
                                                            </div>
                                                            {r.department && <span className="r-dept">{r.department}</span>}
                                                        </div>
                                                    ))
                                                )}
                                            </div>
                                        </>
                                    )}
                                </>
                            )}

                            <div className="compose-nav-btns">
                                <button className="compose-back-btn" onClick={() => setStep(1)}>
                                    <FiChevronLeft /> Back
                                </button>
                                <button
                                    className="compose-next-btn"
                                    disabled={!canProceedStep2()}
                                    onClick={goToStep3}
                                >
                                    Next <FiChevronRight />
                                </button>
                            </div>
                        </div>
                    )}

                    {/* ── Step 3: Compose ── */}
                    {step === 3 && (
                        <div className="compose-step-content" key="step3" style={{ padding: '0 24px 24px' }}>
                            <div className="compose-form">
                                {/* To Field */}
                                <div className="compose-field-row">
                                    <span className="compose-field-label">To</span>
                                    <div className="compose-chips-area">
                                        {getToChips().map((chip, i) => (
                                            <span
                                                key={i}
                                                className={`compose-chip ${chip.bulk ? 'compose-bulk-chip' : ''}`}
                                            >
                                                {chip.label}
                                                {!chip.bulk && (
                                                    <button
                                                        className="compose-chip-remove"
                                                        onClick={() => removeChip(chip.id)}
                                                    >
                                                        <FiX size={10} />
                                                    </button>
                                                )}
                                            </span>
                                        ))}
                                    </div>
                                </div>

                                {/* Cc Field */}
                                <div className="compose-field-row">
                                    <span className="compose-field-label">Cc</span>
                                    <div className="compose-chips-area" style={{ opacity: 0.5 }}>
                                        <span style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)' }}>
                                            Optional
                                        </span>
                                    </div>
                                </div>

                                {/* Subject */}
                                <input
                                    className="compose-subject-input"
                                    type="text"
                                    placeholder="Subject"
                                    value={subject}
                                    onChange={(e) => setSubject(e.target.value)}
                                />

                                {/* Editor */}
                                <div className="compose-editor-area">
                                    <div
                                        ref={editorRef}
                                        className="compose-editor"
                                        contentEditable
                                        data-placeholder="Write your message here..."
                                        suppressContentEditableWarning
                                    />

                                    {/* Toolbar */}
                                    <div className="compose-toolbar">
                                        <button className="compose-toolbar-btn" onClick={() => execCmd('bold')} title="Bold">
                                            <FiBold />
                                        </button>
                                        <button className="compose-toolbar-btn" onClick={() => execCmd('italic')} title="Italic">
                                            <FiItalic />
                                        </button>
                                        <button className="compose-toolbar-btn" onClick={() => execCmd('underline')} title="Underline">
                                            <FiUnderline />
                                        </button>
                                        <button className="compose-toolbar-btn" onClick={handleInsertLink} title="Insert Link">
                                            <FiLink />
                                        </button>
                                        <button className="compose-toolbar-btn" onClick={() => execCmd('insertUnorderedList')} title="Bullet List">
                                            <FiList />
                                        </button>
                                    </div>
                                </div>
                            </div>

                            {error && (
                                <div style={{
                                    color: 'var(--color-error)',
                                    fontSize: '0.82rem',
                                    marginTop: 8,
                                    fontWeight: 600,
                                }}>
                                    {error}
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Footer (only on step 3) */}
                {step === 3 && (
                    <div className="compose-footer">
                        <div className="compose-footer-left">
                            <button className="compose-discard-btn" onClick={onClose}>
                                Discard
                            </button>
                            <button className="compose-footer-icon-btn" title="Save draft">
                                <FiSave />
                            </button>
                            <button className="compose-footer-icon-btn" title="Attach file">
                                <FiPaperclip />
                            </button>
                            <button className="compose-footer-icon-btn" title="Schedule">
                                <FiClock />
                            </button>
                        </div>
                        <div className="compose-footer-right">
                            <button className="compose-send-later-btn" onClick={() => {}}>
                                <FiClock size={14} />
                                Send later
                            </button>
                            <button
                                className="compose-send-btn"
                                disabled={sending || !subject.trim()}
                                onClick={handleSend}
                            >
                                <FiSend size={14} />
                                {sending ? 'Sending...' : 'Send'}
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
