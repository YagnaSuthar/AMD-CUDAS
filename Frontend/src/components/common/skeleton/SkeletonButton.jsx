export default function SkeletonButton({ style, className = '' }) {
    return (
        <div 
            className={`skeleton skeleton-button ${className}`} 
            style={style}
        />
    );
}
