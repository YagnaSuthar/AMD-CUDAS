export default function SkeletonAvatar({ size = 'md', style, className = '' }) {
    // size can be 'sm', 'md', 'lg'
    return (
        <div 
            className={`skeleton skeleton-avatar ${size !== 'md' ? size : ''} ${className}`} 
            style={style}
        />
    );
}
