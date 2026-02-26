import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { toast } from 'react-toastify';
import api from '../utils/api';
import { FiUploadCloud, FiPlus, FiX, FiFileText } from 'react-icons/fi';

export default function Skills() {
    const { user, fetchUser } = useAuth();
    const [skills, setSkills] = useState([]);
    const [newSkill, setNewSkill] = useState('');
    const [resumeFile, setResumeFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (user?.skills) {
            setSkills(user.skills);
        }
    }, [user]);

    const handleAddSkill = () => {
        if (!newSkill.trim()) return;
        if (skills.includes(newSkill.trim())) {
            toast.warning('Skill already added!');
            return;
        }
        setSkills([...skills, newSkill.trim()]);
        setNewSkill('');
    };

    const handleRemoveSkill = (skillToRemove) => {
        setSkills(skills.filter(s => s !== skillToRemove));
    };

    const handleSaveSkills = async () => {
        setSaving(true);
        try {
            await api.put('/auth/profile', { skills });
            toast.success('Skills updated successfully!');
            await fetchUser();
        } catch (error) {
            toast.error(error.response?.data?.detail || 'Failed to update skills');
        } finally {
            setSaving(false);
        }
    };

    const handleResumeUpload = async (e) => {
        e.preventDefault();
        if (!resumeFile) {
            toast.warning('Please select a PDF file');
            return;
        }

        const formData = new FormData();
        formData.append('file', resumeFile);

        setUploading(true);
        try {
            await api.post('/auth/resume', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            toast.success('Resume uploaded successfully!');
            await fetchUser();
            setResumeFile(null);
            document.getElementById('resume-upload-form').reset();
        } catch (error) {
            toast.error(error.response?.data?.detail || 'Failed to upload resume');
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="dashboard-content fade-in-up">
            <div className="page-header slide-in-left">
                <h1 className="gradient-text">My Skills & Resume</h1>
                <p>Manage your professional profile for better AI interviews.</p>
            </div>

            <div className="dashboard-grid">
                {/* Skills Section */}
                <div className="dashboard-card action-card fade-in-up">
                    <h3>Technical Skills</h3>
                    <p className="text-muted" style={{ marginBottom: '15px' }}>
                        Add your key skills (e.g., Python, React, Machine Learning). These will be used by our AI Interviewer to dynamically test your knowledge.
                    </p>

                    <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
                        <input
                            type="text"
                            className="input-field"
                            placeholder="e.g. Node.js"
                            value={newSkill}
                            onChange={(e) => setNewSkill(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleAddSkill()}
                        />
                        <button className="btn btn-primary" onClick={handleAddSkill} style={{ padding: '0.75rem 1rem' }}>
                            <FiPlus />
                        </button>
                    </div>

                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginBottom: '20px' }}>
                        {skills.map((skill, index) => (
                            <span
                                key={index}
                                style={{
                                    background: 'var(--color-bg-alt)',
                                    border: '1px solid var(--color-border)',
                                    padding: '5px 12px',
                                    borderRadius: '50px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px',
                                    fontSize: '0.9rem'
                                }}
                            >
                                {skill}
                                <button
                                    onClick={() => handleRemoveSkill(skill)}
                                    style={{
                                        background: 'transparent',
                                        border: 'none',
                                        cursor: 'pointer',
                                        color: 'var(--color-text-muted)',
                                        display: 'flex',
                                        alignItems: 'center',
                                        padding: 0
                                    }}
                                >
                                    <FiX />
                                </button>
                            </span>
                        ))}
                    </div>

                    <button
                        className="btn btn-secondary"
                        onClick={handleSaveSkills}
                        disabled={saving}
                        style={{ width: '100%' }}
                    >
                        {saving ? 'Saving...' : 'Save Skills'}
                    </button>
                </div>

                {/* Resume Upload Section */}
                <div className="dashboard-card action-card fade-in-delay-1">
                    <h3>Resume Upload</h3>
                    <p className="text-muted" style={{ marginBottom: '15px' }}>
                        Upload your latest resume (PDF format). The AI Interviewer uses this for deep profiling.
                    </p>

                    {user?.resume_url && (
                        <div style={{ marginBottom: '20px', padding: '15px', background: 'var(--color-bg-alt)', border: '1px solid var(--color-success)', borderRadius: '8px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
                                <FiFileText style={{ color: 'var(--color-success)' }} />
                                <span style={{ fontWeight: 600 }}>Active Resume</span>
                            </div>
                            <a
                                href={user.resume_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="btn btn-secondary"
                                style={{ width: '100%', fontSize: '0.8rem', padding: '8px' }}
                            >
                                View Current Resume
                            </a>
                        </div>
                    )}

                    <form id="resume-upload-form" onSubmit={handleResumeUpload} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                        <div className="file-upload-wrapper">
                            <input
                                type="file"
                                id="resume-upload-input"
                                className="file-upload-input"
                                accept="application/pdf"
                                onChange={(e) => setResumeFile(e.target.files[0])}
                            />
                            <div className="file-upload-display">
                                <div className="file-upload-icon bg-secondary">
                                    <FiUploadCloud />
                                </div>
                                <span>{resumeFile ? resumeFile.name : 'Choose PDF file or drag & drop'}</span>
                            </div>
                        </div>

                        <button
                            type="submit"
                            className="btn btn-primary"
                            disabled={uploading || !resumeFile}
                            style={{ width: '100%' }}
                        >
                            {uploading ? 'Uploading...' : 'Upload Resume'}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}
