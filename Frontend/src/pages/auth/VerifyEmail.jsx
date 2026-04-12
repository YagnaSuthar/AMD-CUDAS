import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import api from '../../utils/api';
import AnimatedBackground from '../../components/AnimatedBackground';
import AuthNavbar from '../../components/AuthNavbar';
import { toast } from 'react-toastify';

export default function VerifyEmail() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();

    // Attempt to get email from URL parameters
    const [email, setEmail] = useState('');
    const [otp, setOtp] = useState('');

    // UI states
    const [isVerifying, setIsVerifying] = useState(false);
    const [isResending, setIsResending] = useState(false);

    useEffect(() => {
        const emailParam = searchParams.get('email');
        if (emailParam) {
            setEmail(emailParam);
        }
    }, [searchParams]);

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!email) {
            toast.error('Email is required to verify OTP.');
            return;
        }

        if (otp.length !== 6) {
            toast.error('OTP must be exactly 6 digits.');
            return;
        }

        setIsVerifying(true);
        try {
            const res = await api.post('/auth/verify-email', { email, otp });
            toast.success(res.data.message || 'Email verified successfully!');
            // clear form
            setOtp('');

            // Redirect to login after 2 seconds
            setTimeout(() => {
                navigate('/login');
            }, 2000);
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Verification failed. Invalid or expired OTP.');
        } finally {
            setIsVerifying(false);
        }
    };

    const handleResend = async () => {
        if (!email) {
            toast.error('Please enter your email to request a new OTP.');
            return;
        }

        setIsResending(true);

        try {
            const res = await api.post('/auth/resend-verification', { email });
            toast.success(res.data.message || 'A new OTP has been sent to your email.');
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to resend OTP. Please try again later.');
        } finally {
            setIsResending(false);
        }
    };

    return (
        <div className="auth-page">
            <AuthNavbar />
            <AnimatedBackground />

            <div className="auth-container fade-in-up">
                <div className="auth-header">
                    <h1 className="gradient-text">Verify Email</h1>
                    <p>Enter the 6-digit code sent to your email.</p>
                </div>

                <form onSubmit={handleSubmit} className="auth-form">
                    <div className="form-group">
                        <label className="form-label">Email Address</label>
                        <input
                            type="email"
                            className="form-input"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="name@cudas.edu"
                            required
                            readOnly
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">6-Digit OTP</label>
                        <input
                            type="text"
                            className="form-input"
                            style={{ letterSpacing: '8px', fontSize: '1.2rem', textAlign: 'center', fontWeight: 'bold' }}
                            value={otp}
                            onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                            placeholder="000000"
                            maxLength={6}
                            required
                        />
                    </div>

                    <button type="submit" className="auth-submit-btn" disabled={isVerifying}>
                        {isVerifying ? 'Verifying...' : 'Verify Email'}
                    </button>
                </form>

                <div className="auth-footer" style={{ marginTop: '20px' }}>
                    <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={handleResend}
                        disabled={isResending || isVerifying}
                        style={{ width: '100%', padding: '10px' }}
                    >
                        {isResending ? 'Sending...' : 'Resend OTP Code'}
                    </button>
                    <div style={{ marginTop: '16px' }}>
                        <Link to="/login">Back to Login</Link>
                    </div>
                </div>
            </div>
        </div>
    );
}
