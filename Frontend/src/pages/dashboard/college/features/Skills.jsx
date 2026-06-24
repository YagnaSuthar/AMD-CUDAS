import { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../../../../context/AuthContext';
import { toast } from 'react-toastify';
import api from '../../../../utils/api';
import {
  FiUploadCloud,
  FiPlus,
  FiX,
  FiFileText,
  FiTrendingUp,
  FiAward,
  FiTarget,
  FiBarChart2,
  FiCheckCircle,
  FiClock,
  FiFile,
} from 'react-icons/fi';
import '../../../../style/skills.css';

export default function Skills() {
  const { user, fetchUser } = useAuth();
  const [skills, setSkills] = useState([]);
  const [newSkill, setNewSkill] = useState('');
  const [resumeFile, setResumeFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [skillCategory, setSkillCategory] = useState('technical');
  const [suggestedSkills, setSuggestedSkills] = useState([]);

  const skillSuggestions = useMemo(
    () => ({
      technical: ['JavaScript', 'React', 'Node.js', 'Python', 'AWS', 'Docker', 'MongoDB', 'PostgreSQL'],
      soft: ['Communication', 'Leadership', 'Problem Solving', 'Teamwork', 'Time Management', 'Critical Thinking'],
      business: ['Project Management', 'Agile', 'Scrum', 'Data Analysis', 'Strategic Planning', 'Marketing'],
    }),
    []
  );

  useEffect(() => {
    if (user?.skills) setSkills(user.skills);
  }, [user]);

  useEffect(() => {
    setSuggestedSkills(skillSuggestions[skillCategory] || []);
  }, [skillCategory, skillSuggestions]);

  const handleAddSkill = () => {
    if (!newSkill.trim()) return;
    if (skills.includes(newSkill.trim())) {
      toast.warning('Skill already added!');
      return;
    }
    setSkills([...skills, newSkill.trim()]);
    setNewSkill('');
  };

  const handleAddSuggestedSkill = (skill) => {
    if (skills.includes(skill)) {
      toast.warning('Skill already added!');
      return;
    }
    setSkills([...skills, skill]);
  };

  const handleRemoveSkill = (skillToRemove) => {
    setSkills(skills.filter((s) => s !== skillToRemove));
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
        headers: { 'Content-Type': 'multipart/form-data' },
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

  const profileCompletionPct = useMemo(() => {
    const totalSkills = Object.values(skillSuggestions).flat().length;
    return Math.floor((skills.length / totalSkills) * 100);
  }, [skills, skillSuggestions]);

  const aiReady = useMemo(() => skills.length >= 5, [skills]);

  const skillDistribution = useMemo(() => {
    const technicalSet = new Set(skillSuggestions.technical || []);
    const softSet = new Set(skillSuggestions.soft || []);
    const businessSet = new Set(skillSuggestions.business || []);
    let technical = 0, soft = 0, business = 0;
    for (const s of skills) {
      if (technicalSet.has(s)) technical += 1;
      else if (softSet.has(s)) soft += 1;
      else if (businessSet.has(s)) business += 1;
    }
    return { technical, soft, business };
  }, [skills, skillSuggestions]);

  return (
    <div className="dashboard-content fade-in">

      {/* Page Header */}
      <div className="page-header slide-in-left">
        <h1 className="gradient-text">Skills Development Hub</h1>
        <p>Enhance your professional profile with verified skills and track your career progression</p>
      </div>

      {/* Stats Row */}
      <div className="skills-stats-row fade-in-up">
        <div className="stat-card">
          <div className="stat-card-header">
            <span className="stat-card-label">Total Skills</span>
            <div className="stat-card-icon" style={{ background: 'var(--gradient-primary)' }}><FiAward /></div>
          </div>
          <div className="stat-card-value">{skills.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-header">
            <span className="stat-card-label">Profile Strength</span>
            <div className="stat-card-icon" style={{ background: 'var(--color-success)' }}><FiTrendingUp /></div>
          </div>
          <div className="stat-card-value">{profileCompletionPct}%</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-header">
            <span className="stat-card-label">Career Track</span>
            <div className="stat-card-icon" style={{ background: 'var(--gradient-secondary)' }}><FiTarget /></div>
          </div>
          <div className="stat-card-value">
            {skills.length > 5 ? 'Advanced' : skills.length > 2 ? 'Growing' : 'Starter'}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-card-header">
            <span className="stat-card-label">AI Interview Ready</span>
            <div className="stat-card-icon" style={{ background: aiReady ? 'var(--color-success)' : 'var(--color-warning)' }}>
              {aiReady ? <FiCheckCircle /> : <FiClock />}
            </div>
          </div>
          <div className="stat-card-value">{aiReady ? 'Ready' : 'In Progress'}</div>
        </div>
      </div>

      {/* Main Grid */}
      <div className="skills-layout" style={{ gridTemplateColumns: '1fr 1fr 1fr' }}>

        {/* Skills Management */}
        <div className="dashboard-card fade-in-up skills-card">
          <div className="skills-header">
            <h3><FiAward /> Skills Management</h3>
            <div className="skill-category-tabs">
              {['technical', 'soft', 'business'].map((cat) => (
                <button
                  key={cat}
                  type="button"
                  className={`category-tab ${skillCategory === cat ? 'active' : ''}`}
                  onClick={() => setSkillCategory(cat)}
                >
                  {cat.charAt(0).toUpperCase() + cat.slice(1)}
                </button>
              ))}
            </div>
          </div>

          <div className="skills-input-row">
            <input
              type="text"
              className="input-field"
              placeholder={`e.g., ${suggestedSkills[0] || 'JavaScript'}`}
              value={newSkill}
              onChange={(e) => setNewSkill(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAddSkill()}
            />
            <button className="btn btn-primary skills-icon-btn" type="button" onClick={handleAddSkill}>
              <FiPlus />
            </button>
          </div>

          <div className="suggested-card">
            <div className="suggested-title">Suggested {skillCategory} skills</div>
            <div className="suggested-pill-wrap">
              {suggestedSkills.slice(0, 8).map((s) => (
                <button
                  key={s}
                  type="button"
                  className="suggested-pill"
                  onClick={() => handleAddSuggestedSkill(s)}
                  disabled={skills.includes(s)}
                >
                  <FiPlus />{s}
                </button>
              ))}
            </div>
          </div>

          <div className="skills-pill-wrap">
            {skills.map((skill, index) => (
              <span key={`${skill}-${index}`} className="skills-pill">
                {skill}
                <button type="button" onClick={() => handleRemoveSkill(skill)}><FiX /></button>
              </span>
            ))}
          </div>

          <button className="btn btn-secondary skills-save-btn" type="button" onClick={handleSaveSkills} disabled={saving}>
            {saving ? 'Saving...' : 'Save All Skills'}
          </button>
        </div>

        {/* Resume Upload — Professional */}
        <div className="dashboard-card action-card fade-in-delay-1">
          <h3><FiFileText /> Resume Upload</h3>
          <p className="text-muted" style={{ marginBottom: '14px', fontSize: '0.82rem' }}>
            Upload your latest PDF resume. The AI Interviewer uses it for deep candidate profiling.
          </p>

          {/* Active resume badge */}
          {user?.resume_url && (
            <div className="resume-active">
              <div className="resume-active-icon"><FiCheckCircle /></div>
              <div className="resume-active-info">
                <div className="resume-active-label">Resume Active</div>
                <div className="resume-active-sub">Ready for AI interviews</div>
              </div>
              <a
                href={user.resume_url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-secondary resume-view-btn"
              >
                View
              </a>
            </div>
          )}

          {/* Upload form */}
          <form id="resume-upload-form" onSubmit={handleResumeUpload} className="resume-form">

            {/* Custom drop zone — hides native file input */}
            <label className={`resume-dropzone${resumeFile ? ' has-file' : ''}`}>
              <input
                type="file"
                id="resume-upload-input"
                accept="application/pdf"
                onChange={(e) => setResumeFile(e.target.files[0])}
              />
              <div className="resume-dropzone-icon">
                {resumeFile ? <FiFile /> : <FiUploadCloud />}
              </div>
              {resumeFile ? (
                <>
                  <div className="resume-dropzone-title">File selected</div>
                  <div className="resume-dropzone-filename">
                    <FiFile size={12} />{resumeFile.name}
                  </div>
                </>
              ) : (
                <>
                  <div className="resume-dropzone-title">Click to browse or drag & drop</div>
                  <div className="resume-dropzone-sub">PDF only Â· Max 10 MB</div>
                </>
              )}
            </label>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={uploading || !resumeFile}
              style={{ width: '100%', padding: '9px', fontSize: '0.83rem' }}
            >
              {uploading ? 'Uploading...' : 'Upload Resume'}
            </button>
          </form>
        </div>

        {/* â”€â”€ Skill Analytics â”€â”€ */}
        <div className="dashboard-card analytics-card fade-in-delay-2">
          <h3><FiBarChart2 /> Skill Analytics</h3>
          <div className="analytics-content">
            <div className="progress-item">
              <div className="progress-header">
                <span>Profile Completion</span>
                <span>{profileCompletionPct}%</span>
              </div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${profileCompletionPct}%` }} />
              </div>
            </div>

            <div className="progress-item">
              <div className="progress-header">
                <span style={{ fontWeight: 700, color: 'var(--color-text-primary)' }}>Skill Distribution</span>
              </div>
              <div className="analytics-content" style={{ gap: '10px' }}>
                <div className="progress-header"><span>Technical</span><span>{skillDistribution.technical}</span></div>
                <div className="progress-header"><span>Soft Skills</span><span>{skillDistribution.soft}</span></div>
                <div className="progress-header"><span>Business</span><span>{skillDistribution.business}</span></div>
              </div>
            </div>

            <div className="progress-item">
              <div className="progress-header">
                <span style={{ fontWeight: 700, color: 'var(--color-text-primary)' }}>Next Steps</span>
              </div>
              <div className="progress-header" style={{ justifyContent: 'flex-start', gap: '8px' }}>
                <FiTarget /><span>Start practicing with AI interviews</span>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}