import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import AuthNavbar, { BrandMark } from '../components/AuthNavbar';
import {
    FiArrowRight, FiShield, FiTrendingUp, FiCpu, FiBookOpen, FiBarChart2, FiMap, FiMic,
    FiCheckCircle, FiGlobe, FiUsers, FiUploadCloud, FiMail, FiTarget, FiBriefcase, FiAward,
    FiLayers, FiUserCheck, FiZap,
} from 'react-icons/fi';

const AGENTS = [
    { icon: FiBookOpen, title: 'Academic Planner', text: 'Reads exam timetables and performance data to build subject-wise preparation strategies.' },
    { icon: FiBarChart2, title: 'Performance Analyzer', text: 'Surfaces strengths, weak spots and readiness levels so students improve systematically.' },
    { icon: FiMap, title: 'Career Advisor', text: 'Suggests skills, certifications, MOOCs and roadmaps grounded in academic data and goals.' },
    { icon: FiMic, title: 'Interview Conductor', text: 'Runs AI mock and live interviews with real-time voice and technical questioning.' },
    { icon: FiCheckCircle, title: 'Evaluation Agent', text: 'Produces detailed reports on communication, confidence, clarity and technical depth.' },
    { icon: FiGlobe, title: 'Multilingual Voice', text: 'Guides by voice and text in multiple Indian languages for inclusive AI support.' },
];

const ROLES = [
    { id: 'principal', label: 'Principal', icon: FiShield, headline: 'Run the whole institution from one cockpit.',
      items: ['Register the college & onboard staff', 'Department-wise analytics', 'Connect with recruiting companies', 'Certificates & leaderboards'] },
    { id: 'hod', label: 'HOD', icon: FiLayers, headline: 'Keep every department on track.',
      items: ['Manage faculty and subject assignments', 'Monitor marks & timetables', 'Spot at-risk students early', 'Message faculty and students'] },
    { id: 'faculty', label: 'Faculty', icon: FiUserCheck, headline: 'Teach more, administrate less.',
      items: ['Upload marks and attendance', 'Track class performance', 'Assign aptitude practice', 'Review interview reports'] },
    { id: 'student', label: 'Student', icon: FiAward, headline: 'Practice, grow and get hired.',
      items: ['AI mock interviews with live transcript', 'Aptitude practice & reports', 'Personal career roadmap', 'Apply to jobs from partner companies'] },
    { id: 'recruiter', label: 'Recruiter', icon: FiBriefcase, headline: 'Hire interview-ready talent.',
      items: ['Post jobs to partner colleges', 'AI-evaluated interview scores', 'Round 2 meetings built-in', 'Data-driven shortlists'] },
];

const BRIDGE = [
    { icon: FiTarget, title: 'Skill insights', text: 'Assessments highlight strengths and the skills worth building next.' },
    { icon: FiBriefcase, title: 'Internships & jobs', text: 'Opportunities from partner companies, recommended by fit.' },
    { icon: FiBookOpen, title: 'Industry learning', text: 'Workshops, certifications and mentorship from people in the field.' },
    { icon: FiAward, title: 'Digital portfolio', text: 'Verified skills, projects and certificates in one shareable profile.' },
];

const FLOW = [
    { icon: FiShield, title: 'Register', text: 'Principal or recruiter creates an account and verifies email.' },
    { icon: FiUploadCloud, title: 'Onboard', text: 'Upload HODs, faculty and students in bulk via CSV.' },
    { icon: FiMail, title: 'Credentials', text: 'Every user receives secure login credentials by email.' },
    { icon: FiTarget, title: 'Prepare', text: 'Students train with aptitude, AI interviews and roadmaps.' },
    { icon: FiBriefcase, title: 'Get hired', text: 'Recruiters shortlist with AI reports and Round 2 meets.' },
];

