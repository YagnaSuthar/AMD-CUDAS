import { memo } from 'react';
import { FiArchive, FiCheckCircle, FiChevronDown, FiChevronLeft, FiChevronRight, FiEdit2, FiEye, FiRotateCcw, FiTrash2, FiInbox } from 'react-icons/fi';
import SkeletonTableRow from '../../../../../../../components/common/skeleton/SkeletonTableRow';
import StatusBadge from './StatusBadge';

function QuestionTable({
    questions,
    total,
    page,
    pageSize,
    loading,
    selected,
    sort,
    onSort,
    onPageChange,
    onSelect,
    onSelectAll,
    onView,
    onAction,
}) {
    const totalPages = Math.max(1, Math.ceil(total / pageSize));
    const allSelected = questions.length > 0 && questions.every((item) => selected.has(item.id));

    const sortIcon = (key) => sort.key === key ? <FiChevronDown className={sort.direction === 'asc' ? 'apt-sort-asc' : ''} /> : null;
    const formatDate = (value) => value ? new Date(value).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '-';

    return (
        <div className="apt-table-wrap">
            <div className="apt-table-header">
                <h3>Questions <span className="table-count">{total}</span></h3>
            </div>
            <div className="apt-table-scroll">
                <table className="apt-table">
                    <thead>
                        <tr>
                            <th className="checkbox-cell">
                                <input type="checkbox" checked={allSelected} onChange={onSelectAll} />
                            </th>
                            {[
                                ['question', 'Question'],
                                ['domain', 'Domain'],
                                ['category', 'Category'],
                                ['difficulty', 'Difficulty'],
                                ['status', 'Status'],
                                ['source', 'Source'],
                                ['created_at', 'Created Date'],
                            ].map(([key, label]) => (
                                <th key={key} className="sortable" onClick={() => onSort(key)}>
                                    <span className="apt-th-content">{label}{sortIcon(key)}</span>
                                </th>
                            ))}
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {loading ? (
                            Array.from({ length: 8 }).map((_, index) => <SkeletonTableRow key={index} columns={9} />)
                        ) : questions.length === 0 ? (
                            <tr>
                                <td colSpan="9">
                                    <div className="apt-empty-state">
                                        <FiInbox />
                                        <h3>No Questions Found</h3>
                                        <p>Change the filters or add a new question to start building the bank.</p>
                                    </div>
                                </td>
                            </tr>
                        ) : (
                            questions.map((question) => (
                                <tr key={question.id}>
                                    <td className="checkbox-cell">
                                        <input type="checkbox" checked={selected.has(question.id)} onChange={() => onSelect(question.id)} />
                                    </td>
                                    <td className="question-cell" title={question.question}>{question.question}</td>
                                    <td>{question.domain || '-'}</td>
                                    <td>{question.category || '-'}</td>
                                    <td><StatusBadge value={question.difficulty} /></td>
                                    <td><StatusBadge value={question.is_deleted ? 'deleted' : question.status} /></td>
                                    <td>{question.source || '-'}</td>
                                    <td className="apt-nowrap">{formatDate(question.created_at)}</td>
                                    <td>
                                        <div className="td-actions">
                                            <button className="apt-action-btn" type="button" title="View" onClick={() => onView(question.id)}><FiEye /></button>
                                            <button className="apt-action-btn" type="button" title="Edit" onClick={() => onView(question.id)}><FiEdit2 /></button>
                                            {question.status !== 'approved' && <button className="apt-action-btn success" type="button" title="Approve" onClick={() => onAction('approve', question)}><FiCheckCircle /></button>}
                                            {question.status !== 'archived' && <button className="apt-action-btn" type="button" title="Archive" onClick={() => onAction('archive', question)}><FiArchive /></button>}
                                            {(question.status === 'archived' || question.is_deleted) && <button className="apt-action-btn" type="button" title="Restore" onClick={() => onAction('restore', question)}><FiRotateCcw /></button>}
                                            <button className="apt-action-btn danger" type="button" title="Delete" onClick={() => onAction('delete', question)}><FiTrash2 /></button>
                                        </div>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
            {!loading && total > 0 && (
                <div className="apt-pagination">
                    <span>Showing {(page * pageSize) + 1}-{Math.min((page + 1) * pageSize, total)} of {total}</span>
                    <div className="apt-pagination-btns">
                        <button disabled={page === 0} onClick={() => onPageChange(page - 1)}><FiChevronLeft /> Prev</button>
                        <button disabled={page + 1 >= totalPages} onClick={() => onPageChange(page + 1)}>Next <FiChevronRight /></button>
                    </div>
                </div>
            )}
        </div>
    );
}

export default memo(QuestionTable);
