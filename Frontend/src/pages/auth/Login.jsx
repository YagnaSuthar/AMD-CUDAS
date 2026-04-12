import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import AnimatedBackground from '../../components/AnimatedBackground';
import AuthNavbar from '../../components/AuthNavbar';
import { FaEye, FaEyeSlash } from 'react-icons/fa';
import { toast } from 'react-toastify';

export default function Login() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const { login } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        setError('');

        try {
            await login(email, password);
            toast.success('Login successful!');
            navigate('/dashboard');
        } catch (err) {
            if (err.response?.data?.unverified) {
                toast.info('Please verify your email to continue.');
                navigate(`/verify-email?email=${encodeURIComponent(email)}`);
            } else if (err.response?.data?.reset_required) {
                toast.info('Password reset required before login.');
                navigate(`/forgot-password?email=${encodeURIComponent(email)}`);
            } else {
                toast.error(err.response?.data?.detail || 'Login failed. Please check your credentials.');
            }
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
                    <h1 className="gradient-text">Welcome Back</h1>
                    <p>Log in to access your CUDAS dashboard.</p>
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
                        />
                    </div>

                    <div className="form-group">
                        <div className="form-label-row">
                            <label className="form-label">Password</label>
                            <Link to="/forgot-password" className="form-helper-link">Forgot password?</Link>
                        </div>
                        <div className="input-with-icon">
                            <input
                                type={showPassword ? "text" : "password"}
                                className="form-input form-input-with-icon"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="••••••••"
                                required
                            />
                            <button
                                type="button"
                                onClick={() => setShowPassword(!showPassword)}
                                className="input-icon-btn"
                                aria-label={showPassword ? 'Hide password' : 'Show password'}
                            >
                                {showPassword ? <FaEyeSlash /> : <FaEye />}
                            </button>
                        </div>
                    </div>

                    <button type="submit" className="auth-submit-btn" disabled={isLoading}>
                        {isLoading ? 'Authenticating...' : 'Sign In'}
                    </button>
                </form>

                <div className="auth-divider">or</div>

                <div className="auth-footer">
                    Don't have an account? <Link to="/register">Register your college</Link> <br /><br />
                    (Students, Faculty, and HODs will receive credentials via email from their admins)
                </div>
            </div>
        </div>
    );
}
