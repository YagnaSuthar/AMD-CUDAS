"""
Dedicated Interview Planner (O(1) execution, no LLM calls).
Responsible for:
- Phase progression
- Topic progression
- Project rotation & ranking
- Role roadmap progression
- Structured conversation state
- Metadata-based duplicate prevention
"""
import logging
import re
import random

logger = logging.getLogger(__name__)


def is_duplicate_concept(concept_a: str, concept_b: str) -> bool:
    if not concept_a or not concept_b:
        return False
    a_norm = concept_a.lower().strip()
    b_norm = concept_b.lower().strip()
    
    if a_norm == b_norm or a_norm in b_norm or b_norm in a_norm:
        return True
        
    def clean_concept(c: str) -> str:
        c = c.replace("hash table", "hashmap").replace("hashtable", "hashmap")
        c = c.replace("binary search tree", "bst")
        c = re.sub(r'\b(vs|and|or|the|a|of|difference|between|comparison|overview|design|basics|principles|reasoning|question)\b', '', c)
        return c
        
    a_clean = clean_concept(a_norm)
    b_clean = clean_concept(b_norm)
    
    a_words = set(w for w in re.findall(r'\b\w{3,}\b', a_clean))
    b_words = set(w for w in re.findall(r'\b\w{3,}\b', b_clean))
    
    if len(a_words.intersection(b_words)) >= 2:
        return True
        
    return False

# Role-specific roadmap definitions (exactly 12 high-quality topics per mode)
ROADMAPS = {
    "frontend": [
        "JavaScript ES6", "Closures", "Asynchronous JavaScript", "DOM & Virtual DOM",
        "React Components", "React Hooks", "State Management", "Performance Optimization",
        "API Integration", "Routing & Authentication", "Build Tools & Deployment", "Frontend Architecture"
    ],
    "backend": [
        "HTTP & REST", "Authentication", "Database Design", "SQL vs NoSQL",
        "Caching", "Transactions", "Concurrency", "Queues & Background Jobs",
        "Scalability", "Load Balancing", "Docker & Deployment", "Monitoring & Logging"
    ],
    "mern": [
        "Node.js Event Loop", "Express Middleware", "REST API Design", "MongoDB Schema Design",
        "Mongoose Relationships & Populate", "JWT Authentication & Authorization", "React Components & Props", "React Hooks & State Management",
        "Performance Optimization", "Security (CORS, XSS, CSRF, Validation)", "Deployment (Docker, Nginx, Cloud)", "Full-Stack Architecture & API Integration"
    ],
    "fullstack": [
        "Node.js Event Loop", "Express Middleware", "REST API Design", "MongoDB Schema Design",
        "Mongoose Relationships & Populate", "JWT Authentication & Authorization", "React Components & Props", "React Hooks & State Management",
        "Performance Optimization", "Security (CORS, XSS, CSRF, Validation)", "Deployment (Docker, Nginx, Cloud)", "Full-Stack Architecture & API Integration"
    ],
    "ai": [
        "Python", "Deep Learning", "PyTorch / TensorFlow", "Transformers",
        "LLMs", "RAG", "Vector Databases", "Prompt Engineering",
        "Inference Optimization", "Model Deployment", "Monitoring", "Production AI Systems"
    ],
    "ml_ai": [
        "Python", "Deep Learning", "PyTorch / TensorFlow", "Transformers",
        "LLMs", "RAG", "Vector Databases", "Prompt Engineering",
        "Inference Optimization", "Model Deployment", "Monitoring", "Production AI Systems"
    ],
    "data_science": [
        "Python", "Pandas", "NumPy", "Statistics",
        "Feature Engineering", "Machine Learning", "Model Evaluation", "Overfitting",
        "Deployment", "Optimization", "MLOps", "End-to-End Pipeline"
    ],
    "datascience": [
        "Python", "Pandas", "NumPy", "Statistics",
        "Feature Engineering", "Machine Learning", "Model Evaluation", "Overfitting",
        "Deployment", "Optimization", "MLOps", "End-to-End Pipeline"
    ],
    "python": [
        "Python Data Types", "Decorators", "Generators", "Context Managers",
        "Asyncio", "FastAPI", "SQLAlchemy", "PostgreSQL",
        "JWT", "Logging & Exception Handling", "Testing & Deployment", "Performance Optimization"
    ],
    "java": [
        "OOP", "Collections", "Exception Handling", "Multithreading",
        "JVM", "Spring Boot", "JPA / Hibernate", "REST APIs",
        "SQL", "Security", "Deployment", "Performance"
    ],
    "cybersecurity": [
        "CIA Triad", "Authentication", "Authorization", "Encryption",
        "Network Security", "OWASP", "Threat Modeling", "Incident Response",
        "Secure Coding", "Vulnerability Assessment", "Monitoring", "Security Architecture"
    ],
    "devops": [
        "Linux", "Networking", "Docker", "Kubernetes",
        "CI/CD", "Terraform", "Cloud", "Monitoring",
        "Logging", "Security", "Scaling", "Production Operations"
    ],
    "cloud": [
        "Cloud Fundamentals", "Compute", "Storage", "Networking",
        "IAM", "Containers", "Serverless", "Monitoring",
        "Cost Optimization", "High Availability", "Security", "Architecture"
    ],
    "data_analyst": [
        "SQL", "Excel", "Data Cleaning", "Data Visualization",
        "Statistics", "Power BI / Tableau", "KPIs", "Business Analysis",
        "Reporting", "Optimization", "Case Study", "Analytics Workflow"
    ]
}

