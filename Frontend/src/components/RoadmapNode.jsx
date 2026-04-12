<<<<<<< HEAD
import { FiChevronDown, FiChevronUp, FiZap, FiBookOpen } from 'react-icons/fi';

export default function RoadmapNode({ step, index, isExpanded, onToggle, side }) {
    return (
        <div className={`snake-card snake-card-${side}`}>
            {/* Arrow pointer toward center */}
            <div className={`snake-arrow snake-arrow-${side}`} />

            <div className="snake-card-inner" onClick={onToggle}>
                {/* Header */}
                <div className="snake-card-head">
                    <h4 className="snake-card-title">{step.title}</h4>
                    <button className="snake-toggle" aria-label="Toggle">
                        {isExpanded ? <FiChevronUp /> : <FiChevronDown />}
                    </button>
                </div>

                {/* Preview */}
                {!isExpanded && step.description && (
                    <p className="snake-card-preview">
                        {step.description.length > 100
                            ? step.description.substring(0, 100) + '…'
=======
import { FiChevronDown, FiChevronUp, FiZap, FiCheckCircle, FiClock, FiLock, FiCalendar, FiLoader } from 'react-icons/fi';

export default function RoadmapNode({ step, index, isExpanded, onToggle, side, onStepComplete, onGeneratePhaseDetailed, phaseBranch }) {

    const isLocked = step.status === 'locked';
    const isCompleted = step.status === 'completed';

    // Branch data from phaseBranches state
    const branchData = phaseBranch?.data;
    const branchLoading = phaseBranch?.loading;
    const branchSteps = branchData?.steps || branchData?.data?.steps || [];

    const handleGenerateDetailed = (e) => {
        e.stopPropagation();
        if (onGeneratePhaseDetailed && step.id) {
            onGeneratePhaseDetailed(step.id, false);
        }
    };

    const handleRegenerateDetailed = (e) => {
        e.stopPropagation();
        if (onGeneratePhaseDetailed && step.id) {
            onGeneratePhaseDetailed(step.id, true);
        }
    };



    return (
        <div className={`snake-card snake-card-${side}`}>
            <div className={`snake-arrow snake-arrow-${side}`} />

            <div className="snake-card-inner" onClick={isLocked ? undefined : onToggle}>
                {/* Status badge */}
                <div className="snake-status-badge">
                    <span className={`status-badge ${
                        isCompleted ? 'status-completed' : 
                        isLocked ? 'status-locked' : 
                        'status-pending'
                    }`}>
                        {isCompleted ? <><FiCheckCircle size={10} /> COMPLETED</> :
                         isLocked ? <><FiLock size={10} /> LOCKED</> :
                         <><FiClock size={10} /> PENDING</>}
                    </span>
                </div>

                {/* Header */}
                <div className="snake-card-head">
                    <h4 className="snake-card-title">{step.title}</h4>
                    <div className="snake-card-actions">
                        {!isCompleted && !isLocked && onStepComplete && (
                            <button
                                className="snake-mark-complete-btn"
                                onClick={(e) => { e.stopPropagation(); onStepComplete(step.id); }}
                                title="Mark as complete"
                            >
                                <FiCheckCircle />
                            </button>
                        )}
                        <button className="snake-toggle" aria-label="Toggle">
                            {isExpanded ? <FiChevronUp /> : <FiChevronDown />}
                        </button>
                    </div>
                </div>

                {/* Preview (collapsed) */}
                {!isExpanded && step.description && (
                    <p className="snake-card-preview">
                        {step.description.length > 120
                            ? step.description.substring(0, 120) + '…'
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
                            : step.description}
                    </p>
                )}

<<<<<<< HEAD
                {/* Expanded */}
=======
                {/* Expanded content */}
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
                {isExpanded && (
                    <div className="snake-card-body">
                        {step.description && (
                            <p className="snake-card-desc">{step.description}</p>
                        )}

<<<<<<< HEAD
=======
                        {/* Skills */}
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
                        {step.skills && step.skills.length > 0 && (
                            <div className="snake-section">
                                <div className="snake-section-title">
                                    <FiZap /> Skills
                                </div>
                                <div className="snake-tags">
                                    {step.skills.map((s, i) => (
                                        <span key={i} className="snake-tag">{s}</span>
                                    ))}
                                </div>
                            </div>
                        )}

<<<<<<< HEAD
                        {step.resources && step.resources.length > 0 && (
                            <div className="snake-section">
                                <div className="snake-section-title">
                                    <FiBookOpen /> Resources
                                </div>
                                <ul className="snake-resources">
                                    {step.resources.map((r, i) => (
                                        <li key={i}>{r}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
=======
                        {/* Detailed Roadmap section */}
                        <div className="snake-section" style={{ marginTop: '14px' }}>
                            <div className="snake-section-title">
                                <FiCalendar /> Detailed Roadmap
                            </div>

                            {branchSteps.length === 0 && !branchLoading && (
                                <button
                                    className="detailed-roadmap-btn"
                                    onClick={handleGenerateDetailed}
                                    disabled={branchLoading || isLocked}
                                >
                                    {branchLoading
                                        ? <><FiLoader className="spinning" /> Generating...</>
                                        : <><FiCalendar /> Generate Detailed Roadmap</>
                                    }
                                </button>
                            )}

                            {branchLoading && (
                                <div className="detailed-loading">
                                    <div className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }}></div>
                                    <span>Generating weekly roadmap...</span>
                                </div>
                            )}

                            {branchSteps.length > 0 && (
                                <div>
                                    <button
                                        className="regenerate-detailed-btn"
                                        onClick={handleRegenerateDetailed}
                                        disabled={branchLoading}
                                    >
                                        Regenerate Roadmap
                                    </button>
                                </div>
                            )}
                        </div>
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
                    </div>
                )}
            </div>
        </div>
    );
}
