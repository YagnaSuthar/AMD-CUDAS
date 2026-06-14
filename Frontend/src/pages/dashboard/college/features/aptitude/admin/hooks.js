import { useCallback, useEffect, useState } from 'react';
import { fetchCategories, fetchDomains, fetchSubcategories, fetchTaxonomyTree } from '../../../../../../utils/aptitudeAdminApi';

export function useAptitudeTaxonomy() {
    const [taxonomy, setTaxonomy] = useState({ domains: [], categories: [], subcategories: [], hierarchy: {} });
    const [loading, setLoading] = useState(true);

    const loadTaxonomy = useCallback(async () => {
        setLoading(true);
        try {
            const [domains, categories, subcategories, tree] = await Promise.allSettled([
                fetchDomains(),
                fetchCategories(),
                fetchSubcategories(),
                fetchTaxonomyTree(),
            ]);

            setTaxonomy({
                domains: domains.status === 'fulfilled' ? domains.value : [],
                categories: categories.status === 'fulfilled' ? categories.value : [],
                subcategories: subcategories.status === 'fulfilled' ? subcategories.value : [],
                hierarchy: tree.status === 'fulfilled' ? tree.value?.hierarchy || {} : {},
            });
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadTaxonomy();
    }, [loadTaxonomy]);

    return { taxonomy, loading, reloadTaxonomy: loadTaxonomy };
}
