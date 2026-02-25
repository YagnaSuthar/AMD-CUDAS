# 🚀 CUDAS AI Agents – Full Stack FastAPI Backend

A modular FastAPI backend containing multiple AI agents:  
- Academic Agent  
- Multilingual Agent  
- Interview Agent  
- Performance Agent  

Structured using feature-based architecture for scalability and clean code organization.

## Setup Instructions

### 1. Backend Setup

The backend requires a PostgreSQL database and an LLM provider (Groq).

```bash
cd backend

# Create Virtual Environment & Install Dependencies
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate # Mac/Linux

pip install -r app/requirements.txt
```

#### Environment Variables
Create a `.env` file in the `backend/app/` directory based on `.env.example`:

1.  **Database:** Ensure PostgreSQL is running.
    `DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/cudas`
2.  **LLM:** Add your Groq API key:
    `GROQ_API_KEY=your_key_here`
3.  **Authentication (NEW):**
    `JWT_SECRET_KEY=generate_a_secure_random_string`
    `JWT_REFRESH_SECRET=generate_another_random_string`
4.  **Email settings (for verification/passwords):**
    `SMTP_EMAIL=your_email@gmail.com`
    `SMTP_PASSWORD=your_app_password`
5.  **CUDAS Admin (Root User):**
    `CUDAS_ADMIN_EMAIL=admin@cudas.com`
    `CUDAS_ADMIN_PASSWORD=secure_password`

#### Running the Backend
The new database tables for Auth (Users, Colleges, Companies) will be created automatically on startup.
```bash
cd backend/app
uvicorn main:app --reload
```

### 2. Frontend Setup

The frontend is built with React + Vite and features a modern, animated GUI.

```bash
cd Frontend

# Install Dependencies
npm install

# Start Development Server
npm run dev
```

The frontend runs on `localhost:5173` and automatically proxies `/api` requests to the backend at `localhost:8000`.

---

# 📁 Project Structure

"""
project/
│
├── backend/
│   │
│   ├── app/
│   │   │
│   │   ├── main.py
│   │   │
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── database.py
│   │   │
│   │   ├── api/
│   │   │   ├── router.py
│   │   │   │
│   │   │   └── ai/
│   │   │       ├── router.py
│   │   │       │
│   │   │       └── agents/
│   │   │           │
│   │   │           ├── academic/
│   │   │           │   ├── router.py
│   │   │           │   ├── service.py
│   │   │           │   ├── schema.py
│   │   │           │   └── agent.py
│   │   │           │
│   │   │           ├── multilingual/
│   │   │           │   ├── router.py
│   │   │           │   ├── service.py
│   │   │           │   ├── schema.py
│   │   │           │   └── agent.py
│   │   │           │
│   │   │           ├── interview/
│   │   │           │   ├── router.py
│   │   │           │   ├── service.py
│   │   │           │   ├── schema.py
│   │   │           │   └── agent.py
│   │   │           │
│   │   │           └── performance/
│   │   │               ├── router.py
│   │   │               ├── service.py
│   │   │               ├── schema.py
│   │   │               └── agent.py
│   │   │
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   │
│   ├── requirements.txt
│   └── .env
│
└── frontend/   (Optional React / NextJS frontend)
"""
---