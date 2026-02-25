export default function AnimatedBackground() {
    return (
        <div className="animated-bg">
            <div className="blob blob-1"></div>
            <div className="blob blob-2"></div>
            <div className="blob blob-3"></div>
            <div className="blob blob-4"></div>

            {Array.from({ length: 15 }).map((_, i) => (
                <div
                    key={i}
                    className="particle"
                    style={{
                        left: `${Math.random() * 100}%`,
                        animationDelay: `${Math.random() * -15}s`,
                        opacity: Math.random() * 0.5 + 0.1,
                    }}
                />
            ))}
        </div>
    );
}
