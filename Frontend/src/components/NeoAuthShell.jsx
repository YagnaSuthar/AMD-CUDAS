import AuthNavbar from './AuthNavbar';
import { FiCheck } from 'react-icons/fi';

/**
 * Split-screen neumorphic layout shared by Login and Register.
 * Left: brand showcase. Right: the form card (children).
 */
export default function NeoAuthShell({ eyebrow, title, subtitle, points = [], children, wide = false }) {
    return (
        <div className="neo-auth">
            <AuthNavbar />

            <div className={`neo-auth-grid ${wide ? 'is-wide' : ''}`}>
                <aside className="neo-auth-showcase fade-in-up">
                    <div className="neo-orb neo-orb-sm">
                        <div className="neo-orb-ring" />
                        <div className="neo-orb-core">
                            <img src="/cudas-logo.png" alt="" />
                        </div>
                    </div>

                    <span className="neo-eyebrow">{eyebrow}</span>
                    <h2 className="neo-showcase-title">{title}</h2>
                    <p className="neo-showcase-sub">{subtitle}</p>

                    <ul className="neo-checklist">
                        {points.map((p) => (
                            <li key={p}>
                                <span className="neo-check"><FiCheck /></span>
                                {p}
                            </li>
                        ))}
                    </ul>
                </aside>

                <main className="neo-auth-card fade-in-up fade-in-delay-1">
                    {children}
                </main>
            </div>
        </div>
    );
}