export default function Landing() {
    const { user } = useAuth();
    const [activeRole, setActiveRole] = useState(ROLES[0].id);
    const role = ROLES.find((r) => r.id === activeRole);

    return (
        <div className="neo-landing">
            <AuthNavbar
                links={
                    <>
                        <a href="#agents">AI Agents</a>
                        <a href="#roles">Roles</a>
                        <a href="#flow">How it works</a>
                    </>
                }
                rightContent={
                    user ? (
                        <Link to="/dashboard" className="neo-btn neo-btn-primary neo-btn-sm">
                            Dashboard <FiArrowRight />
                        </Link>
                    ) : (
                        <>
                            <Link to="/login" className="neo-btn neo-btn-ghost neo-btn-sm">Login</Link>
                            <Link to="/register" className="neo-btn neo-btn-primary neo-btn-sm neo-hide-xs">Get started</Link>
                        </>
                    )
                }
            />

            {/* ── Hero ─────────────────────────────────────────────── */}
            <section className="neo-hero">
                <div className="neo-hero-copy fade-in-up">
                    <span className="neo-pill"><FiZap /> Advanced Agentic AI for campuses</span>
                    <h1>
                        The future of <span className="neo-grad">education</span> &amp; <span className="neo-grad">placement</span>.
                    </h1>
                    <p>
                        CUDAS connects colleges, students and recruiters on one multi-agent AI platform —
                        streamline learning, ace interviews and get hired faster.
                    </p>
                    <div className="neo-hero-cta">
                        <Link to={user ? '/dashboard' : '/register'} className="neo-btn neo-btn-primary neo-btn-lg">
                            {user ? 'Open dashboard' : 'Register your college'} <FiArrowRight />
                        </Link>
                        {!user && (
                            <Link to="/login" className="neo-btn neo-btn-ghost neo-btn-lg">Sign in</Link>
                        )}
                    </div>
                    <div className="neo-stats">
                        <div><strong>6</strong><span>AI agents</span></div>
                        <div><strong>5</strong><span>User roles</span></div>
                        <div><strong>24/7</strong><span>Interview practice</span></div>
                    </div>
                </div>

                <div className="neo-hero-visual fade-in-up fade-in-delay-2" aria-hidden="true">
                    <div className="neo-orb">
                        <div className="neo-orb-ring" />
                        <div className="neo-orb-ring neo-orb-ring-2" />
                        <div className="neo-orb-core">
                            <img src="/cudas-logo.png" alt="" />
                        </div>
                    </div>

                    <div className="neo-float neo-float-1"><FiMic /> AI Interview</div>
                    <div className="neo-float neo-float-2"><FiTrendingUp /> Analytics</div>
                    <div className="neo-float neo-float-3"><FiMap /> Career Map</div>

                    <div className="neo-score">
                        <div className="neo-ring" style={{ '--p': 86 }}><span>86</span></div>
                        <div>
                            <strong>Interview score</strong>
                            <small>Communication · Technical</small>
                            <div className="neo-bars"><i style={{ width: '82%' }} /><i style={{ width: '64%' }} /></div>
                        </div>
                    </div>
                </div>
            </section>

            {/* ── Pillars ──────────────────────────────────────────── */}
            <section className="neo-section">
                <div className="neo-pillars">
                    <div className="neo-pillar"><span className="neo-icon"><FiShield /></span><div><h3>Role-based hierarchy</h3><p>Principal → HOD → Faculty → Student, each with tailored access.</p></div></div>
                    <div className="neo-pillar"><span className="neo-icon"><FiCpu /></span><div><h3>AI interview agents</h3><p>Technical & behavioural practice with LLM voice agents.</p></div></div>
                    <div className="neo-pillar"><span className="neo-icon"><FiTrendingUp /></span><div><h3>Powerful analytics</h3><p>A bird's-eye view of platform metrics and student growth.</p></div></div>
                </div>
            </section>

            {/* ── Agents ───────────────────────────────────────────── */}
            <section className="neo-section" id="agents">
                <div className="neo-section-head">
                    <span className="neo-eyebrow">Multi-agent system</span>
                    <h2>AI agents that work for <span className="neo-grad">every role</span></h2>
                    <p>Specialised agents for academic planning, skill development, interview readiness and institutional decisions.</p>
                </div>
                <div className="neo-agents">
                    {AGENTS.map(({ icon: Icon, title, text }, i) => (
                        <article key={title} className="neo-agent">
                            <span className="neo-agent-num">0{i + 1}</span>
                            <span className="neo-icon neo-icon-lg"><Icon /></span>
                            <h3>{title}</h3>
                            <p>{text}</p>
                        </article>
                    ))}
                </div>
            </section>

            {/* ── Roles ────────────────────────────────────────────── */}
            <section className="neo-section" id="roles">
                <div className="neo-section-head">
                    <span className="neo-eyebrow">Built for everyone</span>
                    <h2>One platform, <span className="neo-grad">five dashboards</span></h2>
                </div>

                <div className="neo-roles">
                    <div className="neo-role-tabs" role="tablist">
                        {ROLES.map(({ id, label, icon: Icon }) => (
                            <button
                                key={id}
                                role="tab"
                                aria-selected={activeRole === id}
                                className={`neo-role-tab ${activeRole === id ? 'is-active' : ''}`}
                                onClick={() => setActiveRole(id)}
                            >
                                <Icon /> {label}
                            </button>
                        ))}
                    </div>

                    <div className="neo-role-panel" key={role.id}>
                        <div className="neo-role-copy">
                            <span className="neo-icon neo-icon-xl"><role.icon /></span>
                            <h3>{role.headline}</h3>
                            <Link to={role.id === 'recruiter' || role.id === 'principal' ? '/register' : '/login'} className="neo-link">
                                {role.id === 'recruiter' || role.id === 'principal' ? 'Register now' : 'Sign in with your credentials'} <FiArrowRight />
                            </Link>
                        </div>
                        <ul className="neo-role-list">
                            {role.items.map((it) => (
                                <li key={it}><FiCheckCircle /> {it}</li>
                            ))}
                        </ul>
                    </div>
                </div>
            </section>

            {/* ── Campus to career ─────────────────────────────────── */}
            <section className="neo-section">
                <div className="neo-bridge">
                    <div className="neo-bridge-copy">
                        <span className="neo-eyebrow">Campus to career</span>
                        <h2>Where learning meets <span className="neo-grad">real opportunity</span></h2>
                        <p>
                            Students, faculty and industry partners work in the same place, so skills are
                            built with a clear goal and opportunities go to the people ready for them.
                        </p>
                        <Link to={user ? '/dashboard' : '/register'} className="neo-link">
                            Explore the platform <FiArrowRight />
                        </Link>
                    </div>
                    <div className="neo-bridge-grid">
                        {BRIDGE.map(({ icon: Icon, title, text }) => (
                            <div key={title} className="neo-bridge-card">
                                <span className="neo-icon"><Icon /></span>
                                <h3>{title}</h3>
                                <p>{text}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── Flow ─────────────────────────────────────────────── */}
            <section className="neo-section" id="flow">
                <div className="neo-section-head">
                    <span className="neo-eyebrow">How it works</span>
                    <h2>From registration to <span className="neo-grad">placement</span></h2>
                </div>
                <ol className="neo-flow">
                    {FLOW.map(({ icon: Icon, title, text }, i) => (
                        <li key={title} className="neo-flow-step">
                            <span className="neo-flow-dot"><Icon /><em>{i + 1}</em></span>
                            <h3>{title}</h3>
                            <p>{text}</p>
                        </li>
                    ))}
                </ol>
            </section>

            {/* ── CTA ──────────────────────────────────────────────── */}
            <section className="neo-section">
                <div className="neo-cta">
                    <div>
                        <h2>Ready to transform your institution?</h2>
                        <p>Bridging the gap between education and employment with intelligence and trust.</p>
                        <div className="neo-cta-tags">
                            <span><FiUsers /> Verified student identities</span>
                            <span><FiBarChart2 /> Transparent analytics</span>
                            <span><FiGlobe /> Multilingual AI</span>
                        </div>
                    </div>
                    <Link to={user ? '/dashboard' : '/register'} className="neo-btn neo-btn-primary neo-btn-lg">
                        {user ? 'Go to dashboard' : 'Register your college'} <FiArrowRight />
                    </Link>
                </div>
            </section>

            <footer className="neo-footer">
                <BrandMark size="sm" />
                <span>© 2026 CUDAS Education Platform. Powered by AI Agents.</span>
            </footer>
        </div>
    );
}
