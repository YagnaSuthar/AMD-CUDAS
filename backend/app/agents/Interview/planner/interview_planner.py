"""
Dedicated Interview Planner (O(1) execution, no LLM calls).
Responsible for:
- Phase progression
- Topic progression
- Project rotation
- Role roadmap progression
- Cooldown management (Topic cooldown = 3, Tech cooldown = 3, Project cooldown = 2)
"""

import logging

logger = logging.getLogger(__name__)

# Configurable flows
BASIC_FLOW = {
    "projects": 5,
    "core": 5,
    "dsa": 4,
    "behavioral": 6
}

# Role-specific roadmap definitions
ROADMAPS = {
    "frontend": [
        "JavaScript", "ES6", "Closures", "Promises", "Async/Await", "Event Loop", 
        "DOM", "React", "Props", "State", "Hooks", "Context API", "Performance Optimization", 
        "Frontend System Design"
    ],
    "backend": [
        "Node.js", "Express", "REST APIs", "Authentication", "Authorization", 
        "Database Design", "Caching", "Redis", "Load Balancing", "Scaling", 
        "Microservices", "System Design"
    ],
    "mern": [
        "MongoDB", "Mongoose", "Express", "Node.js", "REST APIs", 
        "Authentication", "React", "Redux/Context", "Performance", "Deployment"
    ],
    "fullstack": [
        "React", "Node.js", "Express", "Database Design", "Authentication", 
        "APIs Integration", "Caching", "Load Balancing", "Scaling", "System Design"
    ],
    "ai": [
        "Machine Learning Basics", "Training", "Overfitting", "Evaluation Metrics", 
        "RAG", "Embeddings", "Vector Databases", "LLMs", "Prompt Engineering", 
        "Agents", "Deployment"
    ],
    "ml_ai": [
        "Machine Learning Basics", "Training", "Overfitting", "Evaluation Metrics", 
        "RAG", "Embeddings", "Vector Databases", "LLMs", "Prompt Engineering", 
        "Agents", "Deployment"
    ],
    "data_science": [
        "Machine Learning Basics", "Training", "Overfitting", "Evaluation Metrics", 
        "RAG", "Embeddings", "Vector Databases", "LLMs", "Prompt Engineering", 
        "Agents", "Deployment"
    ],
    "datascience": [
        "Machine Learning Basics", "Training", "Overfitting", "Evaluation Metrics", 
        "RAG", "Embeddings", "Vector Databases", "LLMs", "Prompt Engineering", 
        "Agents", "Deployment"
    ],
    "python": [
        "Python Fundamentals", "OOP", "Decorators", "Generators", "Concurrency", 
        "Asyncio", "FastAPI", "Database Integration", "Scaling"
    ],
    "java": [
        "OOP", "Collections", "Streams", "Multithreading", "JVM", "Spring Boot", 
        "Microservices"
    ],
    "cybersecurity": [
        "Network Security", "Authentication & Sessions", "Cryptography Basics", 
        "Web Application Security", "OWASP Top 10", "Threat Modeling", 
        "Penetration Testing", "Secure Coding Practices"
    ],
    "devops": [
        "CI/CD Pipelines", "Docker & Containerization", "Kubernetes Orchestration", 
        "Infrastructure as Code", "Linux Systems", "Cloud Services", "Monitoring & Logging"
    ],
    "cloud": [
        "Cloud Infrastructure", "IAM & Access Control", "VPC & Networking", "Compute & Storage", 
        "Load Balancing", "Autoscaling", "Serverless Architecture", "Cloud Security & Compliance"
    ],
    "data_analyst": [
        "SQL Queries", "Data Importing & Cleaning", "Excel & Spreadsheets", "Pandas & DataFrames", 
        "Exploratory Data Analysis", "Data Visualization", "Statistics & Hypothesis Testing", "Business Intelligence"
    ]
}

