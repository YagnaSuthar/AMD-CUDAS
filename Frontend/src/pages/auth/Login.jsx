import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import NeoAuthShell from '../../components/NeoAuthShell';
import { FiMail, FiLock, FiEye, FiEyeOff, FiArrowRight, FiInfo } from 'react-icons/fi';
import { toast } from 'react-toastify';

export default function Login() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const { login } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);

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
        <NeoAuthShell
            eyebrow="One login · every stakeholder"
            title="Where academia meets industry."
            subtitle="Students, academicians, institutions and industries all sign in here. CUDAS takes you to the portal built for your role."
            points={[
                'Skill assessment, gap analysis & career mapping',
                'Matched internships, jobs & industry programs',
                'Verified digital portfolio: skills, certificates, projects',
            ]}
        >
            <div className="neo-card-head">
                <h1>Welcome back</h1>
                <p>Sign in to continue to your CUDAS dashboard.</p>
            </div>

            <form onSubmit={handleSubmit} className="neo-form">
                <label className="neo-field">
                    <span className="neo-label">Email address</span>
                    <span className="neo-input-wrap">
                        <FiMail className="neo-input-icon" />
                        <input
                            type="email"
                            className="neo-input"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="name@cudas.edu"
                            autoComplete="email"
                            required
                        />
                    </span>
                </label>

                <div className="neo-field">
                    <div className="neo-label-row">
                        <label className="neo-label" htmlFor="login-password">Password</label>
                        <Link to="/forgot-password" className="neo-link-sm">Forgot password?</Link>
                    </div>
                    <span className="neo-input-wrap">
                        <FiLock className="neo-input-icon" />
                        <input
                            id="login-password"
                            type={showPassword ? 'text' : 'password'}
                            className="neo-input"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="••••••••"
                            autoComplete="current-password"
                            required
                        />
                        <button
                            type="button"
                            onClick={() => setShowPassword(!showPassword)}
                            className="neo-eye"
                            aria-label={showPassword ? 'Hide password' : 'Show password'}
                        >
                            {showPassword ? <FiEyeOff /> : <FiEye />}
                        </button>
                    </span>
                </div>

                <button type="submit" className="neo-btn neo-btn-primary neo-btn-block" disabled={isLoading}>
                    {isLoading ? <span className="neo-spinner" /> : <>Sign in <FiArrowRight /></>}
                </button>
            </form>

            <div className="neo-divider"><span>new to CUDAS?</span></div>

            <Link to="/register" className="neo-btn neo-btn-ghost neo-btn-block">
                Register your institution or company
            </Link>

            <p className="neo-note">
                <FiInfo />
                Students, Faculty and HODs receive their credentials by email from their institution admin.
            </p>
        </NeoAuthShell>
    );
}
