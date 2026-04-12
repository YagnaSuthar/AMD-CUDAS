import { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { FiVideo, FiMic, FiMicOff, FiVideoOff, FiArrowLeft, FiClock } from 'react-icons/fi';
import api from '../../../../utils/api';

export default function Round2Meeting() {
    const { pipelineId } = useParams();
    const navigate = useNavigate();

    const videoRef = useRef(null);
    const selfVideoRef = useRef(null);
    const streamRef = useRef(null);

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [meta, setMeta] = useState(null);

    const [camOn, setCamOn] = useState(true);
    const [micOn, setMicOn] = useState(true);
    const [joined, setJoined] = useState(false);

    useEffect(() => {
        const load = async () => {
            try {
                setLoading(true);
                setError('');

                const notesRes = await api.get('/messages/notifications');
                const list = notesRes.data?.notifications || [];
                const match = list.find((n) => (n.meta_json?.pipeline_id || n.meta_json?.pipelineId) === pipelineId);
                setMeta(match?.meta_json || null);
            } catch (e) {
                // Non-blocking: meeting UI can still show.
            } finally {
                setLoading(false);
            }
        };
        load();
    }, [pipelineId]);

    useEffect(() => {
        const startMedia = async () => {
            try {
                setError('');
                const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
                streamRef.current = stream;
                if (videoRef.current) {
                    videoRef.current.srcObject = stream;
                }
                if (selfVideoRef.current) {
                    selfVideoRef.current.srcObject = stream;
                }
            } catch (e) {
                setError('Camera/Microphone permission denied or not available. You can still view the invite details.');
            }
        };

        startMedia();

        return () => {
            if (streamRef.current) {
                streamRef.current.getTracks().forEach((t) => t.stop());
                streamRef.current = null;
            }
        };
    }, []);

    const toggleMic = () => {
        const stream = streamRef.current;
        if (!stream) {
            setMicOn((v) => !v);
            return;
        }
        stream.getAudioTracks().forEach((t) => { t.enabled = !micOn; });
        setMicOn((v) => !v);
    };

    const toggleCam = () => {
        const stream = streamRef.current;
        if (!stream) {
            setCamOn((v) => !v);
            return;
        }
        stream.getVideoTracks().forEach((t) => { t.enabled = !camOn; });
        setCamOn((v) => !v);
    };

    const scheduledAt = meta?.round2_scheduled_at ? new Date(meta.round2_scheduled_at) : null;

    const handleJoin = () => setJoined(true);

    const handleLeave = () => {
        setJoined(false);
        navigate('/dashboard/notifications');
    };

    return (
        <div className="dashboard-content" style={{ 
            background: 'linear-gradient(135deg, #0f0f0f 0%, #1a1a1a 100%)', 
            color: '#fff', 
            minHeight: '100vh',
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
            padding: '24px',
            boxSizing: 'border-box',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            position: 'relative',
            zIndex: 1
        }}>
            {/* Back button */}
            <button 
                onClick={() => navigate('/dashboard/notifications')} 
                style={{
                    position: 'absolute',
                    top: '24px',
                    left: '24px',
                    background: 'rgba(255,255,255,0.08)',
                    border: '1px solid rgba(255,255,255,0.15)',
                    color: '#fff',
                    borderRadius: '12px',
                    padding: '10px 16px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    fontSize: '14px',
                    fontWeight: 500,
                    transition: 'all 0.2s ease',
                    zIndex: 10
                }}
                onMouseEnter={(e) => {
                    e.target.style.background = 'rgba(255,255,255,0.12)';
                    e.target.style.borderColor = 'rgba(255,255,255,0.25)';
                }}
                onMouseLeave={(e) => {
                    e.target.style.background = 'rgba(255,255,255,0.08)';
                    e.target.style.borderColor = 'rgba(255,255,255,0.15)';
                }}
            >
                <FiArrowLeft size={16} />
                Back to Notifications
            </button>

            {/* Meeting Info Card */}
            <div style={{
                position: 'absolute',
                top: '24px',
                right: '24px',
                background: 'rgba(0,0,0,0.8)',
                backdropFilter: 'blur(20px)',
                padding: '16px',
                borderRadius: '16px',
                border: '1px solid rgba(255,255,255,0.15)',
                minWidth: '200px',
                zIndex: 10
            }}>
                <div style={{ fontSize: '0.85rem', opacity: 0.7, marginBottom: '4px' }}>Meeting ID</div>
                <div style={{ fontSize: '1rem', fontWeight: 600, fontFamily: 'monospace' }}>
                    {pipelineId?.slice(0, 8).toUpperCase()}
                </div>
                {scheduledAt && (
                    <div style={{ marginTop: '12px', fontSize: '0.85rem', opacity: 0.8 }}>
                        <FiClock size={14} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
                        {scheduledAt.toLocaleDateString()} â€¢ {scheduledAt.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                    </div>
                )}
            </div>

            {/* Main Meeting Card */}
            <div style={{
                width: 'min(1360px, calc(100% - 32px))',
                height: 'min(740px, calc(100vh - 220px))',
                borderRadius: '20px',
                background: 'linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02))',
                border: '1px solid rgba(255,255,255,0.12)',
                boxShadow: '0 30px 80px rgba(0,0,0,0.55)',
                position: 'relative',
                overflow: 'hidden'
            }}>
                    {/* Stage (remote placeholder) */}
                    <div style={{
                        position: 'absolute',
                        inset: 0,
                        background: joined ? '#000' : 'radial-gradient(circle at 30% 20%, rgba(99,102,241,0.20), transparent 60%), radial-gradient(circle at 80% 90%, rgba(16,185,129,0.18), transparent 55%), #0b0b0f',
                        display: 'grid',
                        placeItems: 'center'
                    }}> 
                        {joined ? (
                            <div style={{ textAlign: 'center', padding: '0 18px' }}>
                                <div style={{
                                    width: '76px',
                                    height: '76px',
                                    borderRadius: '50%',
                                    margin: '0 auto 14px',
                                    border: '3px solid rgba(255,255,255,0.18)',
                                    borderTopColor: 'rgba(255,255,255,0.85)',
                                    boxSizing: 'border-box',
                                    animation: 'spin 0.9s linear infinite'
                                }} />
                                <div style={{ fontSize: '1.35rem', fontWeight: 800, letterSpacing: '-0.01em' }}>
                                    Interviewer not joined yet
                                </div>
                                <div style={{ marginTop: '8px', opacity: 0.78, fontSize: '1rem', lineHeight: 1.5 }}>
                                    Please wait â€” the interviewer will join soon.
                                </div>
                            </div>
                        ) : (
                            <div style={{ textAlign: 'center' }}>
                                <div style={{
                                    width: '88px',
                                    height: '88px',
                                    borderRadius: '50%',
                                    margin: '0 auto 14px',
                                    background: 'rgba(255,255,255,0.08)',
                                    border: '1px solid rgba(255,255,255,0.14)',
                                    display: 'grid',
                                    placeItems: 'center',
                                    fontWeight: 700,
                                    fontSize: '22px'
                                }}>
                                    HR
                                </div>
                                <div style={{ fontSize: '1.25rem', fontWeight: 600 }}>Interviewer</div>
                                <div style={{ marginTop: '6px', opacity: 0.75, fontSize: '0.95rem' }}>
                                    Ready to join
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Self view tile */}
                    <div style={{
                        position: 'absolute',
                        right: '16px',
                        bottom: '16px',
                        width: '320px',
                        height: '200px',
                        borderRadius: '16px',
                        overflow: 'hidden',
                        border: '1px solid rgba(255,255,255,0.18)',
                        background: '#000',
                        boxShadow: '0 14px 40px rgba(0,0,0,0.55)'
                    }}>
                        <video
                            ref={selfVideoRef}
                            autoPlay
                            playsInline
                            muted
                            style={{
                                width: '100%',
                                height: '100%',
                                objectFit: 'cover',
                                transform: 'scaleX(-1)',
                                display: camOn ? 'block' : 'none'
                            }}
                        />
                        {!camOn && (
                            <div style={{
                                position: 'absolute',
                                inset: 0,
                                display: 'grid',
                                placeItems: 'center',
                                background: 'rgba(0,0,0,0.65)',
                                color: 'rgba(255,255,255,0.82)'
                            }}>
                                <div style={{ textAlign: 'center' }}>
                                    <FiVideoOff size={28} style={{ marginBottom: '8px', opacity: 0.9 }} />
                                    <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>Camera off</div>
                                </div>
                            </div>
                        )}

                        <div style={{
                            position: 'absolute',
                            left: '10px',
                            top: '10px',
                            background: 'rgba(0,0,0,0.55)',
                            border: '1px solid rgba(255,255,255,0.12)',
                            padding: '6px 10px',
                            borderRadius: '999px',
                            fontSize: '0.82rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px'
                        }}>
                            <span style={{ opacity: 0.9 }}>You</span>
                            <span style={{ opacity: 0.6 }}>â€¢</span>
                            <span style={{ opacity: 0.85 }}>{micOn ? 'Mic on' : 'Mic off'}</span>
                        </div>
                    </div>

                    {/* Lobby overlay */}
                    {!joined && (
                        <div style={{
                            position: 'absolute',
                            inset: 0,
                            display: 'grid',
                            placeItems: 'center',
                            padding: '24px',
                            background: 'linear-gradient(180deg, rgba(0,0,0,0.10), rgba(0,0,0,0.55))'
                        }}>
                            <div style={{
                                width: 'min(520px, 100%)',
                                borderRadius: '18px',
                                background: 'rgba(0,0,0,0.45)',
                                border: '1px solid rgba(255,255,255,0.14)',
                                backdropFilter: 'blur(18px)',
                                padding: '18px 18px 16px'
                            }}>
                                <div style={{ fontSize: '1.2rem', fontWeight: 700, letterSpacing: '-0.01em' }}>Ready to join?</div>
                                <div style={{ marginTop: '6px', opacity: 0.78, fontSize: '0.95rem' }}>
                                    Check your camera and microphone before joining.
                                </div>

                                <div style={{ marginTop: '14px', display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                                    <button
                                        onClick={toggleMic}
                                        style={{
                                            padding: '10px 14px',
                                            borderRadius: '12px',
                                            border: '1px solid rgba(255,255,255,0.16)',
                                            background: 'rgba(255,255,255,0.10)',
                                            color: '#fff',
                                            cursor: 'pointer',
                                            display: 'inline-flex',
                                            alignItems: 'center',
                                            gap: '10px',
                                            fontWeight: 600
                                        }}
                                    >
                                        {micOn ? <FiMic /> : <FiMicOff />}
                                        {micOn ? 'Microphone on' : 'Microphone off'}
                                    </button>
                                    <button
                                        onClick={toggleCam}
                                        style={{
                                            padding: '10px 14px',
                                            borderRadius: '12px',
                                            border: '1px solid rgba(255,255,255,0.16)',
                                            background: 'rgba(255,255,255,0.10)',
                                            color: '#fff',
                                            cursor: 'pointer',
                                            display: 'inline-flex',
                                            alignItems: 'center',
                                            gap: '10px',
                                            fontWeight: 600
                                        }}
                                    >
                                        {camOn ? <FiVideo /> : <FiVideoOff />}
                                        {camOn ? 'Camera on' : 'Camera off'}
                                    </button>
                                </div>

                                <div style={{ marginTop: '14px', display: 'flex', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
                                    <div style={{ opacity: 0.8, fontSize: '0.92rem' }}>
                                        Meeting ID: <span style={{ fontFamily: 'monospace', fontWeight: 700 }}>{pipelineId?.slice(0, 8).toUpperCase()}</span>
                                    </div>
                                    <button
                                        onClick={handleJoin}
                                        style={{
                                            padding: '11px 18px',
                                            borderRadius: '12px',
                                            border: '1px solid rgba(99,102,241,0.45)',
                                            background: 'linear-gradient(145deg, rgba(99,102,241,0.95), rgba(79,70,229,0.95))',
                                            color: '#fff',
                                            cursor: 'pointer',
                                            fontWeight: 800,
                                            letterSpacing: '0.01em'
                                        }}
                                    >
                                        Join now
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Status Badge */}
                <div style={{
                    position: 'absolute',
                    left: '24px',
                    bottom: '132px',
                    background: 'rgba(0,0,0,0.72)',
                    backdropFilter: 'blur(18px)',
                    padding: '10px 14px',
                    borderRadius: '999px',
                    fontSize: '0.95rem',
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    border: '1px solid rgba(255,255,255,0.14)',
                    zIndex: 5
                }}>
                    <div style={{
                        width: '10px',
                        height: '10px',
                        borderRadius: '50%',
                        background: joined ? '#10b981' : '#f59e0b',
                        boxShadow: joined ? '0 0 10px rgba(16, 185, 129, 0.5)' : '0 0 10px rgba(245, 158, 11, 0.5)',
                        animation: joined ? 'none' : 'pulse 2s infinite'
                    }} />
                    {joined ? 'In call' : 'Lobby'}
                </div>

                {/* Bottom Control Bar */}
                <div style={{
                    position: 'absolute',
                    bottom: 0,
                    left: 0,
                    right: 0,
                    background: 'linear-gradient(180deg, rgba(0,0,0,0) 0%, rgba(0,0,0,0.86) 30%, rgba(0,0,0,0.98) 100%)',
                    backdropFilter: 'blur(18px)',
                    padding: '16px 18px',
                    display: 'flex',
                    justifyContent: 'center',
                    zIndex: 5
                }}>
                    <div style={{
                        display: 'flex',
                        gap: '14px',
                        alignItems: 'center',
                        background: 'rgba(255,255,255,0.06)',
                        border: '1px solid rgba(255,255,255,0.10)',
                        padding: '10px 12px',
                        borderRadius: '18px'
                    }}>
                        <button
                            onClick={toggleMic}
                            style={{
                                width: '52px',
                                height: '52px',
                                borderRadius: '999px',
                                display: 'grid',
                                placeItems: 'center',
                                background: micOn ? 'rgba(255,255,255,0.10)' : 'rgba(239,68,68,0.95)',
                                border: '1px solid rgba(255,255,255,0.14)',
                                color: '#fff',
                                cursor: 'pointer'
                            }}
                            title={micOn ? 'Mute microphone' : 'Unmute microphone'}
                        >
                            {micOn ? <FiMic size={22} /> : <FiMicOff size={22} />}
                        </button>

                        <button
                            onClick={toggleCam}
                            style={{
                                width: '52px',
                                height: '52px',
                                borderRadius: '999px',
                                display: 'grid',
                                placeItems: 'center',
                                background: camOn ? 'rgba(255,255,255,0.10)' : 'rgba(239,68,68,0.95)',
                                border: '1px solid rgba(255,255,255,0.14)',
                                color: '#fff',
                                cursor: 'pointer'
                            }}
                            title={camOn ? 'Turn off camera' : 'Turn on camera'}
                        >
                            {camOn ? <FiVideo size={22} /> : <FiVideoOff size={22} />}
                        </button>

                        <button
                            onClick={joined ? handleLeave : () => navigate('/dashboard/notifications')}
                            style={{
                                height: '52px',
                                padding: '0 16px',
                                borderRadius: '999px',
                                display: 'inline-flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '10px',
                                background: 'rgba(239,68,68,0.95)',
                                border: '1px solid rgba(239,68,68,0.55)',
                                color: '#fff',
                                cursor: 'pointer',
                                fontWeight: 800
                            }}
                            title="Leave meeting"
                        >
                            <FiArrowLeft size={18} style={{ transform: 'rotate(180deg)' }} />
                            Leave
                        </button>
                    </div>
                </div>

                {/* Error Toast */}
                {error && (
                    <div style={{
                        position: 'fixed',
                        top: '100px',
                        right: '24px',
                        background: 'linear-gradient(145deg, rgba(239, 68, 68, 0.95), rgba(220, 38, 38, 0.95))',
                        backdropFilter: 'blur(20px)',
                        padding: '16px 20px',
                        borderRadius: '12px',
                        maxWidth: '320px',
                        fontSize: '0.95rem',
                        fontWeight: 500,
                        border: '1px solid rgba(239, 68, 68, 0.5)',
                        boxShadow: '0 10px 40px rgba(239, 68, 68, 0.3)',
                        zIndex: 1000
                    }}>
                        {error}
                    </div>
                )}

                <style jsx>{`
                    @keyframes pulse {
                        0%, 100% { 
                            opacity: 1; 
                            transform: scale(1);
                        }
                        50% { 
                            opacity: 0.6; 
                            transform: scale(1.1);
                        }
                    }

                    @keyframes spin {
                        0% { transform: rotate(0deg); }
                        100% { transform: rotate(360deg); }
                    }
                `}</style>
        </div>
    );
}
