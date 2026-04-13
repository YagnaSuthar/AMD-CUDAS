export default function SkeletonTableRow({ columns = 4, className = '' }) {
    return (
        <tr className={className}>
            {Array.from({ length: columns }).map((_, i) => (
                <td key={i}>
                    <div className="skeleton skeleton-text" style={{ marginBottom: 0 }} />
                </td>
            ))}
        </tr>
    );
}
