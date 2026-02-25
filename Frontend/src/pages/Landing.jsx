import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import AnimatedBackground from '../components/AnimatedBackground';
import AuthNavbar from '../components/AuthNavbar';
import {
    FiArrowRight,
    FiShield,
    FiTrendingUp,
    FiCpu,
    FiBookOpen,
    FiBarChart2,
    FiMap,
    FiMic,
    FiCheckCircle,
    FiGlobe,
} from 'react-icons/fi';

export default function Landing() {
    const { user } = useAuth();

    return (
        <div className="landing-page">
            <AnimatedBackground />

            <AuthNavbar
                rightContent={
                    user ? (
                        <Link to="/dashboard" className="btn btn-primary">
                            Go to Dashboard <FiArrowRight />
                        </Link>
                    ) : (
                        <>
                            <Link to="/login" className="btn btn-secondary">Login</Link>
                            <Link to="/register" className="btn btn-primary">Register College</Link>
                        </>
                    )
                }
            />

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

            <section className="features-section features-section-tight">
                <div className="section-header fade-in-up">
                    <h2 className="gradient-text-secondary">
                        AI Agents That Work For Every Role
                    </h2>
                    <p>
                        CUDAS is powered by specialized AI agents designed to support academic planning,
                        skill development, interview readiness, and institutional decision-making.
                    </p>
                </div>

                <div className="features-grid">
                    <div className="feature-card fade-in-up fade-in-delay-1">
                        <div className="feature-icon"><FiBookOpen /></div>
                        <h3>Academic Planner</h3>
                        <p>
                            Analyzes exam timetables and performance data to generate personalized
                            subject-wise preparation strategies.
                        </p>
                    </div>

                    <div className="feature-card fade-in-up fade-in-delay-2">
                        <div className="feature-icon"><FiBarChart2 /></div>
                        <h3>Performance Analyzer</h3>
                        <p>
                            Identifies strengths, weaknesses, and readiness levels to help students
                            improve systematically.
                        </p>
                    </div>

                    <div className="feature-card fade-in-up fade-in-delay-3">
                        <div className="feature-icon"><FiMap /></div>
                        <h3>Career Advisor</h3>
                        <p>
                            Suggests skill development paths, certifications, MOOCs, and career
                            roadmaps based on academic data and goals.
                        </p>
                    </div>

                    <div className="feature-card fade-in-up fade-in-delay-1">
                        <div className="feature-icon"><FiMic /></div>
                        <h3>Interview Conductor</h3>
                        <p>
                            Conducts AI-powered mock and live interviews using voice interaction
                            and real-time technical questioning.
                        </p>
                    </div>

                    <div className="feature-card fade-in-up fade-in-delay-2">
                        <div className="feature-icon"><FiCheckCircle /></div>
                        <h3>Interview Evaluation Agent</h3>
                        <p>
                            Generates detailed performance reports covering communication,
                            confidence, clarity, and technical understanding.
                        </p>
                    </div>

                    <div className="feature-card fade-in-up fade-in-delay-3">
                        <div className="feature-icon"><FiGlobe /></div>
                        <h3>Multilingual Voice Assistant</h3>
                        <p>
                            Provides voice and text-based guidance in multiple Indian languages
                            for inclusive and accessible AI support.
                        </p>
                    </div>
                </div>
            </section>

            <section className="impact-panel-section">
                <div className="impact-panel fade-in-up">
                    <div className="impact-left">
                        <h2 className="gradient-text-secondary">
                            Transforming Education Through Intelligent Infrastructure
                        </h2>

                        <p className="impact-subtext">
                            CUDAS is designed to become a digital backbone for academic
                            and career ecosystems.
                        </p>

                        <p className="impact-tagline">
                            Bridging the gap between education and employment with intelligence and trust.
                        </p>
                    </div>

                    <div className="impact-right">
                        <div className="impact-list">
                            <div className="impact-point fade-in-up fade-in-delay-1">
                                <FiCheckCircle />
                                <span>AI-driven academic planning</span>
                            </div>

                            <div className="impact-point fade-in-up fade-in-delay-1">
                                <FiCheckCircle />
                                <span>Verified digital student identities</span>
                            </div>

                            <div className="impact-point fade-in-up fade-in-delay-2">
                                <FiCheckCircle />
                                <span>Transparent institutional analytics</span>
                            </div>

                            <div className="impact-point fade-in-up fade-in-delay-2">
                                <FiCheckCircle />
                                <span>Data-driven hiring decisions</span>
                            </div>

                            <div className="impact-point fade-in-up fade-in-delay-3">
                                <FiCheckCircle />
                                <span>Inclusive multilingual AI support</span>
                            </div>
                        </div>
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
