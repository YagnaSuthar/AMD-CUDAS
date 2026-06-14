import { FiRefreshCw, FiSearch } from 'react-icons/fi';

const DIFFICULTIES = ['easy', 'medium', 'hard'];
const STATUSES = ['draft', 'approved', 'archived'];
const SOURCES = ['curated', 'admin', 'imported', 'generated'];

export default function QuestionFilters({ filters, taxonomy, onChange, onReset }) {
    const domains = taxonomy.domains?.length ? taxonomy.domains : ['quantitative', 'logical_reasoning', 'verbal_ability', 'data_interpretation'];

    const setFilter = (key, value) => onChange({ ...filters, [key]: value });

    return (
        <div className="apt-panel apt-filters">
            <div className="apt-search-box">
                <FiSearch />
                <input
                    value={filters.search}
                    onChange={(event) => setFilter('search', event.target.value)}
                    placeholder="Search questions"
                />
            </div>

            <select className="apt-filter-select" value={filters.domain} onChange={(event) => setFilter('domain', event.target.value)}>
                <option value="">All Domains</option>
                {domains.map((item) => <option key={item} value={item}>{item.replaceAll('_', ' ')}</option>)}
            </select>

            <select className="apt-filter-select" value={filters.category} onChange={(event) => setFilter('category', event.target.value)}>
                <option value="">All Categories</option>
                {taxonomy.categories.map((item) => <option key={item} value={item}>{item.replaceAll('_', ' ')}</option>)}
            </select>

            <select className="apt-filter-select" value={filters.subcategory} onChange={(event) => setFilter('subcategory', event.target.value)}>
                <option value="">All Subcategories</option>
                {taxonomy.subcategories.map((item) => <option key={item} value={item}>{item.replaceAll('_', ' ')}</option>)}
            </select>

            <select className="apt-filter-select" value={filters.difficulty} onChange={(event) => setFilter('difficulty', event.target.value)}>
                <option value="">All Difficulties</option>
                {DIFFICULTIES.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>

            <select className="apt-filter-select" value={filters.status} onChange={(event) => setFilter('status', event.target.value)}>
                <option value="">All Statuses</option>
                {STATUSES.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>

            <select className="apt-filter-select" value={filters.source} onChange={(event) => setFilter('source', event.target.value)}>
                <option value="">All Sources</option>
                {SOURCES.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>

            <input
                className="apt-filter-input"
                value={filters.tags}
                onChange={(event) => setFilter('tags', event.target.value)}
                placeholder="Tags"
            />

            <button className="apt-action-btn" type="button" onClick={onReset} title="Reset filters">
                <FiRefreshCw />
            </button>
        </div>
    );
}
