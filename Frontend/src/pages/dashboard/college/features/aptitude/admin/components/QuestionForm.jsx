import { useMemo, useState } from 'react';
import { FiCheckCircle, FiPlus, FiSave, FiX } from 'react-icons/fi';

const DOMAINS = ['quantitative', 'logical_reasoning', 'verbal_ability', 'data_interpretation'];
const DIFFICULTIES = ['easy', 'medium', 'hard'];
const STATUSES = ['draft', 'approved', 'archived'];

export const EMPTY_QUESTION_FORM = {
    question: '',
    option_a: '',
    option_b: '',
    option_c: '',
    option_d: '',
    correct_answer: '',
    explanation: '',
    domain: 'quantitative',
    category: '',
    subcategory: '',
    difficulty: 'medium',
    expected_time_seconds: '',
    status: 'draft',
    source: 'admin',
};

export function normalizeQuestionToForm(question) {
    return {
        question: question?.question || '',
        option_a: question?.options?.[0] || '',
        option_b: question?.options?.[1] || '',
        option_c: question?.options?.[2] || '',
        option_d: question?.options?.[3] || '',
        correct_answer: question?.correct_answer || '',
        explanation: question?.explanation || '',
        domain: question?.domain || 'quantitative',
        category: question?.category || '',
        subcategory: question?.subcategory || '',
        difficulty: question?.difficulty || 'medium',
        expected_time_seconds: question?.expected_time_seconds || '',
        status: question?.status || 'draft',
        source: question?.source || 'admin',
    };
}

export function buildQuestionPayload(form, tags, overrideStatus) {
    return {
        question: form.question.trim(),
        options: [form.option_a, form.option_b, form.option_c, form.option_d].map((item) => item.trim()),
        correct_answer: form.correct_answer.trim(),
        explanation: form.explanation.trim() || null,
        domain: form.domain,
        category: form.category.trim(),
        subcategory: form.subcategory.trim() || null,
        difficulty: form.difficulty,
        tags,
        expected_time_seconds: form.expected_time_seconds ? Number(form.expected_time_seconds) : null,
        status: overrideStatus || form.status,
        source: form.source || 'admin',
    };
}

export function validateQuestionForm(form) {
    const errors = {};
    const options = [form.option_a, form.option_b, form.option_c, form.option_d].map((item) => item.trim());

    if (!form.question.trim()) errors.question = 'Question is required';
    if (form.question.trim().length < 5) errors.question = 'Question must be at least 5 characters';
    options.forEach((value, index) => {
        if (!value) errors[`option_${String.fromCharCode(97 + index)}`] = 'Option is required';
    });
    if (options.every(Boolean) && new Set(options.map((item) => item.toLowerCase())).size !== 4) {
        errors.option_a = 'All options must be unique';
    }
    if (!form.correct_answer.trim()) errors.correct_answer = 'Correct answer is required';
    if (form.correct_answer.trim() && !options.includes(form.correct_answer.trim())) {
        errors.correct_answer = 'Correct answer must match one of the options';
    }
    if (!form.domain) errors.domain = 'Domain is required';
    if (!form.category.trim()) errors.category = 'Category is required';
    if (!DIFFICULTIES.includes(form.difficulty)) errors.difficulty = 'Choose a valid difficulty';
    if (!STATUSES.includes(form.status)) errors.status = 'Choose a valid status';
    if (form.expected_time_seconds !== '' && (!Number.isFinite(Number(form.expected_time_seconds)) || Number(form.expected_time_seconds) <= 0)) {
        errors.expected_time_seconds = 'Expected solve time must be greater than 0';
    }

    return errors;
}

