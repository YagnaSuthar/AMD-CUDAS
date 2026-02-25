import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { SIDEBAR_ROUTES } from '../utils/roles';

export default function ProtectedRoute({ allowedRoles }) {
    const { user, loading } = useAuth();

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
                <div className="spinner"></div>
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
