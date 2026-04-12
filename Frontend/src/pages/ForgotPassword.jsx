import { useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../utils/api';
import AnimatedBackground from '../components/AnimatedBackground';
import AuthNavbar from '../components/AuthNavbar';
import { toast } from 'react-toastify';

export default function ForgotPassword() {
    const [email, setEmail] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);

        try {
            const res = await api.post('/auth/forgot-password', { email });
            toast.success(res.data.message);
            setEmail('');
        } catch (err) {
            toast.error('Something went wrong. Please try again later.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="auth-page">
            <AuthNavbar />
            <AnimatedBackground />

            <div className="auth-container fade-in-up">
                <div className="auth-header">
                    <h1 className="gradient-text">Forgot Password</h1>
                    <p>Enter your email to receive a reset link.</p>
                </div>

                <form onSubmit={handleSubmit} className="auth-form">
                    <div className="form-group">
                        <label className="form-label">Email Address</label>
                        <input
                            type="email"
                            className="form-input"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="name@college.edu"
                            required
                        />
                    </div>

                    <button type="submit" className="auth-submit-btn" disabled={isLoading}>
                        {isLoading ? 'Sending...' : 'Send Reset Link'}
                    </button>
                </form>

                <div className="auth-footer">
                    Remember your password? <Link to="/login">Sign In</Link>
                </div>
            </div>
        </div>
    );
}
