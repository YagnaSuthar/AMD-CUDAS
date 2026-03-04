# 🚀 CUDAS – AI Powered Academic & Career Development System

CUDAS is a **Full Stack AI Platform** designed to assist students with **academic planning, interview preparation, career guidance, and multilingual support**.

The platform integrates **multiple specialized AI agents** powered by **FastAPI, PostgreSQL, React, and Groq LLM** to deliver personalized academic and career insights.

### 🌟 Key Highlights

* 🤖 Modular AI Agent Architecture
* 🎤 AI Mock Interview System
* 📚 Personalized Academic Planning
* 🧭 Career Guidance & Skill Analysis
* 🎓 Course Recommendation Engine
* 🌍 Multilingual AI Support

---

# 👨‍💻 Project Team

### 🚀 Leader

**Dhrumil Kharadi**

### 👥 Members

• **Nirja Patel**
• **Yagna Suthar**

---

# 🤖 AI Agents

• 🎤 **AI Interview Conductor Agent** – Conducts AI-based interviews and generates structured performance evaluations.

• 📚 **Academic Planner Agent** – Analyzes academic data to create personalized study plans and performance insights.

• 🧭 **Career Advisor Agent** – Identifies skill gaps and provides tailored career roadmaps.

• 🎓 **Course Recommendation Agent** – Recommends personalized courses aligned with interests and career goals.

• 🌍 **Multilingual Voice Assistant Agent** – Delivers voice-enabled multilingual academic and career support.

---
---

# 🏗 System Architecture

CUDAS follows a **modular AI agent architecture** where each agent performs a specific task while communicating through the FastAPI backend.

```
User
 │
 ▼
Frontend (React / Vite)
 │
 ▼
FastAPI Backend
 │
 ▼
AI Agent Router
 │
 ├── Academic Planner Agent
 ├── AI Interview Conductor Agent
 ├── Career Advisor Agent
 ├── Course Recommendation Agent
 └── Multilingual Voice Assistant Agent
 │
 ▼
Groq LLM API
 │
 ▼
PostgreSQL Database
```

This architecture ensures:

• Clean modular design
• Easy scalability for new AI agents
• Efficient AI processing
• Maintainable backend structure

---

# 📁 Project Structure

```
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
│   │   │   ├── database.py
│   │   │   ├── security.py
│   │   │   └── dependencies.py
│   │   │
│   │   ├── api/
│   │   │   ├── router.py
│   │   │   │
│   │   │   └── ai/
│   │   │       ├── router.py
│   │   │       │
│   │   │       └── agents/
│   │   │           ├── academic/
│   │   │           ├── multilingual/
│   │   │           ├── interview/
│   │   │           └── performance/
│   │   │
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   │
│   ├── requirements.txt
│   └── .env
│
└── frontend/
    ├── src/
    ├── public/
    └── package.json
```

---

# ⚙️ Backend Setup

### 1️⃣ Navigate to Backend

```
cd backend
```

### 2️⃣ Create Virtual Environment

```
python -m venv venv
```

Activate the environment:

Windows

```
venv\Scripts\activate
```

Mac/Linux

```
source venv/bin/activate
```

---

### 3️⃣ Install Dependencies

```
pip install -r requirements.txt
```

---

# 🗄 Database Setup

CUDAS uses **PostgreSQL** as the primary database.

Create a database:

```
cudas
```

Example database connection:

```
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/cudas
```

---

# 🔐 Environment Variables

Create a `.env` file inside:

```
backend/app/
```

Example configuration:

```
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/cudas

GROQ_API_KEY=your_groq_api_key

JWT_SECRET_KEY=your_secret_key
JWT_REFRESH_SECRET=your_refresh_secret

SMTP_EMAIL=your_email@gmail.com
SMTP_PASSWORD=your_app_password

CUDAS_ADMIN_EMAIL=admin@cudas.com
CUDAS_ADMIN_PASSWORD=secure_password
```

---

# ▶️ Run Backend Server

```
cd backend/app

uvicorn main:app --reload
```

Backend will run on:

```
http://localhost:8000
```

API documentation:

```
http://localhost:8000/docs
```

---

# 🎨 Frontend Setup

Navigate to frontend directory:

```
cd frontend
```

Install dependencies:

```
npm install
```

Run development server:

```
npm run dev
```

Frontend will run on:

```
http://localhost:5173
```

---

# 🛠 Tech Stack

### Backend

• FastAPI
• PostgreSQL
• SQLAlchemy
• AsyncPG
• JWT Authentication

### AI Integration

• Groq LLM API

### Frontend

• React
• Vite
• TailwindCSS

---

# 🚀 Future Improvements

• Docker containerization
• Vector database for RAG
• AI memory system
• Voice-based interaction
• Real-time AI analytics

---

# ⭐ Support

If you like this project:

⭐ Star the repository
⭐ Contribute improvements
⭐ Share feedback
