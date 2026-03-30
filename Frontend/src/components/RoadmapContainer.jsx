import { useState } from 'react';
import RoadmapNode from './RoadmapNode';
import { FiTarget, FiFlag, FiCheck, FiZap, FiBookOpen, FiCheckCircle, FiExternalLink, FiSend, FiGithub, FiLock } from 'react-icons/fi';

function WeekCardsRow({ branchSteps, step, onSubmitProject }) {
    const [submitLink, setSubmitLink] = useState('');
    const [expandedTasks, setExpandedTasks] = useState(new Set()); // Track expanded tasks
    // Track which weeks are completed (by index)
    const [completedWeeks, setCompletedWeeks] = useState(() => {
        // Initialize from branchSteps data if any are already completed
        const initial = new Set();
        branchSteps.forEach((ws, idx) => {
            if (ws.status === 'completed') initial.add(idx);
        });
        return initial;
    });

    const handleSubmit = (e) => {
        e.stopPropagation();
        if (onSubmitProject && submitLink.trim()) {
            onSubmitProject(step.id, submitLink.trim());
            setSubmitLink('');
        }
    };

    const markWeekComplete = (weekIdx) => {
        setCompletedWeeks((prev) => {
            const next = new Set(prev);
            next.add(weekIdx);
            return next;
        });
    };

    const toggleTaskExpansion = (taskId) => {
        setExpandedTasks((prev) => {
            const next = new Set(prev);
            if (next.has(taskId)) {
                next.delete(taskId);
            } else {
                next.add(taskId);
            }
            return next;
        });
    };

    // Determine week status: completed / active (first non-completed) / locked
    const getWeekStatus = (wIdx) => {
        if (completedWeeks.has(wIdx)) return 'completed';
        // First non-completed week is active
        for (let i = 0; i < branchSteps.length; i++) {
            if (!completedWeeks.has(i)) {
                return i === wIdx ? 'active' : 'locked';
            }
        }
        return 'locked';
    };

    return (
        <div className="week-cards-scroll-container">
            <div className="week-cards-scroll-header">
                Showing {branchSteps.length} of {branchSteps.length} weeks • {completedWeeks.size} completed
            </div>
            <div className="week-cards-horizontal">
                {branchSteps.map((ws, wIdx) => {
                    const isLastWeek = wIdx === branchSteps.length - 1;
                    const topics = ws.topics || [];
                    const tasks = ws.tasks || [];
                    const resources = ws.resources || [];
                    const weekStatus = getWeekStatus(wIdx);
                    const isWeekLocked = weekStatus === 'locked';
                    const isWeekCompleted = weekStatus === 'completed';
                    const isWeekActive = weekStatus === 'active';

                    return (
                        <div key={ws.id || wIdx} className={`week-hcard ${isWeekLocked ? 'week-hcard-locked' : ''} ${isWeekCompleted ? 'week-hcard-completed' : ''}`}>
                            <div className="week-hcard-header">
                                <span className="week-hcard-title">Week {ws.week || wIdx + 1}</span>
                                {isWeekCompleted ? (
                                    <FiCheckCircle className="week-hcard-check completed" />
                                ) : isWeekLocked ? (
                                    <FiLock className="week-hcard-check locked" />
                                ) : (
                                    <FiCheckCircle className="week-hcard-check" />
                                )}
                            </div>

                            {/* Content always visible — locked cards just greyed via CSS */}
                            <>
                                    {/* Topics */}
                                    {topics.length > 0 && (
                                        <div className="week-hcard-section">
                                            <div className="week-hcard-label">
                                                <FiZap size={11} /> TOPICS
                                            </div>
                                            <div className="week-hcard-tags">
                                                {topics.map((t, i) => (
                                                    <span key={i} className="week-hcard-tag">{t.length > 25 ? t.slice(0, 25) + '…' : t}</span>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Tasks */}
                                    {tasks.length > 0 && (
                                        <div className="week-hcard-section">
                                            <div className="week-hcard-label">
                                                <FiCheckCircle size={11} /> TASKS
                                            </div>
                                            <ul className="week-hcard-tasks">
                                                {tasks.map((t, i) => {
                                                    const taskId = `${wIdx}-${i}`;
                                                    const isExpanded = expandedTasks.has(taskId);
                                                    const isTruncated = t.length > 40;
                                                    
                                                    return (
                                                        <li 
                                                            key={i} 
                                                            onClick={(e) => {
                                                                if (isTruncated) {
                                                                    e.stopPropagation();
                                                                    toggleTaskExpansion(taskId);
                                                                }
                                                            }}
                                                            style={{ cursor: isTruncated ? 'pointer' : 'default' }}
                                                            title={isTruncated && !isExpanded ? "Click to view full task" : ""}
                                                        >
                                                            {isExpanded ? t : (isTruncated ? t.slice(0, 40) + '…' : t)}
                                                        </li>
                                                    );
                                                })}
                                            </ul>
                                        </div>
                                    )}

                                    {/* Resources */}
                                    {resources.length > 0 && (
                                        <div className="week-hcard-section">
                                            <div className="week-hcard-label">
                                                <FiBookOpen size={11} /> RESOURCES
                                            </div>
                                            <div className="week-hcard-resources">
                                                {resources.map((r, i) => {
                                                    let title, url;
                                                    if (typeof r === 'string') {
                                                        title = r;
                                                        url = null;
                                                    } else {
                                                        title = r.title || r.name || 'Resource';
                                                        url = r.link || r.url || null;
                                                    }
                                                    const shortTitle = title.split(' ').slice(0, 3).join(' ');
                                                    const href = url || `https://www.google.com/search?q=${encodeURIComponent(title)}`;
                                                    return (
                                                        <a key={i} href={href} target="_blank" rel="noopener noreferrer" className="week-hcard-resource-link" title={title}>
                                                            <FiExternalLink size={10} />
                                                            <span>{shortTitle}</span>
                                                        </a>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    )}

                                    {/* Deliverable */}
                                    {ws.deliverable && (
                                        <div className="week-hcard-deliverable">
                                            <strong>Deliverable:</strong> {ws.deliverable.length > 50 ? ws.deliverable.slice(0, 50) + '…' : ws.deliverable}
                                        </div>
                                    )}

                                    {/* Submit Project (last week) */}
                                    {isLastWeek && ws.submission_required && (
                                        <div className="week-hcard-submit">
                                            <div className="week-hcard-label">
                                                <FiSend size={11} /> SUBMIT PROJECT
                                            </div>
                                            <div className="week-submit-form">
                                                <div className="week-submit-input-wrap">
                                                    <FiGithub size={12} />
                                                    <input
                                                        type="text"
                                                        placeholder="GitHub link"
                                                        value={submitLink}
                                                        onChange={(e) => setSubmitLink(e.target.value)}
                                                    />
                                                </div>
                                                <button className="week-submit-btn" onClick={handleSubmit} disabled={!submitLink.trim()}>
                                                    <FiCheckCircle size={12} /> Submit
                                                </button>
                                            </div>
                                        </div>
                                    )}

                                    {/* Mark Week Complete button */}
                                    {isWeekActive && !isWeekCompleted && (
                                        <button className="week-complete-btn" onClick={() => markWeekComplete(wIdx)}>
                                            <FiCheckCircle size={12} /> Mark Week Complete
                                        </button>
                                    )}
                                </>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}




export default function RoadmapContainer({ roadmap, onStepComplete, phaseBranches, onGeneratePhaseDetailed, onMarkBranchStepComplete, onSubmitProject }) {
    const [expandedIndex, setExpandedIndex] = useState(null);

    if (!roadmap || !roadmap.steps || roadmap.steps.length === 0) {
        return null;
    }

    const handleToggle = (index) => {
        setExpandedIndex(expandedIndex === index ? null : index);
    };

    return (
        <div className="snake-timeline">
            {/* Header */}
            <div className="snake-header">
                <span className="snake-start-badge">
                    <FiTarget /> Start
                </span>
                <h3 className="snake-title">{roadmap.title}</h3>
                {roadmap.summary && (
                    <p className="snake-subtitle">{roadmap.summary}</p>
                )}
            </div>

            {/* Timeline rows */}
            <div className="snake-track">
                {roadmap.steps.map((step, index) => {
                    const isLeft = index % 2 === 0;
                    const isLast = index === roadmap.steps.length - 1;
                    const statusClass = step.status === 'completed' ? 'snake-card-completed'
                        : step.status === 'locked' ? 'snake-card-locked' : '';
                    const isExpanded = expandedIndex === index;
                    const phaseBranch = phaseBranches?.[step.id] || null;

                    return (
                        <div key={step.id || index} className="snake-step-group">
                            <div
                                className={`snake-row ${statusClass} ${isExpanded ? 'snake-row-expanded' : ''}`}
                                style={{ animationDelay: `${index * 0.1}s` }}
                            >
                                {/* LEFT column */}
                                <div className="snake-col snake-col-left">
                                    {isLeft && (
                                        <RoadmapNode
                                            step={step}
                                            index={index}
                                            isExpanded={isExpanded}
                                            onToggle={() => handleToggle(index)}
                                            side="left"
                                            onStepComplete={onStepComplete}
                                            onGeneratePhaseDetailed={onGeneratePhaseDetailed}
                                            phaseBranch={phaseBranch}
                                            onSubmitProject={onSubmitProject}
                                        />
                                    )}
                                    {!isLeft && (
                                        <div className="snake-badge-cell">
                                            <span className="snake-badge">{step.timeline || `Step ${index + 1}`}</span>
                                        </div>
                                    )}
                                </div>

                                {/* CENTER column — dot + line */}
                                <div className="snake-col snake-col-center">
                                    <div className={`snake-line-top ${index === 0 ? 'snake-line-hidden' : ''}`} />
                                    <div className={`snake-dot ${isLast ? 'snake-dot-last' : ''} ${step.status === 'completed' ? 'snake-dot-completed' : ''}`}>
                                        {step.status === 'completed'
                                            ? <FiCheck style={{ color: 'white', fontSize: '0.85rem' }} />
                                            : <span className="snake-dot-number">{index + 1}</span>
                                        }
                                    </div>
                                    <div className={`snake-line-bottom ${isLast ? 'snake-line-hidden' : ''}`} />
                                </div>

                                {/* RIGHT column */}
                                <div className="snake-col snake-col-right">
                                    {!isLeft && (
                                        <RoadmapNode
                                            step={step}
                                            index={index}
                                            isExpanded={isExpanded}
                                            onToggle={() => handleToggle(index)}
                                            side="right"
                                            onStepComplete={onStepComplete}
                                            onGeneratePhaseDetailed={onGeneratePhaseDetailed}
                                            phaseBranch={phaseBranch}
                                            onSubmitProject={onSubmitProject}
                                        />
                                    )}
                                    {isLeft && (
                                        <div className="snake-badge-cell">
                                            <span className="snake-badge">{step.timeline || `Step ${index + 1}`}</span>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Week cards - FULL WIDTH below the step row */}
                            {isExpanded && phaseBranch && (phaseBranch?.data?.steps || phaseBranch?.data?.data?.steps || []).length > 0 && (
                                <div className="week-cards-fullwidth">
                                    <WeekCardsRow branchSteps={phaseBranch?.data?.steps || phaseBranch?.data?.data?.steps || []} step={step} onSubmitProject={onSubmitProject} />
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Footer */}
            <div className="snake-footer">
                <span className="snake-finish-badge">
                    <FiFlag /> Goal Achieved! 🎉
                </span>
            </div>
        </div>
    );
}