export default function QuestionForm({
    value,
    tags,
    errors,
    saving,
    isEdit,
    onChange,
    onTagsChange,
    onCancel,
    onSaveDraft,
    onPublish,
}) {
    const [tagInput, setTagInput] = useState('');
    const answerOptions = useMemo(
        () => [value.option_a, value.option_b, value.option_c, value.option_d].filter(Boolean),
        [value.option_a, value.option_b, value.option_c, value.option_d]
    );

    const setField = (field, fieldValue) => onChange({ ...value, [field]: fieldValue });
    const addTag = () => {
        const nextTag = tagInput.trim().toLowerCase();
        if (nextTag && !tags.includes(nextTag)) onTagsChange([...tags, nextTag]);
        setTagInput('');
    };
    const removeTag = (tag) => onTagsChange(tags.filter((item) => item !== tag));

    return (
        <div className="apt-form-card">
            <div className="apt-form-grid">
                <div className="apt-form-group full-width">
                    <label>Question</label>
                    <textarea rows="4" value={value.question} onChange={(event) => setField('question', event.target.value)} />
                    {errors.question && <span className="field-error">{errors.question}</span>}
                </div>

                {['a', 'b', 'c', 'd'].map((key) => (
                    <div className="apt-form-group" key={key}>
                        <label>Option {key.toUpperCase()}</label>
                        <input value={value[`option_${key}`]} onChange={(event) => setField(`option_${key}`, event.target.value)} />
                        {errors[`option_${key}`] && <span className="field-error">{errors[`option_${key}`]}</span>}
                    </div>
                ))}

                <div className="apt-form-group">
                    <label>Correct Answer</label>
                    <select value={value.correct_answer} onChange={(event) => setField('correct_answer', event.target.value)}>
                        <option value="">Select answer</option>
                        {answerOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                    {errors.correct_answer && <span className="field-error">{errors.correct_answer}</span>}
                </div>

                <div className="apt-form-group">
                    <label>Domain</label>
                    <select value={value.domain} onChange={(event) => setField('domain', event.target.value)}>
                        {DOMAINS.map((domain) => <option key={domain} value={domain}>{domain.replaceAll('_', ' ')}</option>)}
                    </select>
                    {errors.domain && <span className="field-error">{errors.domain}</span>}
                </div>

                <div className="apt-form-group">
                    <label>Category</label>
                    <input value={value.category} onChange={(event) => setField('category', event.target.value)} />
                    {errors.category && <span className="field-error">{errors.category}</span>}
                </div>

                <div className="apt-form-group">
                    <label>Subcategory</label>
                    <input value={value.subcategory} onChange={(event) => setField('subcategory', event.target.value)} />
                </div>

                <div className="apt-form-group">
                    <label>Difficulty</label>
                    <select value={value.difficulty} onChange={(event) => setField('difficulty', event.target.value)}>
                        {DIFFICULTIES.map((difficulty) => <option key={difficulty} value={difficulty}>{difficulty}</option>)}
                    </select>
                    {errors.difficulty && <span className="field-error">{errors.difficulty}</span>}
                </div>

                <div className="apt-form-group">
                    <label>Expected Solve Time</label>
                    <input type="number" min="1" value={value.expected_time_seconds} onChange={(event) => setField('expected_time_seconds', event.target.value)} placeholder="Seconds" />
                    {errors.expected_time_seconds && <span className="field-error">{errors.expected_time_seconds}</span>}
                </div>

                <div className="apt-form-group">
                    <label>Status</label>
                    <select value={value.status} onChange={(event) => setField('status', event.target.value)}>
                        {STATUSES.map((status) => <option key={status} value={status}>{status}</option>)}
                    </select>
                    {errors.status && <span className="field-error">{errors.status}</span>}
                </div>

                <div className="apt-form-group full-width">
                    <label>Explanation</label>
                    <textarea rows="3" value={value.explanation} onChange={(event) => setField('explanation', event.target.value)} />
                </div>

                <div className="apt-form-group full-width">
                    <label>Tags</label>
                    <div className="apt-inline-input">
                        <input
                            value={tagInput}
                            onChange={(event) => setTagInput(event.target.value)}
                            onKeyDown={(event) => {
                                if (event.key === 'Enter') {
                                    event.preventDefault();
                                    addTag();
                                }
                            }}
                            placeholder="Type a tag and press Enter"
                        />
                        <button className="apt-action-btn" type="button" onClick={addTag} title="Add tag"><FiPlus /></button>
                    </div>
                    <div className="apt-tags">
                        {tags.map((tag) => (
                            <span className="apt-tag" key={tag}>
                                {tag}
                                <button type="button" onClick={() => removeTag(tag)} aria-label={`Remove ${tag}`}><FiX /></button>
                            </span>
                        ))}
                    </div>
                </div>
            </div>

            <div className="apt-form-actions">
                <button className="btn btn-secondary" type="button" onClick={onCancel}>Cancel</button>
                <button className="btn btn-secondary" type="button" onClick={onSaveDraft} disabled={saving}>
                    <FiSave /> {saving ? 'Saving...' : 'Save Draft'}
                </button>
                <button className="btn btn-primary" type="button" onClick={onPublish} disabled={saving}>
                    <FiCheckCircle /> {saving ? 'Saving...' : isEdit ? 'Approve & Update' : 'Approve & Publish'}
                </button>
            </div>
        </div>
    );
}
