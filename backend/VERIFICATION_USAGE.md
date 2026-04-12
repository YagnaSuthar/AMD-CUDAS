# Verification Agent Usage Guide

## Overview

The Verification Agent provides unified verification for certificates, GitHub projects, and user profiles with scoring, explanations, and storage.

## API Endpoints

### POST /verify
Verify certificates, projects, or profiles.

**Request:** `multipart/form-data`
- `file` (optional): Upload file (PDF/image for certificates)
- `link` (optional): URL to verify (GitHub links for projects)
- `profile_data` (optional): JSON string with profile information

**Response:**
```json
{
  "run_id": "uuid",
  "input_type": "certificate|project|profile",
  "confidence_score": 0.85,
  "status": "verified|suspicious|failed",
  "explanation": {
    "summary": "Verification summary",
    "findings": ["Key finding 1", "Key finding 2"],
    "recommendations": ["Recommendation 1"]
  }
}
```

### POST /verify/{run_id}/feedback
Submit feedback for a verification run.

**Request:**
```json
{
  "is_correct": true,
  "notes": "Optional feedback notes"
}
```

**Response:**
```json
{
  "message": "Feedback submitted"
}
```

## Sample API Requests

### 1. Certificate Verification (File Upload)

```bash
curl -X POST "http://localhost:8000/verify" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@certificate.pdf" \
  -F "profile_data={\"name\":\"John Doe\",\"expected_issuer\":\"Test University\"}"
```

### 2. Project Verification (GitHub Link)

```bash
curl -X POST "http://localhost:8000/verify" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "link=https://github.com/microsoft/vscode" \
  -F "profile_data={\"name\":\"John Doe\",\"github_username\":\"johndoe\"}"
```

### 3. Profile Verification

```bash
curl -X POST "http://localhost:8000/verify" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "profile_data={\"name\":\"John Doe\",\"email\":\"john@example.com\",\"education\":[{\"institution\":\"Test University\",\"degree\":\"Bachelor of Science\"}]}"
```

### 4. Submit Feedback

```bash
curl -X POST "http://localhost:8000/verify/UUID_HERE/feedback" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_correct": true, "notes": "Accurate verification"}'
```

## React Integration

### Setup

```javascript
// api/verification.js
const API_BASE = 'http://localhost:8000';

const getAuthHeaders = () => ({
  'Authorization': `Bearer ${localStorage.getItem('token')}`
});

// Verification API calls
export const verificationAPI = {
  // Verify certificate/project/profile
  verify: async (formData) => {
    const response = await fetch(`${API_BASE}/verify`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: formData // FormData object
    });
    return response.json();
  },

  // Submit feedback
  submitFeedback: async (runId, feedback) => {
    const response = await fetch(`${API_BASE}/verify/${runId}/feedback`, {
      method: 'POST',
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(feedback)
    });
    return response.json();
  }
};
```

### React Component Example

```jsx
// components/VerificationForm.jsx
import React, { useState } from 'react';
import { verificationAPI } from '../api/verification';

const VerificationForm = () => {
  const [file, setFile] = useState(null);
  const [link, setLink] = useState('');
  const [profileData, setProfileData] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const formData = new FormData();
      
      if (file) formData.append('file', file);
      if (link) formData.append('link', link);
      if (profileData) formData.append('profile_data', profileData);

      const response = await verificationAPI.verify(formData);
      setResult(response);
    } catch (error) {
      console.error('Verification failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (runId, isCorrect, notes) => {
    try {
      await verificationAPI.submitFeedback(runId, { is_correct: isCorrect, notes });
      alert('Feedback submitted!');
    } catch (error) {
      console.error('Feedback failed:', error);
    }
  };

  return (
    <div className="verification-form">
      <h2>Verify Certificate, Project, or Profile</h2>
      
      <form onSubmit={handleSubmit}>
        <div>
          <label>Upload File (Certificate):</label>
          <input
            type="file"
            accept=".pdf,.jpg,.jpeg,.png"
            onChange={(e) => setFile(e.target.files[0])}
          />
        </div>

        <div>
          <label>Link (GitHub Project):</label>
          <input
            type="url"
            value={link}
            onChange={(e) => setLink(e.target.value)}
            placeholder="https://github.com/user/repo"
          />
        </div>

        <div>
          <label>Profile Data (JSON):</label>
          <textarea
            value={profileData}
            onChange={(e) => setProfileData(e.target.value)}
            placeholder='{"name": "John Doe", "email": "john@example.com"}'
            rows={4}
          />
        </div>

        <button type="submit" disabled={loading}>
          {loading ? 'Verifying...' : 'Verify'}
        </button>
      </form>

      {result && (
        <div className="verification-result">
          <h3>Verification Result</h3>
          <p><strong>Run ID:</strong> {result.run_id}</p>
          <p><strong>Type:</strong> {result.input_type}</p>
          <p><strong>Confidence:</strong> {(result.confidence_score * 100).toFixed(1)}%</p>
          <p><strong>Status:</strong> <span className={`status ${result.status}`}>{result.status}</span></p>
          
          <div>
            <h4>Explanation</h4>
            <p>{result.explanation.summary}</p>
            <ul>
              {result.explanation.findings.map((finding, idx) => (
                <li key={idx}>{finding}</li>
              ))}
            </ul>
            
            {result.explanation.recommendations.length > 0 && (
              <div>
                <h5>Recommendations:</h5>
                <ul>
                  {result.explanation.recommendations.map((rec, idx) => (
                    <li key={idx}>{rec}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <div className="feedback-section">
            <h4>Was this verification helpful?</h4>
            <button onClick={() => handleFeedback(result.run_id, true, 'Accurate')}>
              ✓ Correct
            </button>
            <button onClick={() => handleFeedback(result.run_id, false, 'Needs improvement')}>
              ✗ Incorrect
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default VerificationForm;
```

### Styling (CSS)

```css
/* VerificationForm.css */
.verification-form {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
}

.verification-form form > div {
  margin-bottom: 15px;
}

.verification-form label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

.verification-form input,
.verification-form textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.verification-form button {
  background: #007bff;
  color: white;
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.verification-form button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.verification-result {
  margin-top: 30px;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background: #f9f9f9;
}

.status.verified {
  color: #28a745;
  font-weight: bold;
}

.status.suspicious {
  color: #ffc107;
  font-weight: bold;
}

.status.failed {
  color: #dc3545;
  font-weight: bold;
}

.feedback-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #ddd;
}

.feedback-section button {
  margin-right: 10px;
  padding: 8px 16px;
}
```

## Running the Backend

```bash
# Navigate to backend directory
cd backend

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Testing

Run the test script:

```bash
# Update JWT_TOKEN in test_verification.py first
python test_verification.py
```

Or use curl commands shown above.

## Logging

The Verification Agent includes detailed logging prefixed with `[VERIFICATION]`. Enable debug logging to see all details:

```bash
# Set log level before starting
export LOG_LEVEL=DEBUG
uvicorn app.main:app --reload
```

## Features

- **Multi-type verification**: Certificates (PDF/image), GitHub projects, user profiles
- **Scoring system**: Weighted scoring with confidence scores and status determination
- **Explanations**: AI-generated explanations with findings and recommendations
- **Storage**: All verification runs stored in database with full details
- **Vector indexing**: Verification runs indexed for semantic search and learning
- **Feedback system**: Users can provide feedback to improve the system
- **Robust extraction**: PDF text extraction with OCR fallback
- **GitHub integration**: Project validation via GitHub API
- **Cross-profile consistency**: Checks for consistency across user data
