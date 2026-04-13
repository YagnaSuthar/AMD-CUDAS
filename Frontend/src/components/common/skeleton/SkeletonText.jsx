export default function SkeletonText({ variant = 'paragraph', style, className = '' }) {
    // variant can be 'title', 'subtitle', or 'paragraph'
    return (
        <div 
            className={`skeleton skeleton-text ${variant} ${className}`} 
            style={style}
        />
    );
}
