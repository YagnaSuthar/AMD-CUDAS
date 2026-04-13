import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { SIDEBAR_ROUTES } from '../utils/roles';
import SkeletonText from './common/skeleton/SkeletonText';
import SkeletonCard from './common/skeleton/SkeletonCard';

export default function ProtectedRoute({ allowedRoles }) {
    const { user, loading } = useAuth();

    if (loading) {
        return (
            <div style={{ padding: '40px', flex: 1, width: '100%', maxWidth: '1400px', margin: '0 auto' }}>
                <SkeletonText variant="title" style={{ width: '250px', marginBottom: '16px' }} />
                <SkeletonText variant="subtitle" style={{ width: '400px', marginBottom: '32px' }} />
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px', marginBottom: '24px' }}>
                    {Array.from({ length: 4 }).map((_, i) => (
                        <SkeletonCard key={i} style={{ height: '120px' }} />
                    ))}
                </div>
                <SkeletonCard style={{ height: '400px' }} />
            </div>
        );
    }

    // Not logged in
    if (!user) {
        return <Navigate to="/login" replace />;
    }

    // Check role authorization if specified
    if (allowedRoles && !allowedRoles.includes(user.role)) {
        // If not authorized for this specific route, redirect back to their role's dashboard home
        return <Navigate to={SIDEBAR_ROUTES[user.role]?.[0]?.path || '/dashboard'} replace />;
    }

    return <Outlet />;
}
