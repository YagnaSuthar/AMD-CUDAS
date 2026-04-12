<<<<<<< HEAD
import { FiMenu, FiLogOut, FiUser } from 'react-icons/fi';
=======
import { useState, useRef, useEffect } from 'react';
import { FiMenu, FiLogOut, FiUser, FiGlobe, FiChevronDown, FiCheck } from 'react-icons/fi';
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
import { useAuth } from '../context/AuthContext';
import { ROLE_LABELS } from '../utils/roles';
import { useNavigate } from 'react-router-dom';
import ThemeToggle from './ThemeToggle';

<<<<<<< HEAD
export default function Header({ onMenuClick }) {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
=======
const LANGUAGES = [
    { code: 'en', label: 'English', native: 'English', flag: '🇬🇧' },
    { code: 'hi', label: 'Hindi', native: 'हिन्दी', flag: '🇮🇳' },
    { code: 'gu', label: 'Gujarati', native: 'ગુજરાતી', flag: '🇮🇳' },
];

/**
 * Robustly trigger Google Translate.
 * Strategy 1: Use the hidden .goog-te-combo <select> element (instant, no reload)
 * Strategy 2: Set the googtrans cookie and reload
 */
function triggerGoogleTranslate(langCode) {
    // Strategy 1 — try the combo-box (works if the widget has loaded)
    const tryCombo = () => {
        const select = document.querySelector('.goog-te-combo');
        if (select) {
            select.value = langCode;
            select.dispatchEvent(new Event('change'));
            return true;
        }
        return false;
    };

    if (tryCombo()) return;

    // Strategy 2 — cookie-based redirect (reliable fallback)
    // Google Translate reads the googtrans cookie format: /sourceLang/targetLang
    const cookieValue = langCode === 'en' ? '' : `/en/${langCode}`;
    const hostname = window.location.hostname;

    // Clear existing cookie first
    document.cookie = `googtrans=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
    document.cookie = `googtrans=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; domain=${hostname};`;
    document.cookie = `googtrans=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; domain=.${hostname};`;

    if (cookieValue) {
        document.cookie = `googtrans=${cookieValue}; path=/;`;
        document.cookie = `googtrans=${cookieValue}; path=/; domain=${hostname};`;
        document.cookie = `googtrans=${cookieValue}; path=/; domain=.${hostname};`;
    }

    // If combo didn't work, wait briefly and retry, then reload as last resort
    setTimeout(() => {
        if (!tryCombo()) {
            window.location.reload();
        }
    }, 300);
}

/** Read the current Google Translate language from the cookie */
function getGoogleTranslateLang() {
    const match = document.cookie.match(/googtrans=\/en\/(\w+)/);
    return match ? match[1] : 'en';
}

export default function Header({ onMenuClick }) {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [langOpen, setLangOpen] = useState(false);
    const [selectedLang, setSelectedLang] = useState(() => getGoogleTranslateLang());
    const dropdownRef = useRef(null);
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

<<<<<<< HEAD
=======
    // Close dropdown on outside click
    useEffect(() => {
        const handler = (e) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
                setLangOpen(false);
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, []);

    const handleLanguageChange = (langCode) => {
        setSelectedLang(langCode);
        setLangOpen(false);
        triggerGoogleTranslate(langCode);
    };

    const currentLang = LANGUAGES.find(l => l.code === selectedLang) || LANGUAGES[0];
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
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
<<<<<<< HEAD
=======
                {/* Premium Language Selector */}
                <div className="lang-selector" ref={dropdownRef}>
                    <button
                        className={`lang-trigger ${langOpen ? 'lang-trigger-active' : ''}`}
                        onClick={() => setLangOpen(!langOpen)}
                        aria-label="Select language"
                        id="language-selector-btn"
                    >
                        <FiGlobe className="lang-trigger-icon" />
                        <span className="lang-trigger-label">{currentLang.flag} {currentLang.native}</span>
                        <FiChevronDown className={`lang-trigger-arrow ${langOpen ? 'lang-arrow-up' : ''}`} />
                    </button>

                    {langOpen && (
                        <div className="lang-dropdown">
                            <div className="lang-dropdown-header">
                                <FiGlobe size={14} />
                                <span>Select Language</span>
                            </div>
                            {LANGUAGES.map((lang) => (
                                <button
                                    key={lang.code}
                                    className={`lang-option ${selectedLang === lang.code ? 'lang-option-active' : ''}`}
                                    onClick={() => handleLanguageChange(lang.code)}
                                    id={`lang-option-${lang.code}`}
                                >
                                    <span className="lang-option-flag">{lang.flag}</span>
                                    <div className="lang-option-text">
                                        <span className="lang-option-label">{lang.label}</span>
                                        <span className="lang-option-native">{lang.native}</span>
                                    </div>
                                    {selectedLang === lang.code && (
                                        <FiCheck className="lang-option-check" />
                                    )}
                                </button>
                            ))}
                        </div>
                    )}
                </div>

>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
                {user && (
                    <div className="header-user-info">
                        <span className="header-role-badge">{roleLabel}</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginLeft: '8px' }}>
                            <FiUser style={{ color: 'var(--color-text-muted)' }} />
                            <span className="header-user-name">{user.name}</span>
                        </div>
                    </div>
                )}
                <ThemeToggle />
                <button className="header-logout-btn" onClick={handleLogout} title="Logout">
                    <FiLogOut />
                    <span className="logout-text">Logout</span>
                </button>
            </div>
        </header>
    );
}
