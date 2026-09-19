import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { FiSun, FiMoon } from 'react-icons/fi';

export function useNeoTheme() {
    const [theme, setTheme] = useState(localStorage.getItem('theme') || 'light');

    useEffect(() => {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    }, [theme]);

    return [theme, () => setTheme(prev => (prev === 'light' ? 'dark' : 'light'))];
}

export function BrandMark({ size = 'md' }) {
    return (
        <Link to="/" className={`neo-brand neo-brand-${size}`}>
            <span className="neo-brand-logo">
                <img src="/cudas-logo.png" alt="CUDAS logo" />
            </span>
            <span className="neo-brand-name">CUDAS</span>
        </Link>
    );
}

export default function AuthNavbar({ rightContent = null, links = null }) {
    const [theme, toggleTheme] = useNeoTheme();
    const [scrolled, setScrolled] = useState(false);

    useEffect(() => {
        const onScroll = () => setScrolled(window.scrollY > 12);
        onScroll();
        window.addEventListener('scroll', onScroll, { passive: true });
        return () => window.removeEventListener('scroll', onScroll);
    }, []);

    return (
        <nav className={`neo-nav ${scrolled ? 'is-scrolled' : ''}`}>
            <div className="neo-nav-inner">
                <BrandMark />
                {links && <div className="neo-nav-links">{links}</div>}
                <div className="neo-nav-actions">
                    {rightContent}
                    <button
                        type="button"
                        onClick={toggleTheme}
                        className="neo-icon-btn"
                        aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
                    >
                        {theme === 'light' ? <FiMoon size={18} /> : <FiSun size={18} />}
                    </button>
                </div>
            </div>
        </nav>
    );
}
