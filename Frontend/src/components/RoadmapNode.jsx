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
                            : step.description}
                    </p>
                )}

                {/* Expanded */}
                {isExpanded && (
                    <div className="snake-card-body">
                        {step.description && (
                            <p className="snake-card-desc">{step.description}</p>
                        )}

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
                    </div>
                )}
            </div>
        </div>
    );
}
