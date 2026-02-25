import { FiMenu, FiLogOut, FiUser } from 'react-icons/fi';
import { useAuth } from '../context/AuthContext';
import { ROLE_LABELS } from '../utils/roles';
import { useNavigate } from 'react-router-dom';

export default function Header({ onMenuClick }) {
    const { user, logout } = useAuth();
    const navigate = useNavigate();

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    const roleLabel = user ? (ROLE_LABELS[user.role] || user.role) : '';

    return (
        <header className="header">
            <div className="header-left">
                <button className="sidebar-toggle" onClick={onMenuClick}>
                    <FiMenu />
                </button>
                <h1 className="header-title gradient-text">Dashboard</h1>
            </div>

            <div className="header-right">
                {user && (
                    <div className="header-user-info">
                        <span className="header-role-badge">{roleLabel}</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginLeft: '8px' }}>
                            <FiUser style={{ color: 'var(--color-text-muted)' }} />
                            <span className="header-user-name">{user.name}</span>
                        </div>
                    </div>
                )}
                <button className="header-logout-btn" onClick={handleLogout} title="Logout">
                    <FiLogOut />
                    <span className="logout-text">Logout</span>
                </button>
            </div>
        </header>
    );
}
