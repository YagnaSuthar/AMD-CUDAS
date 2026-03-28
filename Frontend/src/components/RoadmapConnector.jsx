export default function RoadmapConnector({ direction, isLast }) {
    if (isLast) return null;

    return (
        <div className={`roadmap-connector connector-${direction}`}>
            <svg viewBox="0 0 200 80" preserveAspectRatio="none" className="connector-svg">
                <defs>
                    <linearGradient id={`grad-${direction}`} x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#00bcd4" stopOpacity="0.6" />
                        <stop offset="50%" stopColor="#00bcd4" stopOpacity="1" />
                        <stop offset="100%" stopColor="#00bcd4" stopOpacity="0.6" />
                    </linearGradient>
                </defs>
                {direction === 'left-to-right' ? (
                    <path
                        d="M 20 10 Q 100 10 100 40 Q 100 70 180 70"
                        fill="none"
                        stroke={`url(#grad-${direction})`}
                        strokeWidth="3"
                        strokeLinecap="round"
                        className="connector-path"
                    />
                ) : (
                    <path
                        d="M 180 10 Q 100 10 100 40 Q 100 70 20 70"
                        fill="none"
                        stroke={`url(#grad-${direction})`}
                        strokeWidth="3"
                        strokeLinecap="round"
                        className="connector-path"
                    />
                )}
            </svg>
        </div>
    );
}
