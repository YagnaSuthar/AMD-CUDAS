import { useState, useEffect, useMemo } from 'react';
import { toast } from 'react-toastify';
import { FiChevronRight, FiFolder, FiFolderPlus, FiFile, FiSearch, FiLayers } from 'react-icons/fi';
import { fetchTaxonomyTree } from '../../../../../../utils/aptitudeAdminApi';
import SkeletonCard from '../../../../../../components/common/skeleton/SkeletonCard';
import '../../../../../../style/aptitudeAdmin.css';

export default function AptitudeTaxonomy() {
    const [tree, setTree] = useState({});
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [expanded, setExpanded] = useState(new Set());

    // Local management additions
    const [selectedNode, setSelectedNode] = useState(null);

    useEffect(() => {
        loadTaxonomy();
    }, []);

    const loadTaxonomy = async () => {
        setLoading(true);
        try {
            const data = await fetchTaxonomyTree();
            setTree(data.hierarchy || {});
            
            // Expand all domains initially
            const domains = Object.keys(data.hierarchy || {});
            setExpanded(new Set(domains));
        } catch {
            toast.error('Failed to load taxonomy hierarchy');
        } finally {
            setLoading(false);
        }
    };

    const toggleExpand = (path) => {
        setExpanded((prev) => {
            const next = new Set(prev);
            next.has(path) ? next.delete(path) : next.add(path);
            return next;
        });
    };

    // Filter tree client-side based on search term
    const filteredTree = useMemo(() => {
        if (!search) return tree;
        const q = search.toLowerCase();
        const res = {};

        Object.entries(tree).forEach(([domain, categories]) => {
            const matchedCategories = {};
            let hasDomainMatch = domain.toLowerCase().includes(q);

            Object.entries(categories).forEach(([category, subcategories]) => {
                const matchedSubcategories = subcategories.filter((sub) => sub.toLowerCase().includes(q));
                const hasCategoryMatch = category.toLowerCase().includes(q);

                if (hasCategoryMatch || matchedSubcategories.length > 0 || hasDomainMatch) {
                    matchedCategories[category] = subcategories;
                }
            });

            if (hasDomainMatch || Object.keys(matchedCategories).length > 0) {
                res[domain] = matchedCategories;
            }
        });

        return res;
    }, [tree, search]);

    if (loading) {
        return (
            <div className="apt-admin-page">
                <div className="apt-page-header"><h1 className="gradient-text">Loading Taxonomy...</h1></div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '20px' }}>
                    <SkeletonCard style={{ height: '400px' }} />
                    <SkeletonCard style={{ height: '400px' }} />
                </div>
            </div>
        );
    }

    return (
        <div className="apt-admin-page">
            <div className="apt-page-header">
                <h1 className="gradient-text">Taxonomy Management</h1>
                <p>Manage categories, domains, and subcategories tree hierarchy.</p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', alignItems: 'start' }}>
                {/* Left Side: Tree */}
                <div>
                    {/* Search and header */}
                    <div className="apt-toolbar" style={{ marginBottom: '16px' }}>
                        <div className="apt-search-box" style={{ maxWidth: '100%' }}>
                            <FiSearch />
                            <input
                                placeholder="Search taxonomy tree..."
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                            />
                        </div>
                    </div>

                    <div className="apt-tree">
                        {Object.keys(filteredTree).length === 0 ? (
                            <div className="apt-empty-state" style={{ padding: '30px' }}>
                                <FiLayers />
                                <h3>No matching hierarchy</h3>
                                <p>Try clearing your search filters.</p>
                            </div>
                        ) : (
                            Object.entries(filteredTree).map(([domain, categories]) => {
                                const isDomExpanded = expanded.has(domain);
                                return (
                                    <div key={domain} className="apt-tree-node">
                                        <button
                                            className="apt-tree-toggle"
                                            onClick={() => toggleExpand(domain)}
                                        >
                                            <FiChevronRight className={isDomExpanded ? 'expanded' : ''} />
                                            <FiFolder style={{ color: 'var(--color-secondary)' }} />
                                            <span>{domain.toUpperCase().replace('_', ' ')}</span>
                                        </button>

                                        {isDomExpanded && (
                                            <div className="apt-tree-children">
                                                {Object.entries(categories).map(([category, subcategories]) => {
                                                    const catPath = `${domain}/${category}`;
                                                    const isCatExpanded = expanded.has(catPath);
                                                    return (
                                                        <div key={category} className="apt-tree-node">
                                                            <button
                                                                className="apt-tree-toggle"
                                                                onClick={() => toggleExpand(catPath)}
                                                                style={{ paddingLeft: '8px' }}
                                                            >
                                                                <FiChevronRight className={isCatExpanded ? 'expanded' : ''} />
                                                                <FiFolderPlus style={{ color: 'var(--color-accent)' }} />
                                                                <span style={{ fontWeight: 500 }}>{category}</span>
                                                            </button>

                                                            {isCatExpanded && (
                                                                <div className="apt-tree-children" style={{ marginLeft: '12px', paddingLeft: '16px' }}>
                                                                    {subcategories.length === 0 ? (
                                                                        <div className="apt-tree-leaf" style={{ fontStyle: 'italic', opacity: 0.5 }}>
                                                                            No subcategories
                                                                        </div>
                                                                    ) : (
                                                                        subcategories.map((sub) => (
                                                                            <div
                                                                                key={sub}
                                                                                className="apt-tree-leaf"
                                                                                style={{ display: 'flex', gap: '8px', alignItems: 'center', cursor: 'pointer' }}
                                                                                onClick={() => setSelectedNode({ domain, category, subcategory: sub })}
                                                                            >
                                                                                <FiFile style={{ color: 'var(--color-text-muted)', flexShrink: 0 }} />
                                                                                <span>{sub}</span>
                                                                            </div>
                                                                        ))
                                                                    )}
                                                                </div>
                                                            )}
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        )}
                                    </div>
                                );
                            })
                        )}
                    </div>
                </div>

                {/* Right Side: Details / Actions */}
                <div className="apt-form-card" style={{ padding: '24px' }}>
                    <h3 style={{ fontSize: '1rem', fontWeight: 700, borderBottom: '1px solid var(--color-border)', paddingBottom: '12px', marginBottom: '16px' }}>
                        Node Settings & Properties
                    </h3>

                    {selectedNode ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                            <div className="apt-form-group">
                                <label>Domain</label>
                                <input value={selectedNode.domain} disabled />
                            </div>
                            <div className="apt-form-group">
                                <label>Category</label>
                                <input value={selectedNode.category} disabled />
                            </div>
                            <div className="apt-form-group">
                                <label>Subcategory</label>
                                <input value={selectedNode.subcategory} disabled />
                            </div>
                            <div style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)', display: 'flex', gap: '6px', alignItems: 'center' }}>
                                <FiLayers />
                                <span>Note: Taxonomy is dynamically mapped based on questions present in your database. Adding or updating question taxonomy automatically populates this tree structure.</span>
                            </div>
                        </div>
                    ) : (
                        <div className="apt-empty-state" style={{ padding: '40px' }}>
                            <FiLayers />
                            <h3>Select Node</h3>
                            <p>Click on any subcategory leaf node in the tree to view properties.</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
