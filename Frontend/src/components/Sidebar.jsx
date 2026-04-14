import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { SIDEBAR_ROUTES, ROLE_LABELS } from '../utils/roles';
import { FiX } from 'react-icons/fi';
import { useState, useEffect } from 'react';
import api from '../utils/api';

// Dynamically imporing local background images
import bgImage1 from '../assets/BG-1.jpg';
// Other backgrounds like BG-2, BG-3 can be imported if you want to make it swappable

export default function Sidebar({ isOpen, onClose }) {
    const { user } = useAuth();
    const [unreadCount, setUnreadCount] = useState(0);

    const fetchUnreadCount = async () => {
        if (!user) return;
        // Students see badge on notifications, college roles see badge on messages
        const isCollegeRole = ['COLLEGE_PRINCIPAL', 'HOD', 'FACULTY'].includes(user?.role);
        const isStudent = user?.role === 'STUDENT';
        if (!isStudent && !isCollegeRole) return;
        try {
            const res = await api.get('/messages/notifications');
            setUnreadCount(res.data.unread_count || 0);
        } catch (err) {
            console.error('Failed to fetch unread count', err);
        }
    };

    useEffect(() => {
        fetchUnreadCount();
    }, [user]);

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
                {/* Background Layering */}
                <div 
                    className="sidebar-bg-image" 
                    style={{ backgroundImage: `url(${bgImage1})` }}
                ></div>
                <div className="sidebar-bg-overlay"></div>

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
                            {/* Student notification badge */}
                            {user.role === 'STUDENT' && route.path === '/dashboard/notifications' && unreadCount > 0 && (
                                <span className="sidebar-badge">
                                    {unreadCount}
                                </span>
                            )}
                            {/* College role messages badge */}
                            {['COLLEGE_PRINCIPAL', 'HOD', 'FACULTY'].includes(user.role) && route.path === '/dashboard/college-messages' && unreadCount > 0 && (
                                <span className="sidebar-badge">
                                    {unreadCount}
                                </span>
                            )}
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
