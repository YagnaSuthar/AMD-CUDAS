import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../../utils/api';
import AnimatedBackground from '../../components/AnimatedBackground';
import AuthNavbar from '../../components/AuthNavbar';
import { FaEye, FaEyeSlash } from 'react-icons/fa';
import { toast } from 'react-toastify';

export default function Register() {
    const [role, setRole] = useState('COLLEGE_PRINCIPAL'); // 'COLLEGE_PRINCIPAL' or 'COMPANY_ADMIN'
    const [formData, setFormData] = useState({
        name: '',
        email: '',
        password: '',
        confirmPassword: '',
        college_name: '',
        phone_number: '',
        company_name: ''
    });
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [status, setStatus] = useState({ type: '', msg: '' });
    const [isLoading, setIsLoading] = useState(false);
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        setStatus({ type: '', msg: '' });

        if (formData.password !== formData.confirmPassword) {
            toast.error('Passwords do not match.');
            setIsLoading(false);
            return;
        }

        try {
            let endpoint = '/auth/register-principal';
            let payload = { ...formData };

            if (role === 'COMPANY_ADMIN') {
                endpoint = '/company/register';
                // Only send relevant fields for company
                payload = {
                    name: formData.name,
                    email: formData.email,
                    password: formData.password,
                    company_name: formData.company_name,
                    phone_number: formData.phone_number
                };
            }

            const res = await api.post(endpoint, payload);
            toast.success(res.data.message);
            setFormData({
                name: '', email: '', password: '', confirmPassword: '',
                college_name: '', phone_number: '', company_name: ''
            });

            // Redirect after success
            setTimeout(() => {
                navigate('/login');
            }, 3000);

        } catch (err) {
            const errorMsg = err.response?.data?.detail || 'Registration failed.';
            toast.error(errorMsg);
        } finally {
            setIsLoading(false);
        }
    };

    const handleChange = (e) => setFormData({ ...formData, [e.target.name]: e.target.value });

    return (
        <div className="auth-page">
            <AuthNavbar />
            <AnimatedBackground />

            <div className="auth-container fade-in-up">
                <div className="auth-header">
                    <h1 className="gradient-text-secondary">Create Account</h1>
                    <p>Register your account and join the CUDAS platform.</p>
                </div>

                {status.msg && (
                    <div className={`alert alert-${status.type}`} style={{ marginBottom: '16px' }}>
                        {status.msg}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="auth-form">
                    <div className="form-group">
                        <label className="form-label">I am registering as a:</label>
                        <select
                            className="form-input"
                            value={role}
                            onChange={(e) => setRole(e.target.value)}
                            style={{ cursor: 'pointer' }}
                        >
                            <option value="COLLEGE_PRINCIPAL">College Principal</option>
                            <option value="COMPANY_ADMIN">Company / Recruiter</option>
                        </select>
                    </div>

                    <div className="form-group">
                        <label className="form-label">
                            {role === 'COLLEGE_PRINCIPAL' ? 'College Name' : 'Company Name'}
                        </label>
                        <input
                            type="text"
                            name={role === 'COLLEGE_PRINCIPAL' ? 'college_name' : 'company_name'}
                            className="form-input"
                            value={role === 'COLLEGE_PRINCIPAL' ? formData.college_name : formData.company_name}
                            onChange={handleChange}
                            placeholder={role === 'COLLEGE_PRINCIPAL' ? "e.g. Modern Institute of Technology" : "e.g. Acme Corp"}
                            required
                        />
                    </div>

                    {role === 'COLLEGE_PRINCIPAL' && (
                        <div className="form-group">
                            <label className="form-label">Affiliated Company (Optional)</label>
                            <input
                                type="text"
                                name="company_name"
                                className="form-input"
                                value={formData.company_name}
                                onChange={handleChange}
                                placeholder="e.g. Acme Corp"
                            />
                        </div>
                    )}

                    <div className="form-group">
                        <label className="form-label">Full Name</label>
                        <input
                            type="text"
                            name="name"
                            className="form-input"
                            value={formData.name}
                            onChange={handleChange}
                            placeholder="John Doe"
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">Work Email</label>
                        <input
                            type="email"
                            name="email"
                            className="form-input"
                            value={formData.email}
                            onChange={handleChange}
                            placeholder="name@organization.com"
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">Phone Number</label>
                        <input
                            type="tel"
                            name="phone_number"
                            className="form-input"
                            value={formData.phone_number}
                            onChange={handleChange}
                            placeholder="+1 234 567 890"
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">Password</label>
                        <div style={{ position: 'relative' }}>
                            <input
                                type={showPassword ? "text" : "password"}
                                name="password"
                                className="form-input"
                                value={formData.password}
                                onChange={handleChange}
                                placeholder="â€¢â€¢â€¢â€¢â€¢â€¢â€¢â€¢"
                                required
                                minLength={6}
                                style={{ paddingRight: '40px' }}
                            />
                            <button
                                type="button"
                                onClick={() => setShowPassword(!showPassword)}
                                style={{
                                    position: 'absolute',
                                    right: '10px',
                                    top: '50%',
                                    transform: 'translateY(-50%)',
                                    background: 'none',
                                    border: 'none',
                                    color: 'var(--color-text-muted)',
                                    cursor: 'pointer'
                                }}
                            >
                                {showPassword ? <FaEyeSlash /> : <FaEye />}
                            </button>
                        </div>
                    </div>

                    <div className="form-group">
                        <label className="form-label">Confirm Password</label>
                        <div style={{ position: 'relative' }}>
                            <input
                                type={showConfirmPassword ? "text" : "password"}
                                name="confirmPassword"
                                className="form-input"
                                value={formData.confirmPassword}
                                onChange={handleChange}
                                placeholder="â€¢â€¢â€¢â€¢â€¢â€¢â€¢â€¢"
                                required
                                minLength={6}
                                style={{ paddingRight: '40px' }}
                            />
                            <button
                                type="button"
                                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                style={{
                                    position: 'absolute',
                                    right: '10px',
                                    top: '50%',
                                    transform: 'translateY(-50%)',
                                    background: 'none',
                                    border: 'none',
                                    color: 'var(--color-text-muted)',
                                    cursor: 'pointer'
                                }}
                            >
                                {showConfirmPassword ? <FaEyeSlash /> : <FaEye />}
                            </button>
                        </div>
                    </div>

                    <button type="submit" className="auth-submit-btn" disabled={isLoading}>
                        {isLoading ? 'Registering...' : 'Complete Registration'}
                    </button>
                </form>

                <div className="auth-footer">
                    Already registered? <Link to="/login">Sign in here</Link>
                </div>
            </div>
        </div>
    );
}
