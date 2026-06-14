import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { FiArchive, FiCheckCircle, FiPlus } from 'react-icons/fi';
import {
    approveQuestion,
    archiveQuestion,
    bulkApprove,
    bulkArchive,
    deleteQuestion,
    fetchQuestions,
    getApiErrorMessage,
    restoreQuestion,
} from '../../../../../../utils/aptitudeAdminApi';
import ConfirmDialog from './components/ConfirmDialog';
import QuestionFilters from './components/QuestionFilters';
import QuestionTable from './components/QuestionTable';
import { useAptitudeTaxonomy } from './hooks';
import '../../../../../../style/aptitudeAdmin.css';

const PAGE_SIZE = 20;
const EMPTY_FILTERS = {
    search: '',
    domain: '',
    category: '',
    subcategory: '',
    difficulty: '',
    status: '',
    source: '',
    tags: '',
};

export default function AptitudeQuestions() {
    const navigate = useNavigate();
    const { taxonomy } = useAptitudeTaxonomy();
    const [questions, setQuestions] = useState([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(0);
    const [filters, setFilters] = useState(EMPTY_FILTERS);
    const [selected, setSelected] = useState(new Set());
    const [sort, setSort] = useState({ key: 'created_at', direction: 'desc' });
    const [confirm, setConfirm] = useState(null);
    const [acting, setActing] = useState(false);

    const loadQuestions = useCallback(async () => {
        setLoading(true);
        try {
            const params = {
                limit: PAGE_SIZE,
                offset: page * PAGE_SIZE,
            };

            ['domain', 'category', 'subcategory', 'difficulty', 'status', 'source'].forEach((key) => {
                if (filters[key]) params[key] = filters[key];
            });
            if (filters.tags.trim()) params.tags = filters.tags.split(',').map((tag) => tag.trim()).filter(Boolean);
            if (filters.search.trim()) params.search = filters.search.trim();

            const data = await fetchQuestions(params);
            setQuestions(data.questions || []);
            setTotal(data.total || 0);
            setSelected(new Set());
        } catch (error) {
            toast.error(getApiErrorMessage(error, 'Failed to load questions'));
        } finally {
            setLoading(false);
        }
    }, [filters, page]);

    useEffect(() => {
        loadQuestions();
    }, [loadQuestions]);

    useEffect(() => {
        setPage(0);
    }, [filters]);

    const visibleQuestions = useMemo(() => {
        const query = filters.search.trim().toLowerCase();
        const searched = query
            ? questions.filter((item) => [item.question, item.category, item.subcategory, item.domain, ...(item.tags || [])].some((value) => String(value || '').toLowerCase().includes(query)))
            : questions;

        return [...searched].sort((a, b) => {
            const left = a[sort.key] || '';
            const right = b[sort.key] || '';
            const result = String(left).localeCompare(String(right), undefined, { numeric: true });
            return sort.direction === 'asc' ? result : -result;
        });
    }, [filters.search, questions, sort]);

    const openConfirm = (type, question = null) => {
        const messages = {
            approve: 'Approve this question and make it available for aptitude tests?',
            archive: 'Archive this question? It will be removed from active selection lists.',
            restore: 'Restore this question to draft status?',
            delete: 'Delete this question? This is a soft delete.',
            bulkApprove: `Approve ${selected.size} selected questions?`,
            bulkArchive: `Archive ${selected.size} selected questions?`,
        };
        setConfirm({ type, question, message: messages[type] });
    };

    const runAction = async () => {
        if (!confirm) return;
        setActing(true);
        try {
            if (confirm.type === 'approve') await approveQuestion(confirm.question.id);
            if (confirm.type === 'archive') await archiveQuestion(confirm.question.id);
            if (confirm.type === 'restore') await restoreQuestion(confirm.question.id);
            if (confirm.type === 'delete') await deleteQuestion(confirm.question.id);
            if (confirm.type === 'bulkApprove') await bulkApprove([...selected]);
            if (confirm.type === 'bulkArchive') await bulkArchive([...selected]);

            toast.success('Action completed');
            setConfirm(null);
            loadQuestions();
        } catch (error) {
            toast.error(getApiErrorMessage(error, 'Action failed'));
        } finally {
            setActing(false);
        }
    };

    const toggleSelect = (id) => {
        setSelected((prev) => {
            const next = new Set(prev);
            next.has(id) ? next.delete(id) : next.add(id);
            return next;
        });
    };

    const toggleSelectAll = () => {
        setSelected((prev) => (
            visibleQuestions.length > 0 && visibleQuestions.every((item) => prev.has(item.id))
                ? new Set()
                : new Set(visibleQuestions.map((item) => item.id))
        ));
    };

    const handleSort = (key) => {
        setSort((prev) => ({
            key,
            direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
        }));
    };

    return (
        <div className="apt-admin-page">
            <div className="apt-page-header apt-page-header-row">
                <div>
                    <h1 className="gradient-text">Question Management</h1>
                    <p>Search, review, approve, archive, and maintain the aptitude question bank.</p>
                </div>
                <button className="btn btn-primary apt-btn-sm" type="button" onClick={() => navigate('/admin/aptitude/questions/new')}>
                    <FiPlus /> Add Question
                </button>
            </div>

            <QuestionFilters
                filters={filters}
                taxonomy={taxonomy}
                onChange={setFilters}
                onReset={() => setFilters(EMPTY_FILTERS)}
            />

            {selected.size > 0 && (
                <div className="apt-bulk-bar">
                    <span>{selected.size} selected</span>
                    <button className="btn btn-secondary apt-btn-sm" type="button" onClick={() => openConfirm('bulkApprove')}><FiCheckCircle /> Approve Selected</button>
                    <button className="btn btn-secondary apt-btn-sm" type="button" onClick={() => openConfirm('bulkArchive')}><FiArchive /> Archive Selected</button>
                </div>
            )}

            <QuestionTable
                questions={visibleQuestions}
                total={total}
                page={page}
                pageSize={PAGE_SIZE}
                loading={loading}
                selected={selected}
                sort={sort}
                onSort={handleSort}
                onPageChange={setPage}
                onSelect={toggleSelect}
                onSelectAll={toggleSelectAll}
                onView={(id) => navigate(`/admin/aptitude/questions/${id}`)}
                onAction={openConfirm}
            />

            <ConfirmDialog
                open={!!confirm}
                message={confirm?.message}
                danger={confirm?.type === 'delete' || confirm?.type === 'archive' || confirm?.type === 'bulkArchive'}
                loading={acting}
                onCancel={() => setConfirm(null)}
                onConfirm={runAction}
            />
        </div>
    );
}
