import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { toast } from 'react-toastify';
import { FiArchive, FiCheckCircle, FiRotateCcw } from 'react-icons/fi';
import SkeletonCard from '../../../../../../components/common/skeleton/SkeletonCard';
import {
    approveQuestion,
    archiveQuestion,
    createQuestion,
    fetchQuestion,
    getApiErrorMessage,
    getValidationErrors,
    restoreQuestion,
    updateQuestion,
} from '../../../../../../utils/aptitudeAdminApi';
import ConfirmDialog from './components/ConfirmDialog';
import QuestionForm, {
    buildQuestionPayload,
    EMPTY_QUESTION_FORM,
    normalizeQuestionToForm,
    validateQuestionForm,
} from './components/QuestionForm';
import StatusBadge from './components/StatusBadge';
import '../../../../../../style/aptitudeAdmin.css';

export default function AptitudeQuestionForm() {
    const { id } = useParams();
    const navigate = useNavigate();
    const isEdit = Boolean(id);
    const [form, setForm] = useState(EMPTY_QUESTION_FORM);
    const [tags, setTags] = useState([]);
    const [errors, setErrors] = useState({});
    const [loading, setLoading] = useState(isEdit);
    const [saving, setSaving] = useState(false);
    const [dirty, setDirty] = useState(false);
    const [confirm, setConfirm] = useState(null);

    const loadQuestion = useCallback(async () => {
        setLoading(true);
        try {
            const question = await fetchQuestion(id);
            setForm(normalizeQuestionToForm(question));
            setTags(question.tags || []);
            setDirty(false);
        } catch (error) {
            toast.error(getApiErrorMessage(error, 'Failed to load question'));
            navigate('/admin/aptitude/questions');
        } finally {
            setLoading(false);
        }
    }, [id, navigate]);

    useEffect(() => {
        if (isEdit) loadQuestion();
    }, [isEdit, loadQuestion]);

    useEffect(() => {
        const handler = (event) => {
            if (dirty) {
                event.preventDefault();
                event.returnValue = '';
            }
        };
        window.addEventListener('beforeunload', handler);
        return () => window.removeEventListener('beforeunload', handler);
    }, [dirty]);

    const changeForm = (next) => {
        setForm(next);
        setDirty(true);
        setErrors({});
    };

    const changeTags = (next) => {
        setTags(next);
        setDirty(true);
    };

    const save = async (status) => {
        const nextErrors = validateQuestionForm({ ...form, status });
        setErrors(nextErrors);
        if (Object.keys(nextErrors).length) return;

        setSaving(true);
        try {
            const payload = buildQuestionPayload(form, tags, status);
            if (isEdit) await updateQuestion(id, payload);
            else await createQuestion(payload);
            toast.success(isEdit ? 'Question updated' : 'Question created');
            setDirty(false);
            navigate('/admin/aptitude/questions');
        } catch (error) {
            const serverErrors = getValidationErrors(error);
            if (Object.keys(serverErrors).length) setErrors(serverErrors);
            toast.error(getApiErrorMessage(error, 'Save failed'));
        } finally {
            setSaving(false);
        }
    };

    const runStatusAction = async () => {
        if (!confirm) return;
        setSaving(true);
        try {
            if (confirm === 'approve') await approveQuestion(id);
            if (confirm === 'archive') await archiveQuestion(id);
            if (confirm === 'restore') await restoreQuestion(id);
            toast.success('Status updated');
            setConfirm(null);
            loadQuestion();
        } catch (error) {
            toast.error(getApiErrorMessage(error, 'Status update failed'));
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <div className="apt-admin-page">
                <div className="apt-page-header"><h1 className="gradient-text">Loading Question</h1></div>
                <SkeletonCard style={{ height: '520px' }} />
            </div>
        );
    }

    return (
        <div className="apt-admin-page">
            <div className="apt-page-header apt-page-header-row">
                <div>
                    <h1 className="gradient-text">{isEdit ? 'Edit Question' : 'Add Question'}</h1>
                    <p>{isEdit ? 'Update question content, metadata, publication state, and taxonomy.' : 'Create a new aptitude question for review or publishing.'}</p>
                </div>
                {isEdit && (
                    <div className="apt-status-actions">
                        <StatusBadge value={form.status} />
                        {form.status !== 'approved' && <button className="btn btn-secondary apt-btn-sm" type="button" onClick={() => setConfirm('approve')}><FiCheckCircle /> Approve</button>}
                        {form.status !== 'archived' && <button className="btn btn-secondary apt-btn-sm" type="button" onClick={() => setConfirm('archive')}><FiArchive /> Archive</button>}
                        {form.status === 'archived' && <button className="btn btn-secondary apt-btn-sm" type="button" onClick={() => setConfirm('restore')}><FiRotateCcw /> Restore</button>}
                    </div>
                )}
            </div>

            <QuestionForm
                value={form}
                tags={tags}
                errors={errors}
                saving={saving}
                isEdit={isEdit}
                onChange={changeForm}
                onTagsChange={changeTags}
                onCancel={() => navigate('/admin/aptitude/questions')}
                onSaveDraft={() => save('draft')}
                onPublish={() => save('approved')}
            />

            <ConfirmDialog
                open={!!confirm}
                message={`Are you sure you want to ${confirm} this question?`}
                danger={confirm === 'archive'}
                loading={saving}
                onCancel={() => setConfirm(null)}
                onConfirm={runStatusAction}
            />
        </div>
    );
}