ROLE_TECHS = {
    "frontend": ["javascript", "react", "redux", "html", "css", "es6", "dom", "npm", "webpack", "vite", "nextjs", "tailwind", "vue", "angular", "bootstrap"],
    "backend": ["node", "express", "django", "flask", "fastapi", "postgres", "mysql", "mongodb", "sqlite", "redis", "api", "server", "http", "jwt", "docker", "nginx", "rest", "sql", "nosql"],
    "mern": ["react", "node", "express", "mongodb", "mongoose", "jwt", "docker", "nginx", "javascript", "cors", "xss", "csrf"],
    "fullstack": ["react", "node", "express", "mongodb", "mongoose", "jwt", "docker", "nginx", "javascript", "cors", "xss", "csrf", "postgres", "mysql", "api", "html", "css"],
    "ai": ["python", "pytorch", "tensorflow", "transformers", "llm", "llms", "rag", "vector", "embedding", "embeddings", "openai", "huggingface", "gpu", "cuda", "keras", "scikit-learn", "numpy", "pandas", "opencv"],
    "ml_ai": ["python", "pytorch", "tensorflow", "transformers", "llm", "llms", "rag", "vector", "embedding", "embeddings", "openai", "huggingface", "gpu", "cuda", "keras", "scikit-learn", "numpy", "pandas", "opencv"],
    "data_science": ["python", "pandas", "numpy", "scikit-learn", "sklearn", "matplotlib", "seaborn", "mlops", "tensorflow", "pytorch", "keras", "opencv"],
    "datascience": ["python", "pandas", "numpy", "scikit-learn", "sklearn", "matplotlib", "seaborn", "mlops", "tensorflow", "pytorch", "keras", "opencv"],
    "python": ["python", "django", "flask", "fastapi", "sqlalchemy", "postgresql", "postgres", "jwt", "asyncio", "redis", "docker"],
    "java": ["java", "spring", "spring boot", "jpa", "hibernate", "maven", "gradle", "sql", "rest", "docker"],
    "cybersecurity": ["security", "encryption", "vulnerability", "auth", "jwt", "oauth", "cia", "owasp", "xss", "csrf", "tls", "ssl", "network"],
    "devops": ["linux", "docker", "kubernetes", "k8s", "terraform", "aws", "gcp", "azure", "jenkins", "git", "ci/cd", "monitoring", "logging"],
    "cloud": ["aws", "gcp", "azure", "terraform", "docker", "kubernetes", "serverless", "iam", "vpc", "cloud", "cost"],
    "data_analyst": ["sql", "excel", "pandas", "numpy", "power bi", "tableau", "statistics", "python", "visualization"]
}

def parse_projects(project_summary: str) -> list[dict]:
    """Extract project names and tech stacks from the candidate's resume/profile project summary."""
    projects = []
    tech_words = [
        "fastapi", "react", "mongodb", "django", "postgresql", "flask", "node", "express", 
        "angular", "vue", "mysql", "sqlite", "redis", "nextjs", "bootstrap", "tailwind", 
        "python", "java", "spring", "javascript", "typescript", "html", "css", "docker", 
        "kubernetes", "aws", "gcp", "azure", "pytorch", "tensorflow", "keras", "scikit-learn", 
        "numpy", "pandas", "opencv"
    ]
    
    lines = [line.strip() for line in (project_summary or "").split("\n") if line.strip()]
    for line in lines:
        cleaned = line.lstrip("-*•").strip()
        if not cleaned:
            continue
        
        # Extract title
        title = ""
        for sep in (":", "—", "|", "-"):
            if sep in cleaned:
                parts = cleaned.split(sep, 1)
                cand = parts[0].strip()
                if 1 <= len(cand.split()) <= 4:
                    title = cand
                    break
        if not title:
            words = cleaned.split()
            if len(words) >= 2:
                title = " ".join(words[:2])
            else:
                title = cleaned
        
        title = title.strip('"\'*[]{}')
        
        # Extract techs
        line_lower = cleaned.lower().replace("next.js", "nextjs").replace("node.js", "node")
        techs = []
        for tw in tech_words:
            if tw in line_lower:
                techs.append(tw)
        
        projects.append({
            "name": title,
            "techs": list(set(techs)),
            "description": cleaned
        })
    
    return projects

