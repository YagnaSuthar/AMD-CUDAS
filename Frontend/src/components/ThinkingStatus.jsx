import { useEffect, useState } from 'react';
import '../style/thinking.css';

const DEFAULT_MESSAGES = [
    'Syncing your profile data',
    'Reviewing your skills & projects',
    'Checking your academic performance',
    'Matching you with industry requirements',
    'Identifying your skill gaps',
    'Mapping the best career paths',
    'Crafting your personalized response',
    'Almost there, polishing the answer',
];

/**
 * Loading status that cycles through messages every `interval` ms with a
 * slide/fade transition, shimmering text and animated dots.
 */
export default function ThinkingStatus({ messages = DEFAULT_MESSAGES, interval = 3000, className = '', style }) {
    const [index, setIndex] = useState(0);

    useEffect(() => {
        const id = setInterval(() => {
            // Stop on the last message instead of looping back to the start
            setIndex((i) => Math.min(i + 1, messages.length - 1));
        }, interval);
        return () => clearInterval(id);
    }, [messages.length, interval]);

    return (
        <div className={`thinking-status ${className}`} style={style} role="status" aria-live="polite">
            <span className="thinking-orb" aria-hidden="true">
                <span /><span /><span />
            </span>
            <span className="thinking-text-wrap">
                <span key={index} className="thinking-text">
                    {messages[index]}
                </span>
                <span className="thinking-dots" aria-hidden="true">
                    <i /><i /><i />
                </span>
            </span>
            <span className="thinking-progress" aria-hidden="true">
                <span style={{ width: `${((index + 1) / messages.length) * 100}%` }} />
            </span>
        </div>
    );
}