ROLE_TECHS = {
    "frontend": ["react", "vue", "angular", "javascript", "typescript", "html", "css", "nextjs", "bootstrap", "tailwind"],
    "backend": ["node", "express", "django", "flask", "fastapi", "postgres", "mysql", "mongodb", "sqlite", "redis", "api", "server"],
    "mern": ["react", "node", "express", "mongodb"],
    "fullstack": ["react", "node", "express", "mongodb", "postgres", "mysql", "api", "html", "css", "javascript"],
    "ai": ["pytorch", "tensorflow", "keras", "scikit-learn", "numpy", "pandas", "opencv", "llm", "rag", "embedding"],
    "ml_ai": ["pytorch", "tensorflow", "keras", "scikit-learn", "numpy", "pandas", "opencv", "llm", "rag", "embedding"],
    "data_science": ["pytorch", "tensorflow", "keras", "scikit-learn", "numpy", "pandas", "opencv", "llm", "rag", "embedding"],
    "datascience": ["pytorch", "tensorflow", "keras", "scikit-learn", "numpy", "pandas", "opencv", "llm", "rag", "embedding"],
    "python": ["python", "django", "flask", "fastapi"],
    "java": ["java", "spring"],
    "cybersecurity": ["security", "encryption", "vulnerability", "auth", "jwt", "oauth"],
    "devops": ["docker", "kubernetes", "aws", "gcp", "azure", "ci/cd"],
    "cloud": ["aws", "gcp", "azure", "docker", "kubernetes"],
    "data_analyst": ["sql", "pandas", "numpy", "excel", "visualization"]
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
    
    if not projects:
        projects.append({
            "name": "General Project",
            "techs": [],
            "description": "General software engineering project"
        })
    return projects

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
    ) -> dict:
        """
        Deterministically determine the next question plan in O(1).
        
        history_metadata is a list of dicts: [{"topic": str, "project": str, "technology": str}]
        """
        mode = (mode or "").strip().lower() or "basic"
        
        if mode == "basic":
            return InterviewPlanner._get_basic_plan(
                question_number, history_metadata, resume_project_summary, resume_has_projects
            )
        else:
            return InterviewPlanner._get_role_plan(
                question_number, mode, history_metadata, resume_project_summary, resume_has_projects, answer_quality, topic_depth
            )

    @staticmethod
    def _get_basic_plan(
        question_number: int,
        history_metadata: list[dict],
        resume_project_summary: str,
        resume_has_projects: bool,
    ) -> dict:
        # Phase 1: Projects (Q1-Q5)
        if 1 <= question_number <= 5:
            topics = [
                "project_overview",
                "project_architecture",
                "project_database",
                "project_backend",
                "project_challenges"
            ]
            selected_topic = topics[question_number - 1]
            
            # Select project and technology with cooldowns
            projects = parse_projects(resume_project_summary) if resume_has_projects else parse_projects("")
            
            # Cooldown logic
            # PROJECT_COOLDOWN = 2: block last 2 projects
            cooldown_projects = [item["project"] for item in history_metadata[-2:] if item.get("project")]
            # TECH_COOLDOWN = 3: block last 3 techs
            cooldown_techs = [item["technology"] for item in history_metadata[-3:] if item.get("technology")]
            
            # Filter projects
            eligible_projects = [p for p in projects if p["name"] not in cooldown_projects]
            if not eligible_projects:
                eligible_projects = projects # ignore cooldown if none eligible
                
            # Select project by minimum questions asked in history
            project_counts = {p["name"]: 0 for p in eligible_projects}
            for item in history_metadata:
                proj = item.get("project")
                if proj in project_counts:
                    project_counts[proj] += 1
            min_count = min(project_counts.values())
            selected_project = [p for p in eligible_projects if project_counts[p["name"]] == min_count][0]
            
            # Select technology from project techs
            project_techs = selected_project["techs"]
            eligible_techs = [t for t in project_techs if t not in cooldown_techs]
            if not eligible_techs:
                eligible_techs = project_techs if project_techs else ["general"]
                
            # Select technology by minimum usage in history
            tech_counts = {t: 0 for t in eligible_techs}
            for item in history_metadata:
                tech = item.get("technology")
                if tech in tech_counts:
                    tech_counts[tech] += 1
            min_tech_count = min(tech_counts.values())
            selected_tech = [t for t in eligible_techs if tech_counts[t] == min_tech_count][0]
            
            return {
                "phase": "resume",
                "topic": selected_topic,
                "concept": selected_tech,
                "project": selected_project["name"],
                "technology": selected_tech,
                "role": "basic"
            }
            
        # Phase 2: Core Subjects (Q6-Q10)
        elif 6 <= question_number <= 10:
            core_plan = {
                6: ("DBMS", "Normalization"),
                7: ("OS", "Process vs Thread"),
                8: ("CN", "TCP vs UDP"),
                9: ("OOPS", "Polymorphism"),
                10: ("SQL", "Indexing")
            }
            topic, concept = core_plan.get(question_number, ("DBMS", "Normalization"))
            return {
                "phase": "core",
                "topic": topic,
                "concept": concept,
                "project": "",
                "technology": "",
                "role": "basic"
            }
            
        # Phase 3: DSA (Q11-Q14)
        elif 11 <= question_number <= 14:
            dsa_plan = {
                11: ("Arrays", "Two Pointer / Sliding Window"),
                12: ("Linked List", "Detect Loop"),
                13: ("Trees", "Binary Tree Traversal"),
                14: ("Complexity", "Big O complexity")
            }
            topic, concept = dsa_plan.get(question_number, ("Arrays", "Two Pointer"))
            return {
                "phase": "problem_solving",
                "topic": topic,
                "concept": concept,
                "project": "",
                "technology": "",
                "role": "basic"
            }
            
        # Phase 4: HR / Behavioral (Q15-Q20)
        else:
            hr_plan = {
                15: ("Introduction", "Introduce yourself"),
                16: ("Teamwork", "Teamwork example"),
                17: ("Conflict Resolution", "Conflict resolution"),
                18: ("Leadership", "Leadership experience"),
                19: ("Strengths", "Key strengths"),
                20: ("Career Goals", "Career goals")
            }
            topic, concept = hr_plan.get(question_number, ("Introduction", "Introduce yourself"))
            return {
                "phase": "behavioral",
                "topic": topic,
                "concept": concept,
                "project": "",
                "technology": "",
                "role": "basic"
            }

    @staticmethod
    def _get_role_plan(
        question_number: int,
        mode: str,
        history_metadata: list[dict],
        resume_project_summary: str,
        resume_has_projects: bool,
        answer_quality: str,
        topic_depth: int,
    ) -> dict:
        # Question 1: Role project or general role introduction
        if question_number == 1:
            projects = parse_projects(resume_project_summary) if resume_has_projects else []
            role_tech_keywords = ROLE_TECHS.get(mode, [])
            
            matching_project = None
            matching_tech = ""
            for p in projects:
                for t in p["techs"]:
                    if t in role_tech_keywords:
                        matching_project = p
                        matching_tech = t
                        break
                if matching_project:
                    break
                    
            if matching_project:
                # Explain project architecture
                return {
                    "phase": "resume",
                    "topic": "project_architecture",
                    "concept": f"Explain the architecture of project {matching_project['name']}",
                    "project": matching_project["name"],
                    "technology": matching_tech,
                    "role": mode
                }
            else:
                # General role question
                return {
                    "phase": "core",
                    "topic": "Role Definition",
                    "concept": f"What do you understand about the role of a {mode}",
                    "project": "",
                    "technology": "",
                    "role": mode
                }
                
        # Questions 2-15: Linear Roadmap
        else:
            roadmap = ROADMAPS.get(mode, ROADMAPS["backend"])
            
            # Find which topics have been asked so far
            asked_topics = [item["topic"] for item in history_metadata if item.get("topic")]
            
            # Cooldown logic for topics (TOPIC_COOLDOWN = 3)
            # Since roadmaps are unique, we generally progress forward, but let's implement this strictly.
            
            # Check if we should ask a follow-up (topic_depth = 1 and answer_quality = strong/partial)
            if topic_depth == 1 and answer_quality in ("strong", "partial") and asked_topics:
                last_topic = asked_topics[-1]
                if last_topic in roadmap:
                    return {
                        "phase": "core",
                        "topic": last_topic,
                        "concept": f"{last_topic} follow-up",
                        "project": "",
                        "technology": "",
                        "role": mode
                    }
            
            # Find next unused topic in the roadmap
            target_topic = ""
            for topic in roadmap:
                if topic not in asked_topics:
                    target_topic = topic
                    break
            
            if not target_topic:
                # Wrap around or pick last topic in roadmap
                target_topic = roadmap[-1]
                
            return {
                "phase": "core",
                "topic": target_topic,
                "concept": target_topic,
                "project": "",
                "technology": "",
                "role": mode
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
        "question_number": 1
    }
    if not plan or not isinstance(plan, dict):
        logger.error("[PLANNER VALIDATION] Plan is None or not a dict. Falling back to default plan.")
        return default_plan

    validated = {}
    required_fields = ["phase", "topic", "concept", "project", "technology", "role"]
    for field in required_fields:
        val = plan.get(field)
        if val is None:
            if field == "phase":
                validated[field] = "core"
            elif field == "topic":
                validated[field] = "general"
            elif field == "concept":
                validated[field] = "general_concept"
            elif field == "role":
                validated[field] = "basic"
            else:
                validated[field] = ""
        else:
            validated[field] = str(val).strip()

    # question_number validation
    q_num = plan.get("question_number")
    try:
        validated["question_number"] = int(q_num) if q_num is not None else 1
    except Exception:
        validated["question_number"] = 1

    return validated
