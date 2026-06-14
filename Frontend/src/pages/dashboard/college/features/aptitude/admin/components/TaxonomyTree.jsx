import { useMemo, useState } from 'react';
import { FiChevronRight, FiEdit2, FiPlus, FiRotateCcw, FiSlash } from 'react-icons/fi';

export default function TaxonomyTree({ hierarchy, search, onAction }) {
    const [expanded, setExpanded] = useState(new Set());

    const domains = useMemo(() => {
        const query = search.trim().toLowerCase();
        return Object.entries(hierarchy || {})
            .map(([domain, categories]) => ({
                domain,
                categories: Object.entries(categories || {})
                    .map(([category, subcategories]) => ({
                        category,
                        subcategories: subcategories || [],
                    }))
                    .filter((item) => {
                        if (!query) return true;
                        return item.category.includes(query) || item.subcategories.some((sub) => sub.includes(query)) || domain.includes(query);
                    }),
            }))
            .filter((item) => item.categories.length > 0 || item.domain.includes(query));
    }, [hierarchy, search]);

    const toggle = (key) => {
        setExpanded((prev) => {
            const next = new Set(prev);
            next.has(key) ? next.delete(key) : next.add(key);
            return next;
        });
    };

    const actionButtons = (type, payload) => (
        <span className="apt-tree-actions">
            <button type="button" title="Add" onClick={(event) => { event.stopPropagation(); onAction('add', type, payload); }}><FiPlus /></button>
            <button type="button" title="Edit" onClick={(event) => { event.stopPropagation(); onAction('edit', type, payload); }}><FiEdit2 /></button>
            <button type="button" title="Disable" onClick={(event) => { event.stopPropagation(); onAction('disable', type, payload); }}><FiSlash /></button>
            <button type="button" title="Restore" onClick={(event) => { event.stopPropagation(); onAction('restore', type, payload); }}><FiRotateCcw /></button>
        </span>
    );

    if (!domains.length) {
        return (
            <div className="apt-tree">
                <div className="apt-empty-state compact">
                    <h3>No taxonomy found</h3>
                    <p>Create questions with domains and categories to populate the tree.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="apt-tree">
            {domains.map(({ domain, categories }) => {
                const domainKey = `domain:${domain}`;
                const domainOpen = expanded.has(domainKey);
                return (
                    <div className="apt-tree-node" key={domain}>
                        <button className="apt-tree-toggle" type="button" onClick={() => toggle(domainKey)}>
                            <FiChevronRight className={domainOpen ? 'expanded' : ''} />
                            <span>{domain.replaceAll('_', ' ')}</span>
                            {actionButtons('domain', { domain })}
                        </button>
                        {domainOpen && (
                            <div className="apt-tree-children">
                                {categories.map(({ category, subcategories }) => {
                                    const categoryKey = `${domainKey}:category:${category}`;
                                    const categoryOpen = expanded.has(categoryKey);
                                    return (
                                        <div className="apt-tree-node" key={category}>
                                            <button className="apt-tree-toggle" type="button" onClick={() => toggle(categoryKey)}>
                                                <FiChevronRight className={categoryOpen ? 'expanded' : ''} />
                                                <span>{category.replaceAll('_', ' ')}</span>
                                                {actionButtons('category', { domain, category })}
                                            </button>
                                            {categoryOpen && (
                                                <div className="apt-tree-children">
                                                    {subcategories.length ? subcategories.map((subcategory) => (
                                                        <div className="apt-tree-leaf" key={subcategory}>
                                                            <span>{subcategory.replaceAll('_', ' ')}</span>
                                                            {actionButtons('subcategory', { domain, category, subcategory })}
                                                        </div>
                                                    )) : <div className="apt-tree-leaf apt-muted">No subcategories</div>}
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
    );
}
