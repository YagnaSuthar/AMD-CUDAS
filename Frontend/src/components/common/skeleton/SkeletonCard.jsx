import SkeletonText from './SkeletonText';

export default function SkeletonCard({ style, className = '' }) {
    return (
        <div className={`skeleton-card ${className}`} style={style}>
            <SkeletonText variant="title" />
            <SkeletonText variant="paragraph" />
            <SkeletonText variant="paragraph" />
        </div>
    );
}
