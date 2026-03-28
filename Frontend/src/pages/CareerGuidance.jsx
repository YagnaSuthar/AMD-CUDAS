import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import RoadmapContainer from '../components/RoadmapContainer';
import { FiTarget, FiBookOpen, FiAward, FiBriefcase, FiTrendingUp, FiLoader, FiEdit2, FiSave, FiX, FiCheck, FiCompass, FiZap, FiShield, FiSend, FiMessageCircle, FiLock, FiCheckCircle, FiClock } from 'react-icons/fi';
import '../style/roadmap.css';

export default function CareerGuidance() {
    const { user } = useAuth();
    const [goal, setGoal] = useState(user?.goal || '');
    const [isEditingGoal, setIsEditingGoal] = useState(false);
    const [tempGoal, setTempGoal] = useState('');
    const [roadmap, setRoadmap] = useState(null);
    const [phaseBranches, setPhaseBranches] = useState({});
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [goalChangeInfo, setGoalChangeInfo] = useState(null);

    // Career Guidance Chat
    const [guidanceQuery, setGuidanceQuery] = useState('');
    const [guidanceResponse, setGuidanceResponse] = useState(null);
    const [guidanceLoading, setGuidanceLoading] = useState(false);

    useEffect(() => {
        setGoal(user?.goal || '');
        // Set goal change info from user data
        if (user) {
            setGoalChangeInfo({
                goal_change_count: user.goal_change_count || 0,
                last_goal_updated_at: user.last_goal_updated_at,
                discipline_score: user.discipline_score || 100,
                locked_until: user.locked_until
            });
            // Load existing saved roadmap from DB on mount
            if (user.goal) {
                loadSavedRoadmap(user.goal);
            }
        }
    }, [user]);

    // Load saved roadmap + weekly plans from DB
    const loadSavedRoadmap = async (effectiveGoal) => {
        setLoading(true);
        setError('');
        try {
            const response = await api.get('/rag/my-roadmap');
            const apiData = response.data?.data;

            if (apiData && apiData.steps && apiData.steps.length > 0) {
                // Saved roadmap exists — restore it
                const rawSteps = apiData.steps;
                const firstPendingIndex = rawSteps.findIndex((s) => s.status === 'pending');

                const transformedSteps = rawSteps.map((step, idx) => {
                    const isLocked = firstPendingIndex !== -1 && step.status === 'pending' && idx > firstPendingIndex;
                    return {
                        id: step.id,
                        title: step.title || step.phase,
                        description: step.description,
                        skills: step.skills || [],
                        resources: step.resources || [],
                        timeline: step.timeline || step.duration || `Step ${idx + 1}`,
                        status: isLocked ? 'locked' : step.status,
                    };
                });

                setRoadmap({
                    title: apiData.goal || effectiveGoal,
                    summary: 'Personalized roadmap based on your profile',
                    steps: transformedSteps,
                });

                // Restore saved weekly branch plans
                if (apiData.phase_branches) {
                    const restoredBranches = {};
                    for (const [phaseId, branchData] of Object.entries(apiData.phase_branches)) {
                        restoredBranches[phaseId] = {
                            loading: false,
                            error: '',
                            data: branchData,
                        };
                    }
                    setPhaseBranches(restoredBranches);
                }
            } else {
                // No saved roadmap — generate fresh
                await generateRoadmap(false, effectiveGoal);
            }
        } catch (err) {
            console.error('Error loading saved roadmap:', err);
            // Fallback: try generating
            await generateRoadmap(false, effectiveGoal);
        } finally {
            setLoading(false);
        }
    };


    const handleSaveGoal = async () => {
        try {
            await api.put('/auth/profile', { goal: tempGoal });
            
            const nextGoal = tempGoal;
            setGoal(nextGoal);
            setIsEditingGoal(false);
            user.goal = nextGoal;
            
            // Clear roadmap and force-generate a fresh one for the new goal
            setRoadmap(null);
            await generateRoadmap(true, nextGoal);
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to save goal');
            console.error(err);
        }
    };

    const generateRoadmap = async (forceRegenerate = false, goalOverride = null) => {
        const effectiveGoal = (goalOverride ?? goal ?? '').trim();
        if (!effectiveGoal) {
            setError('Please set your career goal first');
            return;
        }

        setLoading(true);
        setError('');

        try {
            const response = await api.post('/rag/generate-roadmap', { force_regenerate: forceRegenerate });
            console.log('=== ROADMAP API RESPONSE ===');
            console.log('Full response:', JSON.stringify(response.data, null, 2));

            const apiResponse = response.data;
            // Backend wraps under {success, data: {...steps, goal, ...}}
            const apiData = apiResponse.data || apiResponse;

            const rawSteps = Array.isArray(apiData.steps) ? apiData.steps : [];
            const firstPendingIndex = rawSteps.findIndex((s) => s.status === 'pending');

            // Transform steps to match existing UI structure.
            // UI "locked" state: any pending step after the first pending step.
            const transformedSteps = rawSteps.map((step, idx) => {
                const isLocked = firstPendingIndex !== -1 && step.status === 'pending' && idx > firstPendingIndex;
                return {
                    id: step.id,
                    title: step.title || step.phase,
                    description: step.description,
                    skills: step.skills || [],
                    resources: step.resources || [],
                    timeline: step.timeline || step.duration || `Step ${idx + 1}`,
                    status: isLocked ? 'locked' : step.status,
                };
            });

            const validatedRoadmap = {
                title: apiData.goal || effectiveGoal,
                summary: apiData.current_level_estimation 
                    ? `Personalized roadmap (${apiData.current_level_estimation})`
                    : 'Personalized roadmap based on your profile',
                steps: transformedSteps,
            };

            console.log('Validated roadmap:', validatedRoadmap);
            setRoadmap(validatedRoadmap);
        } catch (err) {
            console.error('Roadmap generation error:', err);
            setError(err.response?.data?.detail || 'Failed to generate career roadmap');
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

    const markStepComplete = async (stepId) => {
        try {
            await api.post('/rag/mark-step-complete', { step_id: stepId });

            // Update status IN-PLACE — only unlock the NEXT step
            setRoadmap((prev) => {
                if (!prev) return prev;

                // First, mark the clicked step as completed
                const updatedSteps = prev.steps.map((s) =>
                    s.id === stepId ? { ...s, status: 'completed' } : s
                );

                // Find the first non-completed step and make ONLY that one 'pending'
                let firstNonCompleteFound = false;
                const finalSteps = updatedSteps.map((s) => {
                    if (s.status === 'completed') return s;
                    if (!firstNonCompleteFound) {
                        firstNonCompleteFound = true;
                        return { ...s, status: 'pending' };
                    }
                    return { ...s, status: 'locked' };
                });

                return { ...prev, steps: finalSteps };
            });
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to mark step as complete');
            console.error(err);
        }
    };

    const generatePhaseDetailedRoadmap = async (phaseId, forceRegenerate = false) => {
        setPhaseBranches((prev) => ({
            ...prev,
            [phaseId]: {
                ...(prev?.[phaseId] || {}),
                loading: true,
                error: '',
            },
        }));

        try {
            const response = await api.post('/rag/generate-phase-detailed-roadmap', {
                phase_id: phaseId,
                force_regenerate: forceRegenerate,
            });
            setPhaseBranches((prev) => ({
                ...prev,
                [phaseId]: {
                    loading: false,
                    error: '',
                    data: response.data,
                },
            }));
        } catch (err) {
            setPhaseBranches((prev) => ({
                ...prev,
                [phaseId]: {
                    ...(prev?.[phaseId] || {}),
                    loading: false,
                    error: err.response?.data?.detail || 'Failed to generate detailed roadmap',
                },
            }));
        }
    };

    const markBranchStepComplete = async (phaseId, branchStepId) => {
        try {
            const response = await api.post('/mark-branch-step-complete', { branch_step_id: branchStepId });
            setPhaseBranches((prev) => ({
                ...prev,
                [phaseId]: {
                    ...(prev?.[phaseId] || {}),
                    data: response.data,
                },
            }));
        } catch (err) {
            setPhaseBranches((prev) => ({
                ...prev,
                [phaseId]: {
                    ...(prev?.[phaseId] || {}),
                    error: err.response?.data?.detail || 'Failed to mark week as complete',
                },
            }));
        }
    };

    const submitProject = async (phaseId, branchStepId, githubLink) => {
        try {
            const response = await api.post('/submit-project', {
                branch_step_id: branchStepId,
                github_link: githubLink,
            });
            setPhaseBranches((prev) => ({
                ...prev,
                [phaseId]: {
                    ...(prev?.[phaseId] || {}),
                    data: response.data,
                },
            }));
        } catch (err) {
            setPhaseBranches((prev) => ({
                ...prev,
                [phaseId]: {
                    ...(prev?.[phaseId] || {}),
                    error: err.response?.data?.detail || 'Failed to submit project link',
                },
            }));
        }
    };

    const isGoalLocked = () => {
        if (!goalChangeInfo?.locked_until) return false;
        return new Date(goalChangeInfo.locked_until) > new Date();
    };

    const getLockoutMessage = () => {
        if (!isGoalLocked()) return null;
        const lockDate = new Date(goalChangeInfo.locked_until);
        return `Goal changes locked until ${lockDate.toLocaleDateString()} due to frequent changes. Focus on your current path!`;
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
                                <button 
                                    className="btn btn-secondary goal-edit-btn" 
                                    onClick={startEditingGoal}
                                    disabled={isGoalLocked()}
                                    title={isGoalLocked() ? getLockoutMessage() : 'Edit goal'}
                                >
                                    {isGoalLocked() ? <FiLock /> : <FiEdit2 />} 
                                    {isGoalLocked() ? 'Locked' : 'Edit Goal'}
                                </button>
                                <button
                                    className="btn btn-primary goal-roadmap-btn"
                                    onClick={() => generateRoadmap(false)}
                                    disabled={loading}
                                >
                                    {loading ? <FiLoader className="spinning" /> : <FiCompass />}
                                    {loading ? 'Generating...' : 'Generate Roadmap'}
                                </button>
                            </div>
                        </div>

                        {/* Goal Change Info */}
                        {goalChangeInfo && (
                            <div className="goal-change-info">
                                <div className="goal-stats">
                                    <div className="goal-stat">
                                        <FiCheckCircle className="stat-icon" />
                                        <span className="stat-label">Discipline Score:</span>
                                        <span className="stat-value">{goalChangeInfo.discipline_score}</span>
                                    </div>
                                    <div className="goal-stat">
                                        <FiEdit2 className="stat-icon" />
                                        <span className="stat-label">Goal Changes:</span>
                                        <span className="stat-value">{goalChangeInfo.goal_change_count}</span>
                                    </div>
                                    {goalChangeInfo.last_goal_updated_at && (
                                        <div className="goal-stat">
                                            <FiClock className="stat-icon" />
                                            <span className="stat-label">Last Updated:</span>
                                            <span className="stat-value">{new Date(goalChangeInfo.last_goal_updated_at).toLocaleDateString()}</span>
                                        </div>
                                    )}
                                </div>
                                {isGoalLocked() && (
                                    <div className="goal-lockout-notice">
                                        <FiLock className="lock-icon" />
                                        <span>{getLockoutMessage()}</span>
                                    </div>
                                )}
                            </div>
                        )}

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
                                <button className="btn btn-primary btn-lg generator-btn" onClick={() => generateRoadmap(false)} disabled={loading}>
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
                            <RoadmapContainer
                                roadmap={roadmap}
                                onStepComplete={markStepComplete}
                                phaseBranches={phaseBranches}
                                onGeneratePhaseDetailed={generatePhaseDetailedRoadmap}
                                onMarkBranchStepComplete={markBranchStepComplete}
                                onSubmitProject={submitProject}
                            />
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
