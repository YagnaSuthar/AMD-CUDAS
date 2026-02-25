import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import AnimatedBackground from '../components/AnimatedBackground';
import { FiArrowRight, FiShield, FiTrendingUp, FiCpu } from 'react-icons/fi';

export default function Landing() {
    const { user } = useAuth();

    return (
        <div className="landing-page">
            <AnimatedBackground />

            <nav className="landing-nav fade-in-up">
                <div className="landing-nav-brand gradient-text">CUDAS.</div>
                <div className="landing-nav-links">
                    {user ? (
                        <Link to="/dashboard" className="btn btn-primary">
                            Go to Dashboard <FiArrowRight />
                        </Link>
                    ) : (
                        <>
                            <Link to="/login" className="btn btn-secondary">Login</Link>
                            <Link to="/register" className="btn btn-primary">Register College</Link>
                        </>
                    )}
                </div>
            </nav>

            <section className="hero">
                <div className="hero-content fade-in-up fade-in-delay-1">
                    <span className="hero-badge pulse-glow">Advanced Agentic AI</span>
                    <h1 className="gradient-text">The Future of Education & Placement</h1>
                    <p>
                        An AI-powered platform for colleges, students, and recruiters.
                        Streamline learning, ace your interviews, and get hired faster with
                        CUDAS multi-agent system.
                    </p>
                    <div className="hero-buttons">
                        <Link to={user ? "/dashboard" : "/register"} className="btn btn-primary btn-lg hover-scale">
                            Get Started Now <FiArrowRight />
                        </Link>
                    </div>
                </div>
            </section>

            <section className="features-section">
                <div className="section-header fade-in-up">
                    <h2 className="gradient-text-secondary">Why Choose CUDAS?</h2>
                    <p>A unified hierarchy system that connects every level of education.</p>
                </div>

                <div className="features-grid">
                    <div className="feature-card fade-in-up fade-in-delay-1">
                        <div className="feature-icon"><FiShield /></div>
                        <h3>Role-Based Hierarchy</h3>
                        <p>From Principals to Students, every user has tailored access. HODs manage faculty, faculty manage students.</p>
                    </div>
                    <div className="feature-card fade-in-up fade-in-delay-2">
                        <div className="feature-icon"><FiCpu /></div>
                        <h3>AI Interview Agents</h3>
                        <p>Students practice technical and behavioral interviews with our advanced LLM voice agents.</p>
                    </div>
                    <div className="feature-card fade-in-up fade-in-delay-3">
                        <div className="feature-icon"><FiTrendingUp /></div>
                        <h3>Powerful Analytics</h3>
                        <p>CUDAS Admins and Principals get a bird's-eye view of all platform metrics and student growth.</p>
                    </div>
                </div>
            </section>

            <section className="cta-section">
                <h2 className="gradient-text">Ready to transform your institution?</h2>
                <p>Register your college today and bring the power of AI to your students.</p>
                <Link to="/register" className="btn btn-primary hover-scale">
                    Register Your College <FiArrowRight />
                </Link>
            </section>

            <footer className="landing-footer">
                © 2026 CUDAS Education Platform. Powered by AI Agents.
            </footer>
        </div>
    );
}
