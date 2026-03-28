import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import RoadmapContainer from '../components/RoadmapContainer';
import { FiTarget, FiBookOpen, FiAward, FiBriefcase, FiTrendingUp, FiLoader, FiEdit2, FiSave, FiX, FiCheck, FiCompass, FiZap, FiShield, FiSend, FiMessageCircle } from 'react-icons/fi';
import '../style/roadmap.css';

export default function CareerGuidance() {
    const { user } = useAuth();
    const [goal, setGoal] = useState(user?.goal || '');
    const [isEditingGoal, setIsEditingGoal] = useState(false);
    const [tempGoal, setTempGoal] = useState('');
    const [roadmap, setRoadmap] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    // Career Guidance Chat
    const [guidanceQuery, setGuidanceQuery] = useState('');
    const [guidanceResponse, setGuidanceResponse] = useState(null);
    const [guidanceLoading, setGuidanceLoading] = useState(false);

    useEffect(() => {
        setGoal(user?.goal || '');
    }, [user]);

    const handleSaveGoal = async () => {
        try {
            await api.put('/auth/profile', { goal: tempGoal });
            setGoal(tempGoal);
            setIsEditingGoal(false);
            user.goal = tempGoal;
        } catch (err) {
            setError('Failed to save goal');
            console.error(err);
        }
    };

    const generateRoadmap = async () => {
        if (!goal) {
            setError('Please set your career goal first');
            return;
        }

        setLoading(true);
        setError('');
        setRoadmap(null);

        try {
            const response = await api.post('/college/student/career-roadmap');
            console.log('=== ROADMAP API RESPONSE ===');
            console.log('Full response:', JSON.stringify(response.data, null, 2));

            const apiData = response.data;

            // Validate response
            if (!apiData.success) {
                console.error('API returned error:', apiData.error);
                setError(apiData.error || 'Failed to generate roadmap');
                return;
            }

            const roadmapData = apiData.data;
            console.log('Roadmap data:', roadmapData);
            console.log('Steps array:', roadmapData?.steps);
            console.log('Steps count:', roadmapData?.steps?.length);

            // Validate roadmap structure
            if (roadmapData?.steps && Array.isArray(roadmapData.steps) && roadmapData.steps.length > 0) {
                // Ensure each step has required fields
                const validatedSteps = roadmapData.steps.map((step, idx) => ({
                    id: step.id || idx + 1,
                    title: step.title || `Step ${idx + 1}`,
                    description: step.description || '',
                    skills: Array.isArray(step.skills) ? step.skills : [],
                    resources: Array.isArray(step.resources) ? step.resources : [],
                    timeline: step.timeline || '',
                }));

                const validatedRoadmap = {
                    title: roadmapData.title || goal,
                    summary: roadmapData.summary || '',
                    steps: validatedSteps,
                };

                console.log('Validated roadmap:', validatedRoadmap);
                console.log('Setting roadmap state — should render now');
                setRoadmap(validatedRoadmap);
            } else if (roadmapData?.roadmap) {
                // Legacy markdown format — wrap in structured format
                console.log('Legacy markdown format detected');
                setRoadmap({
                    title: goal,
                    summary: 'Career roadmap based on your profile',
                    steps: [{
                        id: 1,
                        title: 'Your Career Roadmap',
                        description: roadmapData.roadmap.substring(0, 500),
                        skills: [],
                        resources: [],
                        timeline: 'See details below'
                    }],
                });
            } else {
                console.error('Invalid roadmap data structure:', roadmapData);
                setError('Invalid roadmap data received from server');
            }
        } catch (err) {
            console.error('Roadmap generation error:', err);
            setError(err.response?.data?.error || 'Failed to generate career roadmap');
        } finally {
            setLoading(false);
        }
    };

    const handleGuidanceQuery = async () => {
        if (!guidanceQuery.trim()) return;

        setGuidanceLoading(true);
        setGuidanceResponse(null);
        try {
            const response = await api.post('/rag/query-career-guidance', {
                query: guidanceQuery
            });
            console.log('=== GUIDANCE API RESPONSE ===', response.data);

            if (response.data.success) {
                setGuidanceResponse(response.data.data);
            } else {
                setError(response.data.error || 'Failed to get career guidance');
            }
        } catch (err) {
            setError('Failed to get career guidance');
            console.error(err);
        } finally {
            setGuidanceLoading(false);
        }
    };

    const startEditingGoal = () => {
        setTempGoal(goal);
        setIsEditingGoal(true);
    };

    const cancelEditingGoal = () => {
        setTempGoal('');
        setIsEditingGoal(false);
    };

    return (
        <div className="dashboard-content">
            <div className="page-header slide-in-left">
                <h1 className="gradient-text">Career Guidance</h1>
                <p>Plan your path to success with AI-powered personalized career guidance</p>
            </div>

            {/* Error Message — top level for visibility */}
            {error && (
                <div className="roadmap-error-banner">
                    <p>⚠️ {error}</p>
                    <button onClick={() => setError('')} className="error-dismiss">✕</button>
                </div>
            )}

            {/* Goal Section */}
            <div className="career-goal-section">
                <div className="goal-header">
                    <div className="goal-icon-wrapper">
                        <FiTarget className="goal-main-icon" />
                    </div>
                    <div className="goal-title-section">
                        <h2 className="goal-main-title">Your Career Aspiration</h2>
                        <p className="goal-subtitle">Define your dream and we'll create your path to success</p>
                    </div>
                </div>

                {isEditingGoal ? (
                    <div className="goal-editor-container">
                        <div className="goal-input-wrapper">
                            <textarea
                                value={tempGoal}
                                onChange={(e) => setTempGoal(e.target.value)}
                                placeholder="What's your dream career? Be specific! (e.g., 'Become a senior full-stack developer at a FAANG company')"
                                className="goal-textarea"
                                maxLength={500}
                            />
                            <div className="goal-input-footer">
                                <span className="goal-char-count">{tempGoal.length}/500</span>
                                <div className="goal-suggestions">
                                    <span className="suggestions-label">Popular goals:</span>
                                    {['Full-stack Developer', 'Data Scientist', 'Product Manager', 'AI Engineer', 'DevOps Engineer'].map((suggestion) => (
                                        <button
                                            key={suggestion}
                                            onClick={() => setTempGoal(`Become a ${suggestion}`)}
                                            className="suggestion-chip"
                                        >
                                            {suggestion}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>
                        <div className="goal-editor-actions">
                            <button
                                className="btn btn-primary goal-save-btn"
                                onClick={handleSaveGoal}
                                disabled={!tempGoal.trim()}
                            >
                                <FiSave /> Save Goal
                            </button>
                            <button
                                className="btn btn-secondary goal-cancel-btn"
                                onClick={cancelEditingGoal}
                            >
                                <FiX /> Cancel
                            </button>
                        </div>
                    </div>
                ) : goal ? (
                    <div className="goal-display-container">
                        <div className="goal-content">
                            <div className="goal-text">
                                <FiTarget className="goal-display-icon" />
                                <p>{goal}</p>
                            </div>
                            <div className="goal-actions">
                                <button className="btn btn-secondary goal-edit-btn" onClick={startEditingGoal}>
                                    <FiEdit2 /> Edit Goal
                                </button>
                                <button
                                    className="btn btn-primary goal-roadmap-btn"
                                    onClick={generateRoadmap}
                                    disabled={loading}
                                >
                                    {loading ? <FiLoader className="spinning" /> : <FiCompass />}
                                    {loading ? 'Generating...' : 'Generate Roadmap'}
                                </button>
                            </div>
                        </div>

                        {/* Quick Career Insights */}
                        <div className="career-insights">
                            <h4 className="insights-title"><FiZap /> Quick Career Insights</h4>
                            <div className="insights-grid">
                                <div className="insight-card">
                                    <div className="insight-icon"><FiTrendingUp /></div>
                                    <div className="insight-content">
                                        <h5>Growth Potential</h5>
                                        <p>High demand in tech industry with 22% projected growth</p>
                                    </div>
                                </div>
                                <div className="insight-card">
                                    <div className="insight-icon"><FiAward /></div>
                                    <div className="insight-content">
                                        <h5>Salary Range</h5>
                                        <p>₹6L - ₹25L+ depending on experience and location</p>
                                    </div>
                                </div>
                                <div className="insight-card">
                                    <div className="insight-icon"><FiBookOpen /></div>
                                    <div className="insight-content">
                                        <h5>Key Skills</h5>
                                        <p>JavaScript, Python, Cloud, System Design</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="goal-empty-state">
                        <div className="empty-icon"><FiTarget /></div>
                        <h3>What's Your Career Dream?</h3>
                        <p>Set your career goal to get personalized guidance, skill recommendations, and a step-by-step roadmap.</p>
                        <button className="btn btn-primary goal-set-btn" onClick={startEditingGoal}>
                            <FiTarget /> Set My Career Goal
                        </button>
                        <div className="career-suggestions">
                            <h4>Popular Career Paths</h4>
                            <div className="suggestion-cards">
                                {[
                                    { title: 'Full-Stack Developer', desc: 'Build complete web applications', icon: '💻' },
                                    { title: 'Data Scientist', desc: 'Analyze data and drive insights', icon: '📊' },
                                    { title: 'Product Manager', desc: 'Lead product strategy and teams', icon: '📱' },
                                    { title: 'AI/ML Engineer', desc: 'Create intelligent systems', icon: '🤖' }
                                ].map((career) => (
                                    <div key={career.title} className="career-card" onClick={() => { setTempGoal(`Become a ${career.title}`); setIsEditingGoal(true); }}>
                                        <div className="career-card-icon">{career.icon}</div>
                                        <h5>{career.title}</h5>
                                        <p>{career.desc}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* AI Career Guidance Chat */}
            {goal && (
                <div className="guidance-chat-section">
                    <div className="guidance-chat-header">
                        <div className="chat-header-icon"><FiMessageCircle /></div>
                        <div>
                            <h3>AI Career Advisor</h3>
                            <p>Ask anything about your career path — powered by RAG</p>
                        </div>
                    </div>

                    <div className="guidance-chat-input">
                        <textarea
                            value={guidanceQuery}
                            onChange={(e) => setGuidanceQuery(e.target.value)}
                            placeholder="Ask me about your career..."
                            className="guidance-textarea"
                            rows={3}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault();
                                    handleGuidanceQuery();
                                }
                            }}
                        />
                        <button
                            className="btn btn-primary guidance-send-btn"
                            onClick={handleGuidanceQuery}
                            disabled={guidanceLoading || !guidanceQuery.trim()}
                        >
                            {guidanceLoading ? <FiLoader className="spinning" /> : <FiSend />}
                        </button>
                    </div>

                    <div className="guidance-suggestions">
                        {['What skills do I need?', 'How to prepare for interviews?', 'Recommend learning resources', 'Career switch advice'].map((s) => (
                            <button key={s} className="guidance-suggestion-chip" onClick={() => setGuidanceQuery(s)}>
                                {s}
                            </button>
                        ))}
                    </div>

                    {guidanceResponse && (
                        <div className="guidance-response">
                            <div className="response-header">
                                <div className="response-badge">
                                    <FiShield />
                                    <span>{guidanceResponse.used_rag ? 'RAG-Enhanced' : 'Direct AI'}</span>
                                </div>
                                <span className="response-intent">{guidanceResponse.intent?.replace(/_/g, ' ')}</span>
                            </div>
                            <div className="response-content">
                                {guidanceResponse.response?.split('\n').map((line, idx) => (
                                    <p key={idx}>{line}</p>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Generate Roadmap Section */}
            {goal && (
                <div className="roadmap-main-section">
                    {!roadmap ? (
                        <div className="roadmap-generator">
                            <div className="generator-content">
                                <div className="generator-icon"><FiCompass /></div>
                                <h3>Your Personalized Career Roadmap</h3>
                                <p>Get a comprehensive career roadmap tailored to your goals, skills, and academic performance.</p>
                                <div className="generator-features">
                                    {['Personalized skill development plan', 'Timeline with actionable milestones', 'Learning resources & certifications', 'Interactive snake/zig-zag visualization'].map((f) => (
                                        <div key={f} className="feature-item">
                                            <FiCheck className="feature-icon" />
                                            <span>{f}</span>
                                        </div>
                                    ))}
                                </div>
                                <button className="btn btn-primary btn-lg generator-btn" onClick={generateRoadmap} disabled={loading}>
                                    {loading ? <><FiLoader className="spinning" /> Generating Your Roadmap...</> : <><FiCompass /> Generate My Career Roadmap</>}
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="roadmap-display">
                            <div className="roadmap-header-actions">
                                <div className="roadmap-title-section">
                                    <h3>Your Career Roadmap</h3>
                                    <p>Personalized path to achieve your career goals</p>
                                </div>
                            </div>

                            {/* Snake/Zig-Zag Roadmap UI */}
                            <RoadmapContainer roadmap={roadmap} />
                        </div>
                    )}
                </div>
            )}

            {/* Additional Resources */}
            <div className="dashboard-card fade-in-up fade-in-delay-2">
                <h3><FiBookOpen style={{ marginRight: '8px' }} /> Additional Resources</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '15px' }}>
                    {[
                        { icon: <FiBriefcase />, title: 'Job Opportunities', desc: 'Explore job listings that match your career goals and skills.', color: 'var(--color-secondary)' },
                        { icon: <FiAward />, title: 'Skill Development', desc: 'Identify and develop key skills needed for your target career.', color: 'var(--color-warning)' },
                        { icon: <FiTrendingUp />, title: 'Interview Preparation', desc: 'Practice AI-powered interviews tailored to your career goals.', color: 'var(--color-success)' }
                    ].map((r) => (
                        <div key={r.title} style={{ padding: '15px', backgroundColor: 'var(--color-bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}>
                            <div style={{ marginBottom: '10px', color: r.color }}>{r.icon}</div>
                            <h4 style={{ marginBottom: '8px' }}>{r.title}</h4>
                            <p style={{ fontSize: '14px', color: 'var(--color-text-muted)' }}>{r.desc}</p>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
