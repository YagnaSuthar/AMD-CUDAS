import { useState } from 'react';
import RoadmapNode from './RoadmapNode';
import { FiTarget, FiFlag } from 'react-icons/fi';

export default function RoadmapContainer({ roadmap }) {
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

                    return (
                        <div
                            key={step.id || index}
                            className="snake-row"
                            style={{ animationDelay: `${index * 0.1}s` }}
                        >
                            {/* LEFT column */}
                            <div className="snake-col snake-col-left">
                                {isLeft && (
                                    <RoadmapNode
                                        step={step}
                                        index={index}
                                        isExpanded={expandedIndex === index}
                                        onToggle={() => handleToggle(index)}
                                        side="left"
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
                                <div className="snake-line-top" />
                                <div className={`snake-dot ${isLast ? 'snake-dot-last' : ''}`}>
                                    <span className="snake-dot-number">{index + 1}</span>
                                </div>
                                <div className={`snake-line-bottom ${isLast ? 'snake-line-hidden' : ''}`} />
                            </div>

                            {/* RIGHT column */}
                            <div className="snake-col snake-col-right">
                                {!isLeft && (
                                    <RoadmapNode
                                        step={step}
                                        index={index}
                                        isExpanded={expandedIndex === index}
                                        onToggle={() => handleToggle(index)}
                                        side="right"
                                    />
                                )}
                                {isLeft && (
                                    <div className="snake-badge-cell">
                                        <span className="snake-badge">{step.timeline || `Step ${index + 1}`}</span>
                                    </div>
                                )}
                            </div>
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
