import { useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../utils/api';
import AnimatedBackground from '../components/AnimatedBackground';
import AuthNavbar from '../components/AuthNavbar';

export default function RegisterPrincipal() {
    const [formData, setFormData] = useState({
        name: '',
        email: '',
        password: '',
        college_name: ''
    });
    const [status, setStatus] = useState({ type: '', msg: '' });
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        setStatus({ type: '', msg: '' });

        try {
            const res = await api.post('/auth/register-principal', formData);
            setStatus({ type: 'success', msg: res.data.message });
            setFormData({ name: '', email: '', password: '', college_name: '' });
        } catch (err) {
            setStatus({
                type: 'error',
                msg: err.response?.data?.detail || 'Registration failed.'
            });
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
                    <h1 className="gradient-text-secondary">College Register</h1>
                    <p>Register your institution and set up the Principal account.</p>
                </div>

                {status.msg && (
                    <div className={`alert alert-${status.type}`} style={{ marginBottom: '16px' }}>
                        {status.msg}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="auth-form">
                    <div className="form-group">
                        <label className="form-label">College Name</label>
                        <input
                            type="text"
                            name="college_name"
                            className="form-input"
                            value={formData.college_name}
                            onChange={handleChange}
                            placeholder="e.g. Modern Institute of Technology"
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">Principal Name</label>
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
                        <label className="form-label">Work Email / Principal Email</label>
                        <input
                            type="email"
                            name="email"
                            className="form-input"
                            value={formData.email}
                            onChange={handleChange}
                            placeholder="principal@college.edu"
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">Password</label>
                        <input
                            type="password"
                            name="password"
                            className="form-input"
                            value={formData.password}
                            onChange={handleChange}
                            placeholder="••••••••"
                            required
                            minLength={6}
                        />
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
