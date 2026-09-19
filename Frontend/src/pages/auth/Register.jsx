import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../../utils/api';
import NeoAuthShell from '../../components/NeoAuthShell';
import {
    FiEye, FiEyeOff, FiUser, FiMail, FiPhone, FiLock, FiBookOpen, FiBriefcase, FiArrowRight,
} from 'react-icons/fi';
import { toast } from 'react-toastify';

const ROLES = [
    { id: 'COLLEGE_PRINCIPAL', label: 'Institution', sub: 'Principal', icon: FiBookOpen },
    { id: 'COMPANY_ADMIN', label: 'Industry', sub: 'Recruiter', icon: FiBriefcase },
];

function Field({ label, icon: Icon, children }) {
    return (
        <label className="neo-field">
            <span className="neo-label">{label}</span>
            <span className="neo-input-wrap">
                <Icon className="neo-input-icon" />
                {children}
            </span>
        </label>
    );
}

export default function Register() {
    const [role, setRole] = useState('COLLEGE_PRINCIPAL');
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
    const [isLoading, setIsLoading] = useState(false);
    const navigate = useNavigate();
    const isCollege = role === 'COLLEGE_PRINCIPAL';

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);

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
        <NeoAuthShell
            wide
            eyebrow={isCollege ? 'For institutions' : 'For recruiters'}
            title={isCollege ? 'Make every student industry-ready.' : 'Hire skill-verified talent, faster.'}
            subtitle={isCollege
                ? 'Register as Principal, then onboard HODs, faculty and students in bulk via CSV. Track skill development, internships and placements from one dashboard.'
                : 'Post internships, jobs and learning programs, share skill questionnaires and shortlist by skill compatibility.'}
            points={isCollege
                ? ['Skill-gap & placement-readiness analytics', 'FDPs, faculty internships & industry collaboration', 'Secure student records & digital portfolios']
                : ['Post internships, projects, apprenticeships & jobs', 'Publish trainings, certifications & mentorships', 'Skill-based shortlisting with AI interviews']}
        >
            <div className="neo-card-head">
                <h1>Create account</h1>
                <p>Choose how you're joining the CUDAS platform.</p>
            </div>

            <div className="neo-segment" role="radiogroup" aria-label="Register as">
                <span className={`neo-segment-thumb ${isCollege ? '' : 'is-right'}`} />
                {ROLES.map(({ id, label, sub, icon: Icon }) => (
                    <button
                        key={id}
                        type="button"
                        role="radio"
                        aria-checked={role === id}
                        className={`neo-segment-opt ${role === id ? 'is-active' : ''}`}
                        onClick={() => setRole(id)}
                    >
                        <Icon />
                        <span><strong>{label}</strong><small>{sub}</small></span>
                    </button>
                ))}
            </div>

            <form onSubmit={handleSubmit} className="neo-form neo-form-grid">
                <Field label={isCollege ? 'College name' : 'Company name'} icon={isCollege ? FiBookOpen : FiBriefcase}>
                    <input
                        type="text"
                        name={isCollege ? 'college_name' : 'company_name'}
                        className="neo-input"
                        value={isCollege ? formData.college_name : formData.company_name}
                        onChange={handleChange}
                        placeholder={isCollege ? 'e.g. Modern Institute of Technology' : 'e.g. Acme Corp'}
                        required
                    />
                </Field>

                {isCollege && (
                    <Field label="Affiliated company (optional)" icon={FiBriefcase}>
                        <input
                            type="text"
                            name="company_name"
                            className="neo-input"
                            value={formData.company_name}
                            onChange={handleChange}
                            placeholder="e.g. Acme Corp"
                        />
                    </Field>
                )}

                <Field label="Full name" icon={FiUser}>
                    <input
                        type="text"
                        name="name"
                        className="neo-input"
                        value={formData.name}
                        onChange={handleChange}
                        placeholder="John Doe"
                        autoComplete="name"
                        required
                    />
                </Field>

                <Field label="Work email" icon={FiMail}>
                    <input
                        type="email"
                        name="email"
                        className="neo-input"
                        value={formData.email}
                        onChange={handleChange}
                        placeholder="name@organization.com"
                        autoComplete="email"
                        required
                    />
                </Field>

                <Field label="Phone number" icon={FiPhone}>
                    <input
                        type="tel"
                        name="phone_number"
                        className="neo-input"
                        value={formData.phone_number}
                        onChange={handleChange}
                        placeholder="+91 98765 43210"
                        autoComplete="tel"
                        required
                    />
                </Field>

                <Field label="Password" icon={FiLock}>
                    <input
                        type={showPassword ? 'text' : 'password'}
                        name="password"
                        className="neo-input"
                        value={formData.password}
                        onChange={handleChange}
                        placeholder="Min. 6 characters"
                        autoComplete="new-password"
                        required
                        minLength={6}
                    />
                    <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="neo-eye"
                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                        {showPassword ? <FiEyeOff /> : <FiEye />}
                    </button>
                </Field>

                <Field label="Confirm password" icon={FiLock}>
                    <input
                        type={showConfirmPassword ? 'text' : 'password'}
                        name="confirmPassword"
                        className="neo-input"
                        value={formData.confirmPassword}
                        onChange={handleChange}
                        placeholder="Re-enter password"
                        autoComplete="new-password"
                        required
                        minLength={6}
                    />
                    <button
                        type="button"
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        className="neo-eye"
                        aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                    >
                        {showConfirmPassword ? <FiEyeOff /> : <FiEye />}
                    </button>
                </Field>

                <button type="submit" className="neo-btn neo-btn-primary neo-btn-block neo-span-2" disabled={isLoading}>
                    {isLoading ? <span className="neo-spinner" /> : <>Complete registration <FiArrowRight /></>}
                </button>
            </form>

            <p className="neo-foot">
                Already registered? <Link to="/login">Sign in</Link>
            </p>
        </NeoAuthShell>
    );
}
