import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { SIDEBAR_ROUTES, ROLE_LABELS } from '../utils/roles';
import { FiX } from 'react-icons/fi';

export default function Sidebar({ isOpen, onClose }) {
    const { user } = useAuth();

    if (!user) return null;

    const routes = SIDEBAR_ROUTES[user.role] || [];
    const roleLabel = ROLE_LABELS[user.role] || user.role;

    return (
        <>
            <div
                className={`sidebar-overlay ${isOpen ? 'active' : ''}`}
                onClick={onClose}
            />
            <aside className={`sidebar ${isOpen ? 'sidebar-open' : ''}`}>
                <div className="sidebar-brand">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <h2>CUDAS</h2>
                        <button className="sidebar-toggle" onClick={onClose} style={{ display: isOpen ? 'block' : 'none' }}>
                            <FiX />
                        </button>
                    </div>
                    <span>Education Platform</span>
                </div>

                <nav className="sidebar-nav">
                    <div className="sidebar-section-title">Main Menu</div>
                    {routes.map((route, idx) => (
                        <NavLink
                            key={idx}
                            to={route.path}
                            className={({ isActive }) =>
                                `sidebar-link ${isActive ? 'sidebar-link-active' : ''}`
                            }
                            onClick={onClose}
                            end={route.path === '/dashboard'}
                        >
                            <span className="sidebar-link-icon">
                                <route.icon />
                            </span>
                            {route.label}
                        </NavLink>
                    ))}
                </nav>

                <div className="sidebar-footer">
                    <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', textAlign: 'center' }}>
                        Logged in as:<br />
                        <strong>{roleLabel}</strong>
                    </div>
                </div>
            </aside>
        </>
    );
}
