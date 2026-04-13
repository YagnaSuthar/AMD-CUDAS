import SkeletonAvatar from './SkeletonAvatar';
import SkeletonText from './SkeletonText';

export default function SkeletonListItem({ style, className = '' }) {
    return (
        <div className={`skeleton-list-item ${className}`} style={style}>
            <SkeletonAvatar size="md" />
            <div style={{ flex: 1 }}>
                <SkeletonText variant="subtitle" />
                <SkeletonText variant="paragraph" style={{ width: '80%', marginBottom: 0 }} />
            </div>
        </div>
    );
}