def rank_projects(projects: list[dict], job_role: str = "") -> list[dict]:
    """
    Rank projects using lightweight heuristics only:
    - Resume order (primary weight)
    - Technology diversity (number of verified technologies)
    - Job-description/role relevance (if role-specific interview)
    - Recency (if available in description)
    Do NOT use project description length as a ranking signal.
    """
    ranked = []
    job_role = (job_role or "").lower()
    role_keywords = ROLE_TECHS.get(job_role, [])
        
    for idx, p in enumerate(projects):
        # 1. Resume order (first has highest priority, subtracting 20 points for each step)
        order_score = max(100 - idx * 20, 0)
        
        # 2. Technology diversity (number of verified technologies in tech stack)
        tech_score = len(p.get("techs", [])) * 10
        
        # 3. Job-description/role relevance
        relevance_score = 0
        if role_keywords:
            relevance_score = sum(15 for t in p.get("techs", []) if t.lower() in role_keywords)
            desc_lower = p.get("description", "").lower()
            for kw in role_keywords:
                if kw in desc_lower:
                    relevance_score += 5
                    
        # 4. Recency (if available in description, e.g. year)
        recency_score = 0
        desc = p.get("description", "")
        years = re.findall(r'\b(20\d{2})\b', desc)
        if years:
            max_year = max(int(y) for y in years)
            recency_score = (max_year - 2020) * 10
            
        total_score = order_score + tech_score + relevance_score + recency_score
        ranked.append((total_score, p))
        
    ranked.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in ranked]

