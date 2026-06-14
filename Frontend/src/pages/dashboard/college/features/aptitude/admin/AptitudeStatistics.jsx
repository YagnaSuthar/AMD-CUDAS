import { useEffect, useMemo, useState } from 'react';
import { toast } from 'react-toastify';
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { fetchImportJobs, fetchQuestions, fetchStatistics, getApiErrorMessage } from '../../../../../../utils/aptitudeAdminApi';
import StatisticsCards from './components/StatisticsCards';
import StatusBadge from './components/StatusBadge';
import '../../../../../../style/aptitudeAdmin.css';

const COLORS = ['#00bcd4', '#22c55e', '#f59e0b', '#ef4444', '#4dd0e1', '#94a3b8'];

function groupCount(items, key) {
    return items.reduce((acc, item) => {
        const label = item[key] || 'unknown';
        acc[label] = (acc[label] || 0) + 1;
        return acc;
    }, {});
}

function toChartData(grouped) {
    return Object.entries(grouped).map(([name, value]) => ({ name: name.replaceAll('_', ' '), value }));
}

export default function AptitudeStatistics() {
    const [questions, setQuestions] = useState([]);
    const [recentImports, setRecentImports] = useState([]);
    const [remoteStats, setRemoteStats] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let alive = true;
        async function load() {
            setLoading(true);
            try {
                const [statsResult, questionResult, importResult] = await Promise.allSettled([
                    fetchStatistics(),
                    fetchQuestions({ limit: 100, offset: 0, include_deleted: true }),
                    fetchImportJobs({ limit: 5 }),
                ]);

                if (!alive) return;
                if (statsResult.status === 'fulfilled') setRemoteStats(statsResult.value);
                if (questionResult.status === 'fulfilled') setQuestions(questionResult.value.questions || []);
                if (importResult.status === 'fulfilled') setRecentImports(importResult.value.jobs || importResult.value.imports || importResult.value || []);
                if (questionResult.status === 'rejected') toast.error(getApiErrorMessage(questionResult.reason, 'Failed to load statistics'));
            } finally {
                if (alive) setLoading(false);
            }
        }
        load();
        return () => { alive = false; };
    }, []);

    const stats = useMemo(() => {
        if (remoteStats?.totals) {
            return {
                totalQuestions: remoteStats.totals.total_questions,
                approved: remoteStats.totals.approved,
                draft: remoteStats.totals.draft,
                archived: remoteStats.totals.archived,
            };
        }
        return {
            totalQuestions: questions.length,
            approved: questions.filter((item) => item.status === 'approved').length,
            draft: questions.filter((item) => item.status === 'draft').length,
            archived: questions.filter((item) => item.status === 'archived').length,
        };
    }, [questions, remoteStats]);

    const byDomain = toChartData(remoteStats?.by_domain || groupCount(questions, 'domain'));
    const byDifficulty = toChartData(remoteStats?.by_difficulty || groupCount(questions, 'difficulty'));
    const bySource = toChartData(remoteStats?.by_source || groupCount(questions, 'source'));

    const tooltipStyle = {
        background: 'var(--color-bg-card)',
        border: '1px solid var(--color-border)',
        borderRadius: '8px',
        color: 'var(--color-text-primary)',
    };

    if (loading) {
        return (
            <div className="apt-admin-page">
                <div className="apt-page-header"><h1 className="gradient-text">Statistics Dashboard</h1></div>
                <div className="apt-stats-row">{Array.from({ length: 4 }).map((_, index) => <div className="apt-stat-card apt-skeleton-block" key={index} />)}</div>
                <div className="apt-charts-row"><div className="apt-chart-card apt-skeleton-block" /><div className="apt-chart-card apt-skeleton-block" /></div>
            </div>
        );
    }

    return (
        <div className="apt-admin-page">
            <div className="apt-page-header">
                <h1 className="gradient-text">Statistics Dashboard</h1>
                <p>Monitor aptitude question coverage, approval mix, source distribution, and recent import activity.</p>
            </div>

            <StatisticsCards stats={stats} />

            <div className="apt-charts-row">
                <div className="apt-chart-card">
                    <h3>By Domain</h3>
                    <ResponsiveContainer width="100%" height={280}>
                        <BarChart data={byDomain} margin={{ top: 10, right: 10, left: 0, bottom: 40 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                            <XAxis dataKey="name" stroke="var(--color-text-muted)" fontSize={11} angle={-20} textAnchor="end" height={60} />
                            <YAxis stroke="var(--color-text-muted)" fontSize={11} />
                            <Tooltip contentStyle={tooltipStyle} />
                            <Bar dataKey="value" radius={[6, 6, 0, 0]}>{byDomain.map((_, index) => <Cell key={index} fill={COLORS[index % COLORS.length]} />)}</Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>

                <div className="apt-chart-card">
                    <h3>By Difficulty</h3>
                    <ResponsiveContainer width="100%" height={280}>
                        <PieChart>
                            <Pie data={byDifficulty} dataKey="value" nameKey="name" outerRadius={96} label>
                                {byDifficulty.map((_, index) => <Cell key={index} fill={COLORS[index % COLORS.length]} />)}
                            </Pie>
                            <Tooltip contentStyle={tooltipStyle} />
                        </PieChart>
                    </ResponsiveContainer>
                </div>

                <div className="apt-chart-card">
                    <h3>By Source</h3>
                    <ResponsiveContainer width="100%" height={280}>
                        <BarChart data={bySource} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                            <XAxis dataKey="name" stroke="var(--color-text-muted)" fontSize={11} />
                            <YAxis stroke="var(--color-text-muted)" fontSize={11} />
                            <Tooltip contentStyle={tooltipStyle} />
                            <Bar dataKey="value" fill="var(--color-secondary)" radius={[6, 6, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>

                <div className="apt-chart-card">
                    <h3>Recent Imports</h3>
                    <div className="apt-mini-list">
                        {recentImports.length ? recentImports.map((job) => (
                            <div className="apt-mini-list-item" key={job.id}>
                                <span>{job.filename}</span>
                                <StatusBadge value={job.status} />
                            </div>
                        )) : <div className="apt-empty-state compact"><h3>No recent imports</h3><p>Completed upload jobs will appear here.</p></div>}
                    </div>
                </div>
            </div>
        </div>
    );
}
