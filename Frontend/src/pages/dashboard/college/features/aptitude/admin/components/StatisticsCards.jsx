import { FiArchive, FiCheckCircle, FiDatabase, FiEdit3 } from 'react-icons/fi';

export default function StatisticsCards({ stats }) {
    const cards = [
        { label: 'Total Questions', value: stats.totalQuestions, icon: FiDatabase, tone: 'blue' },
        { label: 'Approved', value: stats.approved, icon: FiCheckCircle, tone: 'green' },
        { label: 'Draft', value: stats.draft, icon: FiEdit3, tone: 'yellow' },
        { label: 'Archived', value: stats.archived, icon: FiArchive, tone: 'red' },
    ];

    return (
        <div className="apt-stats-row">
            {cards.map(({ label, value, icon: Icon, tone }) => (
                <div className="apt-stat-card" key={label}>
                    <span className={`stat-icon ${tone}`}><Icon /></span>
                    <span className="stat-label">{label}</span>
                    <span className="stat-value">{value || 0}</span>
                </div>
            ))}
        </div>
    );
}
