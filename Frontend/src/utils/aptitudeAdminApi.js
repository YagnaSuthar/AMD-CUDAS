import api from './api';

const BASE = '/admin/aptitude';

export function getApiErrorMessage(error, fallback = 'Something went wrong') {
    const status = error?.response?.status;
    const detail = error?.response?.data?.detail;

    if (status === 401) return 'Your session expired. Please sign in again.';
    if (status === 403) return 'You do not have permission to manage aptitude questions.';
    if (status === 404) return 'The requested aptitude resource was not found.';
    if (status === 422) return 'Please check the highlighted fields and try again.';
    if (status >= 500) return 'Server error. Please try again in a moment.';
    if (typeof detail === 'string') return detail;
    if (detail?.message) return detail.message;

    return fallback;
}

export function getValidationErrors(error) {
    const detail = error?.response?.data?.detail;
    const errors = Array.isArray(detail?.errors) ? detail.errors : Array.isArray(detail) ? detail : [];

    return errors.reduce((acc, item) => {
        const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : item.field;
        if (field) acc[field] = item.message || item.msg || 'Invalid value';
        return acc;
    }, {});
}

export async function fetchQuestions(params = {}) {
    const res = await api.get(`${BASE}/questions`, { params });
    return res.data;
}

export async function fetchQuestion(id) {
    const res = await api.get(`${BASE}/questions/${id}`);
    return res.data;
}

export async function createQuestion(body) {
    const res = await api.post(`${BASE}/questions`, body);
    return res.data;
}

export async function updateQuestion(id, body) {
    const res = await api.put(`${BASE}/questions/${id}`, body);
    return res.data;
}

export async function deleteQuestion(id) {
    const res = await api.delete(`${BASE}/questions/${id}`);
    return res.data;
}

export async function approveQuestion(id) {
    const res = await api.patch(`${BASE}/questions/${id}/approve`);
    return res.data;
}

export async function archiveQuestion(id) {
    const res = await api.patch(`${BASE}/questions/${id}/archive`);
    return res.data;
}

export async function restoreQuestion(id) {
    const res = await api.patch(`${BASE}/questions/${id}/restore`);
    return res.data;
}

export async function bulkApprove(ids) {
    return Promise.all(ids.map((id) => approveQuestion(id)));
}

export async function bulkArchive(ids) {
    return Promise.all(ids.map((id) => archiveQuestion(id)));
}

export async function uploadImportFile(file, onUploadProgress) {
    const form = new FormData();
    form.append('file', file);

    const res = await api.post(`${BASE}/import/upload`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress,
    });
    return res.data;
}

export async function fetchImportJobs(params = {}) {
    const res = await api.get(`${BASE}/import/jobs`, { params });
    return res.data;
}

export async function fetchImportJob(jobId) {
    const res = await api.get(`${BASE}/import/jobs/${jobId}`);
    return res.data;
}

export async function confirmImport(jobId) {
    const res = await api.post(`${BASE}/import/jobs/${jobId}/confirm`);
    return res.data;
}

export async function cancelImport(jobId) {
    const res = await api.post(`${BASE}/import/jobs/${jobId}/cancel`);
    return res.data;
}

export async function fetchDomains() {
    const res = await api.get('/domains');
    return res.data;
}

export async function fetchCategories() {
    const res = await api.get('/categories');
    return res.data;
}

export async function fetchSubcategories() {
    const res = await api.get('/subcategories');
    return res.data;
}

export async function fetchTaxonomyTree() {
    const res = await api.get(`${BASE}/taxonomy`);
    return res.data;
}

export async function fetchStatistics() {
    const res = await api.get(`${BASE}/statistics`);
    return res.data;
}