class InterviewPlanner:
    @staticmethod
    def get_next_plan(
        question_number: int,
        mode: str,
        history_metadata: list[dict],
        resume_project_summary: str,
        resume_has_projects: bool,
        answer_quality: str = "",
        topic_depth: int = 0,
        skills: list[str] | str = "",
        phase: str = "",
        job_description: str = "",
    ) -> dict:
        """
        Deterministically determine the next question plan in O(1) without LLM calls.
        Reconstructs and utilizes a structured conversation state dynamically.
        """
        mode = (mode or "").strip().lower() or "basic"
        
        # Parse projects
        raw_projects = parse_projects(resume_project_summary) if resume_has_projects else []
        # Filter projects to remove any default General Project
        raw_projects = [p for p in raw_projects if p["name"] != "General Project"]
        has_projects = len(raw_projects) > 0 and resume_has_projects
        
        # Rank projects using heuristics
        projects = rank_projects(raw_projects, mode) if has_projects else []
        
        # Parse skills
        if isinstance(skills, str):
            skills_list = [s.strip() for s in skills.split(",") if s.strip()]
        elif isinstance(skills, list):
            skills_list = [str(s).strip() for s in skills if str(s).strip()]
        else:
            skills_list = []
            
        # Reconstruct Conversation State
        asked_topics = []
        asked_concepts = []
        asked_projects = []
        mentioned_technologies = []
        
        current_phase = phase or ("resume" if mode == "basic" else "resume")
        current_project = ""
        current_subject = ""
        current_concept = ""
        
        for turn in history_metadata:
            topic = turn.get("topic", "")
            concept = turn.get("concept", "")
            proj = turn.get("project", "")
            tech = turn.get("technology", "")
            ph = turn.get("phase", "")
            
            if topic and topic not in asked_topics:
                asked_topics.append(topic)
            if concept and concept not in asked_concepts:
                asked_concepts.append(concept)
            if proj and proj not in asked_projects:
                asked_projects.append(proj)
            if tech and tech not in mentioned_technologies:
                mentioned_technologies.append(tech)
                
            if ph:
                current_phase = ph
            if proj:
                current_project = proj
            if topic:
                current_subject = topic
            if concept:
                current_concept = concept
                
        # If no projects exist, we still keep current_phase as resume for the first 5 questions
        # but we rely on skills and tech stack.
            
        state = {
            "current_phase": current_phase,
            "current_project": current_project,
            "current_subject": current_subject,
            "current_concept": current_concept,
            "asked_topics": asked_topics,
            "asked_concepts": asked_concepts,
            "asked_projects": asked_projects,
            "mentioned_technologies": mentioned_technologies,
            "question_number": question_number
        }
        
        if mode == "basic":
            plan = InterviewPlanner._get_basic_plan(state, projects, skills_list, has_projects, history_metadata)
        else:
            plan = InterviewPlanner._get_role_plan(state, mode, projects, skills_list, has_projects)
            
        return validate_plan(plan)

    @staticmethod
    def _get_basic_plan(
        state: dict,
        projects: list[dict],
        skills_list: list[str],
        has_projects: bool,
        history_metadata: list[dict]
    ) -> dict:
        phase = state["current_phase"]
        q_num = state["question_number"]
        
        # Determine difficulty 3-tier
        if 1 <= q_num <= 6:
            difficulty = "easy"
        elif 7 <= q_num <= 13:
            difficulty = "medium"
        else:
            difficulty = "hard"

        # We no longer fail over to core early. Q1-Q5 MUST be resume phase.

        # Q1–Q5: Resume Phase
        if 1 <= q_num <= 5:
            if has_projects and projects:
                # Dynamically choose a project, picking randomly to ensure rotation
                # but weighted by ranking is fine, or just shuffle. 
                # To be deterministic but varied, use a hash of question_number + len(projects)
                target_proj = projects[(q_num * 7) % len(projects)]
                proj_name = target_proj["name"]
                proj_techs = target_proj["techs"]
                proj_tech = proj_techs[0] if proj_techs else "general"
            else:
                proj_name = "Skills & Tech Stack"
                proj_tech = skills_list[0] if skills_list else "general"

            return {
                "phase": "resume",
                "topic": "Resume & Projects",
                "concept": "",
                "project": proj_name,
                "technology": proj_tech,
                "role": "basic",
                "difficulty": difficulty,
                "intent": "concept",
                "question_number": q_num
            }

        # Q6–Q10: Core Subjects
        elif 6 <= q_num <= 10:
            core_topics = ["OS", "Computer_Networks", "DBMS"]
            # Grouping: Q6-Q7 -> OS, Q8-Q9 -> Networks, Q10 -> DBMS
            idx = (q_num - 6) // 2
            if idx >= len(core_topics): idx = len(core_topics) - 1
            topic = core_topics[idx]
            return {
                "phase": "core",
                "topic": topic,
                "concept": "",
                "project": "",
                "technology": "",
                "role": "basic",
                "difficulty": difficulty,
                "intent": "concept",
                "question_number": q_num
            }

        # Q11–Q15: Problem Solving / System Design
        elif 11 <= q_num <= 15:
            adv_topics = ["OOP", "Software_Engineering", "System_Design_Basics"]
            # Grouping: Q11-Q12 -> OOP, Q13-Q14 -> SE, Q15 -> System Design
            idx = (q_num - 11) // 2
            if idx >= len(adv_topics): idx = len(adv_topics) - 1
            topic = adv_topics[idx]
            return {
                "phase": "problem_solving",
                "topic": topic,
                "concept": "",
                "project": "",
                "technology": "",
                "role": "basic",
                "difficulty": difficulty,
                "intent": "concept",
                "question_number": q_num
            }

        # Q16–Q20: Behavioral ending
        else:
            return {
                "phase": "behavioral",
                "topic": "Behavioral",
                "concept": "",
                "project": "",
                "technology": "",
                "role": "basic",
                "difficulty": difficulty,
                "intent": "concept",
                "question_number": q_num
            }

    @staticmethod
    def _get_role_plan(
        state: dict,
        mode: str,
        projects: list[dict],
        skills_list: list[str],
        has_projects: bool
    ) -> dict:
        q_num = state["question_number"]
        mode = (mode or "").strip().lower()
        
        # Normalize synonyms
        if mode == "datascience":
            mode = "data_science"
        elif mode == "ai":
            mode = "ml_ai"
            
        # Q1: Exactly ONE personalized resume/project question
        if q_num == 1:
            if has_projects and projects:
                target_proj = projects[0]
                proj_name = target_proj["name"]
                proj_techs = target_proj["techs"]
                proj_tech = proj_techs[0] if proj_techs else "general"
            else:
                proj_name = "Skills & Tech Stack"
                proj_tech = skills_list[0] if skills_list else "general"
                
            return {
                "phase": "resume",
                "topic": "Resume & Projects",
                "concept": "",
                "project": proj_name,
                "technology": proj_tech,
                "role": mode,
                "difficulty": "easy",
                "intent": "concept",
                "question_number": 1
            }

        # Q2–Q13: Role Knowledge Phase (Strictly follow the roadmap topics)
        elif 2 <= q_num <= 13:
            if q_num <= 5:
                difficulty = "easy"
            elif 6 <= q_num <= 9:
                difficulty = "medium"
            else:
                difficulty = "hard"
                
            roadmap = ROADMAPS.get(mode, [])
            asked_concepts = state.get("asked_concepts", [])
            asked_topics = state.get("asked_topics", [])
            
            def is_duplicate_of_history(topic: str) -> bool:
                for ac in asked_concepts:
                    if is_duplicate_concept(topic, ac):
                        return True
                for at in asked_topics:
                    if is_duplicate_concept(topic, at):
                        return True
                return False
                
            # Find the first topic in the roadmap that is not a duplicate of history
            chosen_topic = None
            for t in roadmap:
                if not is_duplicate_of_history(t):
                    chosen_topic = t
                    break
                    
            # Fallback if all topics are duplicates (very rare), pick the one matching the current turn index
            if not chosen_topic:
                if roadmap:
                    chosen_topic = roadmap[(q_num - 2) % len(roadmap)]
                else:
                    chosen_topic = "General Concepts"
                    
            return {
                "phase": "core",
                "topic": chosen_topic,
                "concept": chosen_topic,
                "project": "",
                "technology": "",
                "role": mode,
                "difficulty": difficulty,
                "intent": "concept",
                "question_number": q_num
            }

        # Q14: Scenario
        elif q_num == 14:
            scenarios = {
                "mern": "Debugging a slow MERN application after deployment",
                "frontend": "Resolving performance bottlenecks in a complex React/JavaScript application",
                "backend": "Handling database connection spikes and API latency issues under high load",
                "python": "Debugging a memory leak or CPU spike in a production FastAPI or Django application",
                "java": "Analyzing and resolving thread deadlocks or JVM OutOfMemoryError in production",
                "data_analyst": "Handling contradictory data sources or massive clean-up challenges before reporting",
                "data_science": "Dealing with concept drift or high variance in a deployed model in production",
                "ml_ai": "Optimizing latency for LLM inference or handling vector database scaling issues",
                "devops": "Recovering from a failing CI/CD deployment or secret leak in production",
                "cloud": "Diagnosing cloud service outage or unexpected monthly cost overrun",
                "cybersecurity": "Responding to a suspected security breach or zero-day vulnerability in the system"
            }
            scenario_concept = scenarios.get(mode, "Technical Scenario Analysis")
            return {
                "phase": "core",
                "topic": "Scenario",
                "concept": scenario_concept,
                "project": "",
                "technology": "",
                "role": mode,
                "difficulty": "hard",
                "intent": "concept",
                "question_number": q_num
            }

        # Q15: Behavioral
        else:
            return {
                "phase": "behavioral",
                "topic": "Behavioral",
                "concept": "",
                "project": "",
                "technology": "",
                "role": mode,
                "difficulty": "medium",
                "intent": "concept",
                "question_number": q_num
            }


def validate_plan(plan: dict | None) -> dict:
    """Validate and normalize planner output to prevent malformed prompts or NoneType exceptions."""
    default_plan = {
        "phase": "core",
        "topic": "general",
        "concept": "general_concept",
        "project": "",
        "technology": "",
        "role": "basic",
        "question_number": 1,
        "difficulty": "medium",
        "intent": "concept"
    }
    if not plan or not isinstance(plan, dict):
        logger.error("[PLANNER VALIDATION] Plan is None or not a dict. Falling back to default plan.")
        return default_plan

    validated = {}
    required_fields = ["phase", "topic", "concept", "project", "technology", "role", "difficulty", "intent"]
    
    for f in required_fields:
        val = plan.get(f, "")
        if val is None:
            val = ""
        validated[f] = str(val).strip()
        
    validated["question_number"] = int(plan.get("question_number", 1))
    
    if not validated["phase"]:
        validated["phase"] = "core"
    if not validated["topic"]:
        validated["topic"] = "general"
    if not validated["role"]:
        validated["role"] = "basic"
    if not validated["difficulty"]:
        validated["difficulty"] = "medium"
        
    return validated
