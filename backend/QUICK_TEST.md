# Quick Verification Agent Test

## Start Backend
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Test with curl (replace JWT_TOKEN)

### 1. Certificate Verification
```bash
curl -X POST "http://localhost:8000/verify" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "profile_data={\"name\":\"John Doe\"}"
```

### 2. Project Verification  
```bash
curl -X POST "http://localhost:8000/verify" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "link=https://github.com/microsoft/vscode" \
  -F "profile_data={\"name\":\"John Doe\"}"
```

### 3. Profile Verification
```bash
curl -X POST "http://localhost:8000/verify" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "profile_data={\"name\":\"John Doe\",\"email\":\"john@example.com\"}"
```

## Check Terminal Logs
Look for `[VERIFICATION]` prefixed logs showing:
- Input classification
- Pipeline execution
- Scoring results
- Storage operations

## Expected Response Format
```json
{
  "run_id": "uuid",
  "input_type": "certificate|project|profile", 
  "confidence_score": 0.85,
  "status": "verified|suspicious|failed",
  "explanation": {
    "summary": "...",
    "findings": ["..."],
    "recommendations": ["..."]
  }
}
```
