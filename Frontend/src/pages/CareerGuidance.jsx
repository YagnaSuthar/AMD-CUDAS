import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { FiTarget, FiBookOpen, FiAward, FiBriefcase, FiTrendingUp, FiLoader, FiEdit2, FiSave, FiX, FiCheck, FiAlertCircle, FiStar, FiCompass, FiZap, FiShield } from 'react-icons/fi';
import '../style/roadmap.css';

export default function CareerGuidance() {
    const { user } = useAuth();
    const [goal, setGoal] = useState(user?.goal || '');
    const [isEditingGoal, setIsEditingGoal] = useState(false);
    const [tempGoal, setTempGoal] = useState('');
    const [roadmap, setRoadmap] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        setGoal(user?.goal || '');
    }, [user]);

    const handleSaveGoal = async () => {
        try {
            const response = await api.put('/auth/profile', { goal: tempGoal });
            setGoal(tempGoal);
            setIsEditingGoal(false);
            // Update user context
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
        try {
            const response = await api.post('/college/student/career-roadmap');
            console.log('Roadmap response:', response.data); // Debug log
            setRoadmap(response.data);
        } catch (err) {
            setError('Failed to generate career roadmap');
            console.error('Roadmap error:', err);
        } finally {
            setLoading(false);
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

    // Helper functions to parse and format roadmap content
    const extractSection = (content, sectionTitle) => {
        const lines = content.split('\n');
        let sectionContent = [];
        let inSection = false;
        
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (line.startsWith('## ') && line.toLowerCase().includes(sectionTitle.toLowerCase())) {
                inSection = true;
                continue;
            }
            if (line.startsWith('## ') && inSection) {
                break;
            }
            if (inSection && line && !line.startsWith('#')) {
                sectionContent.push(line);
            }
        }
        
        const result = sectionContent.join(' ').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        return result || 'Content not available';
    };

    const formatSkillsSection = (content) => {
        const lines = content.split('\n');
        const technicalSkills = [];
        const softSkills = [];
        
        let currentSection = null;
        
        lines.forEach(line => {
            if (line.toLowerCase().includes('technical skills')) {
                currentSection = technicalSkills;
            } else if (line.toLowerCase().includes('soft skills')) {
                currentSection = softSkills;
            } else if (line.startsWith('-') && currentSection) {
                const skill = line.replace(/^-\s*\*\*/, '').replace(/\*\*/, '').trim();
                if (skill) currentSection.push(skill);
            }
        });
        
        return (
            <div className="skills-grid">
                <div className="skill-category">
                    <h4>Technical Skills</h4>
                    <ul>
                        {technicalSkills.length > 0 ? technicalSkills.map((skill, idx) => (
                            <li key={idx}>{skill}</li>
                        )) : <li>Core programming, Data structures, System design</li>}
                    </ul>
                </div>
                <div className="skill-category">
                    <h4>Soft Skills</h4>
                    <ul>
                        {softSkills.length > 0 ? softSkills.map((skill, idx) => (
                            <li key={idx}>{skill}</li>
                        )) : <li>Communication, Team collaboration, Problem-solving</li>}
                    </ul>
                </div>
            </div>
        );
    };

    const extractTimelineItems = (content, sectionTitle) => {
        const lines = content.split('\n');
        let items = [];
        let inSection = false;
        
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (line.startsWith('## ') && line.toLowerCase().includes(sectionTitle.toLowerCase())) {
                inSection = true;
                continue;
            }
            if (line.startsWith('## ') && inSection) {
                break;
            }
            if (inSection && line.match(/^\d+\./)) {
                const cleanLine = line.replace(/^\d+\.\s*/, '').replace(/\*\*(.*?)\*\*/g, '$1');
                if (cleanLine) {
                    items.push(<li key={items.length}>{cleanLine}</li>);
                }
            }
        }
        
        if (items.length === 0) {
            // Default items based on section
            if (sectionTitle.includes('Short-term')) {
                return [
                    <li key="default1">Build foundational skills through online courses</li>,
                    <li key="default2">Create personal projects to showcase abilities</li>,
                    <li key="default3">Network with professionals in target field</li>
                ];
            } else if (sectionTitle.includes('Medium-term')) {
                return [
                    <li key="default1">Apply for internships to gain practical experience</li>,
                    <li key="default2">Contribute to open-source projects</li>,
                    <li key="default3">Obtain relevant certifications</li>
                ];
            } else {
                return [
                    <li key="default1">Apply for entry-level positions in target field</li>,
                    <li key="default2">Build professional network</li>,
                    <li key="default3">Continue learning and skill development</li>
                ];
            }
        }
        
        return items;
    };

    const formatResourcesSection = (content) => {
        const defaultResources = {
            'Online Learning': ['Coursera, edX courses', 'YouTube tutorials', 'Technical blogs'],
            'Certifications': ['Industry-recognized certifications', 'Cloud computing certs', 'Domain-specific certs'],
            'Practice Platforms': ['LeetCode for coding', 'GitHub for projects', 'Kaggle for data science']
        };
        
        return (
            <div className="resources-grid">
                {Object.entries(defaultResources).map(([category, items]) => (
                    <div key={category} className="resource-category">
                        <h4>{category}</h4>
                        <ul>
                            {items.map((item, idx) => (
                                <li key={idx}>{item}</li>
                            ))}
                        </ul>
                    </div>
                ))}
            </div>
        );
    };

    const formatChallengesSection = (content) => {
        const defaultChallenges = [
            { title: 'Academic Pressure', solution: 'Time management and prioritization' },
            { title: 'Skill Gap', solution: 'Consistent learning and practice' },
            { title: 'Competition', solution: 'Differentiate with unique projects' },
            { title: 'Work-Life Balance', solution: 'Set boundaries and maintain health' }
        ];
        
        return (
            <div className="challenges-list">
                {defaultChallenges.map((challenge, idx) => (
                    <div key={idx} className="challenge-item">
                        <div className="challenge-title">⚠️ {challenge.title}</div>
                        <div className="challenge-solution">💡 {challenge.solution}</div>
                    </div>
                ))}
            </div>
        );
    };

    const formatSuccessTips = (content) => {
        const defaultTips = [
            'Stay consistent with daily efforts',
            'Seek regular feedback for improvement',
            'Build practical projects and portfolio',
            'Network with industry professionals',
            'Stay curious and keep learning'
        ];
        
        return (
            <ul className="success-tips-list">
                {defaultTips.map((tip, idx) => (
                    <li key={idx}>{tip}</li>
                ))}
            </ul>
        );
    };

    return (
        <div className="dashboard-content">
            <div className="page-header slide-in-left">
                <h1 className="gradient-text">Career Guidance</h1>
                <p>Plan your path to success with personalized career guidance</p>
            </div>

            {/* Goal Section with Modern Design */}
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
                                placeholder="What's your dream career? Be specific! (e.g., 'Become a senior full-stack developer at a FAANG company', 'Start my own AI startup', 'Lead data science team at a fintech company')"
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
                                disabled={!tempGoal.trim() || loading}
                            >
                                {loading ? <FiLoader className="spinning" /> : <FiSave />}
                                {loading ? 'Saving...' : 'Save Goal'}
                            </button>
                            <button 
                                className="btn btn-secondary goal-cancel-btn"
                                onClick={cancelEditingGoal}
                            >
                                <FiX />
                                Cancel
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
                                    className="btn btn-outline-primary goal-edit-btn"
                                    onClick={startEditingGoal}
                                >
                                    <FiEdit2 />
                                    Edit Goal
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
                            <h4 className="insights-title">
                                <FiZap />
                                Quick Career Insights
                            </h4>
                            <div className="insights-grid">
                                <div className="insight-card">
                                    <div className="insight-icon">
                                        <FiTrendingUp />
                                    </div>
                                    <div className="insight-content">
                                        <h5>Growth Potential</h5>
                                        <p>High demand in tech industry with 22% projected growth</p>
                                    </div>
                                </div>
                                <div className="insight-card">
                                    <div className="insight-icon">
                                        <FiAward />
                                    </div>
                                    <div className="insight-content">
                                        <h5>Salary Range</h5>
                                        <p>$80K - $150K+ depending on experience and location</p>
                                    </div>
                                </div>
                                <div className="insight-card">
                                    <div className="insight-icon">
                                        <FiBookOpen />
                                    </div>
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
                        <div className="empty-icon">
                            <FiTarget />
                        </div>
                        <h3>What's Your Career Dream?</h3>
                        <p>Set your career goal to get personalized guidance, skill recommendations, and a step-by-step roadmap to achieve your dreams.</p>
                        <button 
                            className="btn btn-primary goal-set-btn"
                            onClick={startEditingGoal}
                        >
                            <FiTarget />
                            Set My Career Goal
                        </button>
                        
                        {/* Career Suggestions */}
                        <div className="career-suggestions">
                            <h4>Popular Career Paths</h4>
                            <div className="suggestion-cards">
                                {[
                                    { title: 'Full-Stack Developer', desc: 'Build complete web applications', icon: '💻' },
                                    { title: 'Data Scientist', desc: 'Analyze data and drive insights', icon: '📊' },
                                    { title: 'Product Manager', desc: 'Lead product strategy and teams', icon: '📱' },
                                    { title: 'AI/ML Engineer', desc: 'Create intelligent systems', icon: '🤖' }
                                ].map((career) => (
                                    <div key={career.title} className="career-card">
                                        <div className="career-card-icon">{career.icon}</div>
                                        <h5>{career.title}</h5>
                                        <p>{career.desc}</p>
                                        <button 
                                            className="btn btn-outline-secondary career-select-btn"
                                            onClick={() => {
                                                setTempGoal(`Become a ${career.title}`);
                                                setIsEditingGoal(true);
                                            }}
                                        >
                                            Choose This Path
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Generate Roadmap Section */}
            {goal && (
                <div className="roadmap-main-section">
                    {!roadmap ? (
                        <div className="roadmap-generator">
                            <div className="generator-content">
                                <div className="generator-icon">
                                    <FiCompass />
                                </div>
                                <h3>Your Personalized Career Roadmap</h3>
                                <p>Get a comprehensive career roadmap tailored to your goals, skills, and academic performance. Our AI analyzes your profile to create a step-by-step path to success.</p>
                                
                                <div className="generator-features">
                                    <div className="feature-item">
                                        <FiCheck className="feature-icon" />
                                        <span>Personalized skill development plan</span>
                                    </div>
                                    <div className="feature-item">
                                        <FiCheck className="feature-icon" />
                                        <span>Timeline with short, medium & long-term goals</span>
                                    </div>
                                    <div className="feature-item">
                                        <FiCheck className="feature-icon" />
                                        <span>Learning resources & certification recommendations</span>
                                    </div>
                                    <div className="feature-item">
                                        <FiCheck className="feature-icon" />
                                        <span>Industry insights & salary expectations</span>
                                    </div>
                                </div>
                                
                                <button 
                                    className="btn btn-primary btn-lg generator-btn"
                                    onClick={generateRoadmap}
                                    disabled={loading}
                                >
                                    {loading ? (
                                        <>
                                            <FiLoader className="spinning" />
                                            Generating Your Roadmap...
                                        </>
                                    ) : (
                                        <>
                                            <FiCompass />
                                            Generate My Career Roadmap
                                        </>
                                    )}
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
                                <button 
                                    className="btn btn-outline-primary regenerate-btn"
                                    onClick={generateRoadmap}
                                    disabled={loading}
                                >
                                    {loading ? <FiLoader className="spinning" /> : <FiTrendingUp />}
                                    Regenerate
                                </button>
                            </div>
                            
                            <div className="roadmap-container">
                                <div className="roadmap-hero">
                                    <div className="hero-content">
                                        <h2>
                                            {roadmap.roadmap.split('\n').find(line => line.startsWith('# Career Roadmap:'))?.replace('# Career Roadmap:', '').trim() || 'Your Career Roadmap'}
                                        </h2>
                                        <p>AI-powered personalized career guidance based on your unique profile</p>
                                        <div className="hero-stats">
                                            <div className="stat-item">
                                                <span className="stat-number">94%</span>
                                                <span className="stat-label">Match Score</span>
                                            </div>
                                            <div className="stat-item">
                                                <span className="stat-number">12</span>
                                                <span className="stat-label">Key Skills</span>
                                            </div>
                                            <div className="stat-item">
                                                <span className="stat-number">36</span>
                                                <span className="stat-label">Month Plan</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="hero-visual">
                                        <div className="orbit-container">
                                            <div className="orbit-center">
                                                <FiTarget />
                                            </div>
                                            <div className="orbit orbit-1">
                                                <FiStar />
                                            </div>
                                            <div className="orbit orbit-2">
                                                <FiAward />
                                            </div>
                                            <div className="orbit orbit-3">
                                                <FiTrendingUp />
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div className="roadmap-content-grid">
                                    {/* Goal Analysis */}
                                    <div className="roadmap-card analysis-card">
                                        <div className="card-header">
                                            <div className="card-icon analysis-icon">
                                                <FiTarget />
                                            </div>
                                            <h4>Goal Analysis</h4>
                                        </div>
                                        <div className="card-content">
                                            <div className="analysis-text">
                                                <div dangerouslySetInnerHTML={{ __html: extractSection(roadmap.roadmap, 'Career Goal Analysis') || 'Your career goal has been analyzed and a personalized path has been created for you.' }} />
                                            </div>
                                            <div className="match-meter">
                                                <div className="meter-label">Goal Match</div>
                                                <div className="meter-bar">
                                                    <div className="meter-fill" style={{ width: '94%' }}></div>
                                                </div>
                                                <span className="meter-value">94%</span>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Performance */}
                                    <div className="roadmap-card performance-card">
                                        <div className="card-header">
                                            <div className="card-icon performance-icon">
                                                <FiTrendingUp />
                                            </div>
                                            <h4>Current Performance</h4>
                                        </div>
                                        <div className="card-content">
                                            <div className="performance-metrics">
                                                <div className="metric">
                                                    <span className="metric-label">Academic Score</span>
                                                    <span className="metric-value excellent">94%</span>
                                                </div>
                                                <div className="metric">
                                                    <span className="metric-label">Skills Level</span>
                                                    <span className="metric-value good">Intermediate</span>
                                                </div>
                                                <div className="metric">
                                                    <span className="metric-label">Progress</span>
                                                    <span className="metric-value">On Track</span>
                                                </div>
                                            </div>
                                            <div className="performance-insight">
                                                <div dangerouslySetInnerHTML={{ __html: extractSection(roadmap.roadmap, 'Current Academic Performance') || 'Your academic performance has been assessed to provide personalized recommendations.' }} />
                                            </div>
                                        </div>
                                    </div>

                                    {/* Skills */}
                                    <div className="roadmap-card skills-card">
                                        <div className="card-header">
                                            <div className="card-icon skills-icon">
                                                <FiZap />
                                            </div>
                                            <h4>Skill Development</h4>
                                        </div>
                                        <div className="card-content">
                                            {formatSkillsSection(roadmap.roadmap)}
                                        </div>
                                    </div>

                                    {/* Timeline */}
                                    <div className="roadmap-card timeline-card full-width">
                                        <div className="card-header">
                                            <div className="card-icon timeline-icon">
                                                <FiCompass />
                                            </div>
                                            <h4>Career Timeline</h4>
                                        </div>
                                        <div className="card-content">
                                            <div className="timeline-modern">
                                                <div className="timeline-phase">
                                                    <div className="phase-header">
                                                        <div className="phase-marker short"></div>
                                                        <div className="phase-info">
                                                            <h5>Short-term</h5>
                                                            <span>Next 6 months</span>
                                                        </div>
                                                    </div>
                                                    <div className="phase-content">
                                                        <ul>
                                                            {extractTimelineItems(roadmap.roadmap, 'Short-term Goals (Next 6 Months)')}
                                                        </ul>
                                                    </div>
                                                </div>

                                                <div className="timeline-phase">
                                                    <div className="phase-header">
                                                        <div className="phase-marker medium"></div>
                                                        <div className="phase-info">
                                                            <h5>Medium-term</h5>
                                                            <span>6-18 months</span>
                                                        </div>
                                                    </div>
                                                    <div className="phase-content">
                                                        <ul>
                                                            {extractTimelineItems(roadmap.roadmap, 'Medium-term Goals (6-18 Months)')}
                                                        </ul>
                                                    </div>
                                                </div>

                                                <div className="timeline-phase">
                                                    <div className="phase-header">
                                                        <div className="phase-marker long"></div>
                                                        <div className="phase-info">
                                                            <h5>Long-term</h5>
                                                            <span>18+ months</span>
                                                        </div>
                                                    </div>
                                                    <div className="phase-content">
                                                        <ul>
                                                            {extractTimelineItems(roadmap.roadmap, 'Long-term Goals (18+ Months)')}
                                                        </ul>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Resources */}
                                    <div className="roadmap-card resources-card">
                                        <div className="card-header">
                                            <div className="card-icon resources-icon">
                                                <FiBookOpen />
                                            </div>
                                            <h4>Learning Resources</h4>
                                        </div>
                                        <div className="card-content">
                                            {formatResourcesSection(roadmap.roadmap)}
                                        </div>
                                    </div>

                                    {/* Challenges */}
                                    <div className="roadmap-card challenges-card">
                                        <div className="card-header">
                                            <div className="card-icon challenges-icon">
                                                <FiAlertCircle />
                                            </div>
                                            <h4>Challenges & Solutions</h4>
                                        </div>
                                        <div className="card-content">
                                            {formatChallengesSection(roadmap.roadmap)}
                                        </div>
                                    </div>

                                    {/* Success Tips */}
                                    <div className="roadmap-card tips-card full-width">
                                        <div className="card-header">
                                            <div className="card-icon tips-icon">
                                                <FiStar />
                                            </div>
                                            <h4>Success Tips</h4>
                                        </div>
                                        <div className="card-content">
                                            {formatSuccessTips(roadmap.roadmap)}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Error Message */}
            {error && (
                <div className="dashboard-card fade-in-up" style={{ 
                    backgroundColor: 'var(--color-error-bg)', 
                    border: '1px solid var(--color-error)',
                    color: 'var(--color-error)'
                }}>
                    <p>{error}</p>
                </div>
            )}

            {/* Additional Resources */}
            <div className="dashboard-card fade-in-up fade-in-delay-2">
                <h3>
                    <FiBookOpen style={{ marginRight: '8px' }} />
                    Additional Resources
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '15px' }}>
                    <div style={{ 
                        padding: '15px',
                        backgroundColor: 'var(--color-bg-secondary)',
                        borderRadius: '8px',
                        border: '1px solid var(--color-border)'
                    }}>
                        <FiBriefcase style={{ marginBottom: '10px', color: 'var(--color-secondary)' }} />
                        <h4 style={{ marginBottom: '8px' }}>Job Opportunities</h4>
                        <p style={{ fontSize: '14px', color: 'var(--color-text-muted)' }}>
                            Explore job listings that match your career goals and skills.
                        </p>
                    </div>
                    <div style={{ 
                        padding: '15px',
                        backgroundColor: 'var(--color-bg-secondary)',
                        borderRadius: '8px',
                        border: '1px solid var(--color-border)'
                    }}>
                        <FiAward style={{ marginBottom: '10px', color: 'var(--color-warning)' }} />
                        <h4 style={{ marginBottom: '8px' }}>Skill Development</h4>
                        <p style={{ fontSize: '14px', color: 'var(--color-text-muted)' }}>
                            Identify and develop key skills needed for your target career.
                        </p>
                    </div>
                    <div style={{ 
                        padding: '15px',
                        backgroundColor: 'var(--color-bg-secondary)',
                        borderRadius: '8px',
                        border: '1px solid var(--color-border)'
                    }}>
                        <FiTrendingUp style={{ marginBottom: '10px', color: 'var(--color-success)' }} />
                        <h4 style={{ marginBottom: '8px' }}>Interview Preparation</h4>
                        <p style={{ fontSize: '14px', color: 'var(--color-text-muted)' }}>
                            Practice AI-powered interviews tailored to your career goals.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
