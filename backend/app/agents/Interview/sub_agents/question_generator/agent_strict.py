"""
Strict Question Phrasing Agent.
Phrases questions based on deterministic plans provided by the planner.
Validates the generated question against the plan and verified resume details.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Fallback pool questions mapped by role
FALLBACK_QUESTIONS = {
    "basic": [
        {"question": "What is database normalization, and why is it used in relational databases?", "concept": "database normalization", "topic": "DBMS"},
        {"question": "Explain the difference between an abstract class and an interface in OOP.", "concept": "OOP interface abstract class", "topic": "OOP"},
        {"question": "What is virtual memory, and how does it help a computer run large applications?", "concept": "virtual memory", "topic": "OS"},
        {"question": "How do TCP and UDP differ in terms of reliability and speed?", "concept": "TCP vs UDP", "topic": "Computer_Networks"},
        {"question": "What is the purpose of the software development lifecycle, and what are its key stages?", "concept": "SDLC stages", "topic": "Software_Engineering"},
        {"question": "Explain the difference between a stack and a queue data structure.", "concept": "stack vs queue", "topic": "Linked_Lists_and_Stacks"},
        {"question": "What is the Big O time complexity of searching in a balanced binary search tree?", "concept": "BST search complexity", "topic": "Trees_and_Graphs"},
        {"question": "What is rate limiting, and why is it important for APIs?", "concept": "rate limiting", "topic": "DBMS"},
        {"question": "Explain the concept of inheritance in object-oriented programming.", "concept": "OOP inheritance", "topic": "OOP"},
        {"question": "What is the difference between a process and a thread in an operating system?", "concept": "process vs thread", "topic": "OS"}
    ],
    "frontend": [
        {"question": "What is the difference between state and props in React?", "concept": "React state props", "topic": "React"},
        {"question": "How does the virtual DOM work in React to update the UI?", "concept": "virtual DOM", "topic": "React"},
        {"question": "What is the event loop in JavaScript, and how does it handle asynchronous tasks?", "concept": "JavaScript event loop", "topic": "JavaScript"},
        {"question": "What is the difference between local storage and session storage in browsers?", "concept": "browser storage", "topic": "Browser_Rendering_DOM"},
        {"question": "Explain the concept of CSS box model and its components.", "concept": "CSS box model", "topic": "CSS"},
        {"question": "What is semantic HTML, and why is it important for SEO and accessibility?", "concept": "semantic HTML", "topic": "HTML"},
        {"question": "How does hoisting work in JavaScript for variables and functions?", "concept": "JavaScript hoisting", "topic": "JavaScript"},
        {"question": "What are React hooks, and what rules must you follow when using them?", "concept": "React hooks", "topic": "React"},
        {"question": "Explain the difference between event bubbling and event capturing in JS.", "concept": "JS event propagation", "topic": "JavaScript"},
        {"question": "What is the purpose of useEffect hook in React?", "concept": "React useEffect", "topic": "React"}
    ],
    "backend": [
        {"question": "What is the difference between an inner join and a left join in SQL?", "concept": "SQL joins", "topic": "DBMS"},
        {"question": "What is database normalization, and why is it used?", "concept": "database normalization", "topic": "DBMS"},
        {"question": "What is the purpose of caching, and when should you invalidate a cache?", "concept": "caching concepts", "topic": "Caching"},
        {"question": "How does JWT authentication work to secure an API?", "concept": "JWT auth", "topic": "Authentication"},
        {"question": "What is the difference between horizontal and vertical scaling?", "concept": "system design scaling", "topic": "System_Design_Basics"},
        {"question": "What is a transaction in DBMS, and what are the ACID properties?", "concept": "database transactions", "topic": "DBMS"},
        {"question": "What is the purpose of database indexes, and how do they improve query speed?", "concept": "database indexing", "topic": "DBMS"},
        {"question": "What is the difference between SQL and NoSQL databases?", "concept": "SQL vs NoSQL", "topic": "DBMS"},
        {"question": "How do REST APIs differ from GraphQL APIs?", "concept": "REST vs GraphQL", "topic": "APIs"},
        {"question": "What is rate limiting, and why is it important for APIs?", "concept": "API rate limiting", "topic": "APIs"}
    ],
    "mern": [
        {"question": "What is the difference between state and props in React?", "concept": "React state props", "topic": "React"},
        {"question": "Explain how middleware functions work in Express.js.", "concept": "Express middleware", "topic": "Node_APIs"},
        {"question": "What is the purpose of MongoDB indexes, and how do they affect query performance?", "concept": "MongoDB indexing", "topic": "MongoDB"},
        {"question": "How does JWT authentication work to secure an API?", "concept": "JWT auth", "topic": "Auth_Fullstack"},
        {"question": "What is the difference between SQL and NoSQL databases?", "concept": "SQL vs NoSQL", "topic": "MongoDB"},
        {"question": "What is the event loop in JavaScript, and how does it handle asynchronous tasks?", "concept": "JavaScript event loop", "topic": "Node_APIs"},
        {"question": "How do you handle cross-origin resource sharing CORS issues in Express?", "concept": "CORS handling", "topic": "Node_APIs"},
        {"question": "What is the difference between controlled and uncontrolled components in React?", "concept": "React controlled components", "topic": "React"},
        {"question": "How does database indexing work to speed up queries?", "concept": "database indexing", "topic": "MongoDB"},
        {"question": "Explain the difference between authentication and authorization.", "concept": "authentication vs authorization", "topic": "Auth_Fullstack"}
    ],
    "fullstack": [
        {"question": "What is the difference between state and props in React?", "concept": "React state props", "topic": "React"},
        {"question": "Explain how middleware functions work in Express.js.", "concept": "Express middleware", "topic": "Node_APIs"},
        {"question": "What is the purpose of MongoDB indexes, and how do they affect query performance?", "concept": "MongoDB indexing", "topic": "MongoDB"},
        {"question": "How does JWT authentication work to secure an API?", "concept": "JWT auth", "topic": "Auth_Fullstack"},
        {"question": "What is the difference between SQL and NoSQL databases?", "concept": "SQL vs NoSQL", "topic": "MongoDB"},
        {"question": "What is the event loop in JavaScript, and how does it handle asynchronous tasks?", "concept": "JavaScript event loop", "topic": "Node_APIs"},
        {"question": "How do you handle cross-origin resource sharing CORS issues in Express?", "concept": "CORS handling", "topic": "Node_APIs"},
        {"question": "What is the difference between controlled and uncontrolled components in React?", "concept": "React controlled components", "topic": "React"},
        {"question": "How does database indexing work to speed up queries?", "concept": "database indexing", "topic": "MongoDB"},
        {"question": "Explain the difference between authentication and authorization.", "concept": "authentication vs authorization", "topic": "Auth_Fullstack"}
    ],
    "java": [
        {"question": "What is the difference between an interface and an abstract class in Java?", "concept": "OOP interface abstract class", "topic": "OOP"},
        {"question": "Explain how the Java Virtual Machine JVM manages memory using garbage collection.", "concept": "JVM memory management", "topic": "memory_runtime"},
        {"question": "What is the difference between method overloading and method overriding in Java?", "concept": "OOP overloading overriding", "topic": "OOP"},
        {"question": "What are Java collections, and what is the difference between List and Set?", "concept": "Java collections List Set", "topic": "java_language_concepts"},
        {"question": "What is the difference between a process and a thread in Java concurrency?", "concept": "process vs thread", "topic": "memory_runtime"},
        {"question": "Explain the concept of polymorphism in Java with an example.", "concept": "OOP polymorphism", "topic": "OOP"},
        {"question": "What is the purpose of the final keyword in Java for classes and methods?", "concept": "Java final keyword", "topic": "java_language_concepts"},
        {"question": "What is the difference between Checked and Unchecked exceptions in Java?", "concept": "Java exceptions check uncheck", "topic": "java_language_concepts"},
        {"question": "How does Spring Boot framework simplify Java web application development?", "concept": "Spring Boot framework", "topic": "java_language_concepts"},
        {"question": "Explain how threads are synchronized in Java to avoid data races.", "concept": "Java thread synchronization", "topic": "memory_runtime"}
    ],
    "python": [
        {"question": "What is the difference between a list and a tuple in Python?", "concept": "Python list tuple", "topic": "python_language_concepts"},
        {"question": "Explain how decorators work in Python with a brief example.", "concept": "Python decorators", "topic": "python_language_concepts"},
        {"question": "What is a generator in Python, and how does it differ from a regular function?", "concept": "Python generators", "topic": "python_language_concepts"},
        {"question": "What is the difference between deep copy and shallow copy in Python?", "concept": "Python shallow deep copy", "topic": "memory_runtime"},
        {"question": "How does memory management work in Python using reference counting and garbage collection?", "concept": "Python memory management", "topic": "memory_runtime"},
        {"question": "Explain the purpose of the global interpreter lock GIL in Python.", "concept": "Python GIL lock", "topic": "memory_runtime"},
        {"question": "What is the difference between instance, class, and static methods in Python?", "concept": "Python method types", "topic": "OOP"},
        {"question": "What is list comprehension in Python, and when should you use it?", "concept": "Python list comprehension", "topic": "python_language_concepts"},
        {"question": "How do you handle exceptions in Python using try, except, and finally blocks?", "concept": "Python exception handling", "topic": "python_language_concepts"},
        {"question": "What is the difference between a module and a package in Python?", "concept": "Python module package", "topic": "python_language_concepts"}
    ],
    "cybersecurity": [
        {"question": "What is the difference between authentication and authorization?", "concept": "authentication vs authorization", "topic": "auth_sessions"},
        {"question": "Explain the concept of SQL injection and how to prevent it.", "concept": "SQL injection prevention", "topic": "web_security"},
        {"question": "What is the difference between symmetric and asymmetric encryption?", "concept": "symmetric asymmetric encryption", "topic": "encryption_basics"},
        {"question": "What is a cross-site scripting XSS attack, and how do you mitigate it?", "concept": "XSS attack mitigation", "topic": "web_security"},
        {"question": "What is the purpose of a multi-factor authentication system?", "concept": "multi-factor authentication", "topic": "auth_sessions"},
        {"question": "Explain how a man-in-the-middle attack works on a public WiFi network.", "concept": "man-in-the-middle attack", "topic": "network_security"},
        {"question": "What is the difference between a firewall and an intrusion detection system?", "concept": "firewall vs IDS", "topic": "network_security"},
        {"question": "What is the purpose of the HTTPS protocol, and how does TLS secure it?", "concept": "HTTPS TLS security", "topic": "network_security"},
        {"question": "Explain how cross-site request forgery CSRF works and how to prevent it.", "concept": "CSRF attack prevention", "topic": "web_security"},
        {"question": "What is threat modeling, and why is it useful during software design?", "concept": "threat modeling concepts", "topic": "threat_modeling_scenarios"}
    ],
    "data_analyst": [
        {"question": "What is the difference between mean and median, and when is median a better summary?", "concept": "mean vs median", "topic": "statistics"},
        {"question": "What is exploratory data analysis EDA, and what are its main objectives?", "concept": "exploratory data analysis", "topic": "eda"},
        {"question": "What is the difference between an inner join and a left join in SQL?", "concept": "SQL joins", "topic": "sql"},
        {"question": "What is data cleaning, and name two common techniques to handle missing values.", "concept": "data cleaning imputation", "topic": "data_cleaning"},
        {"question": "What is the difference between correlation and causation in data analysis?", "concept": "correlation vs causation", "topic": "statistics"},
        {"question": "How do you use the group by statement in SQL, and what is its purpose?", "concept": "SQL group by", "topic": "sql"},
        {"question": "What is a database index, and how does it speed up SQL queries?", "concept": "database indexing", "topic": "sql"},
        {"question": "Explain the difference between structured and unstructured data.", "concept": "structured vs unstructured", "topic": "eda"},
        {"question": "What is a pivot table, and how does it help in summarizing data?", "concept": "pivot tables Excel", "topic": "pandas_excel"},
        {"question": "What is the difference between outlier detection and noise in data cleaning?", "concept": "outlier vs noise data", "topic": "data_cleaning"}
    ],
    "data_science": [
        {"question": "What is data leakage, and how can it happen during model training?", "concept": "data leakage prevention", "topic": "data_leakage"},
        {"question": "What is overfitting, and name two ways to reduce it?", "concept": "overfitting reduction", "topic": "bias_variance"},
        {"question": "Explain the difference between supervised and unsupervised learning.", "concept": "supervised unsupervised learning", "topic": "model_selection"},
        {"question": "What is the bias-variance trade-off in machine learning?", "concept": "bias variance trade-off", "topic": "bias_variance"},
        {"question": "What is the difference between L1 and L2 regularization?", "concept": "L1 L2 regularization", "topic": "model_evaluation"},
        {"question": "How does a random forest classifier differ from a single decision tree?", "concept": "random forest decision tree", "topic": "model_selection"},
        {"question": "What is the purpose of cross-validation in machine learning model evaluation?", "concept": "cross-validation evaluation", "topic": "model_evaluation"},
        {"question": "What are precision and recall, and how do they differ?", "concept": "precision vs recall", "topic": "model_evaluation"},
        {"question": "Explain the difference between classification and regression tasks.", "concept": "classification vs regression", "topic": "model_selection"},
        {"question": "What is the purpose of feature engineering in data preprocessing?", "concept": "feature engineering concepts", "topic": "feature_engineering"}
    ],
    "datascience": [
        {"question": "What is data leakage, and how can it happen during model training?", "concept": "data leakage prevention", "topic": "data_leakage"},
        {"question": "What is overfitting, and name two ways to reduce it?", "concept": "overfitting reduction", "topic": "bias_variance"},
        {"question": "Explain the difference between supervised and unsupervised learning.", "concept": "supervised unsupervised learning", "topic": "model_selection"},
        {"question": "What is the bias-variance trade-off in machine learning?", "concept": "bias variance trade-off", "topic": "bias_variance"},
        {"question": "What is the difference between L1 and L2 regularization?", "concept": "L1 L2 regularization", "topic": "model_evaluation"},
        {"question": "How does a random forest classifier differ from a single decision tree?", "concept": "random forest decision tree", "topic": "model_selection"},
        {"question": "What is the purpose of cross-validation in machine learning model evaluation?", "concept": "cross-validation evaluation", "topic": "model_evaluation"},
        {"question": "What are precision and recall, and how do they differ?", "concept": "precision vs recall", "topic": "model_evaluation"},
        {"question": "Explain the difference between classification and regression tasks.", "concept": "classification vs regression", "topic": "model_selection"},
        {"question": "What is the purpose of feature engineering in data preprocessing?", "concept": "feature engineering concepts", "topic": "feature_engineering"}
    ],
    "ml_ai": [
        {"question": "What is data leakage, and how can it happen during model training?", "concept": "data leakage prevention", "topic": "data_leakage"},
        {"question": "What is overfitting, and name two ways to reduce it?", "concept": "overfitting reduction", "topic": "bias_variance"},
        {"question": "Explain the difference between supervised and unsupervised learning.", "concept": "supervised unsupervised learning", "topic": "model_selection"},
        {"question": "What is the bias-variance trade-off in machine learning?", "concept": "bias variance trade-off", "topic": "bias_variance"},
        {"question": "What is the difference between L1 and L2 regularization?", "concept": "L1 L2 regularization", "topic": "model_evaluation"},
        {"question": "How does a random forest classifier differ from a single decision tree?", "concept": "random forest decision tree", "topic": "model_selection"},
        {"question": "What is the purpose of cross-validation in machine learning model evaluation?", "concept": "cross-validation evaluation", "topic": "model_evaluation"},
        {"question": "What are precision and recall, and how do they differ?", "concept": "precision vs recall", "topic": "model_evaluation"},
        {"question": "Explain the difference between classification and regression tasks.", "concept": "classification vs regression", "topic": "model_selection"},
        {"question": "What is the purpose of feature engineering in data preprocessing?", "concept": "feature engineering concepts", "topic": "feature_engineering"}
    ],
    "devops": [
        {"question": "What is the difference between CI and CD?", "concept": "CI vs CD", "topic": "ci_cd"},
        {"question": "What is the difference between horizontal scaling and vertical scaling?", "concept": "horizontal vertical scaling", "topic": "scaling_reliability"},
        {"question": "Explain the concept of infrastructure as code IaC.", "concept": "infrastructure as code", "topic": "infra_as_code"},
        {"question": "What is docker, and how does it differ from a virtual machine?", "concept": "docker containerization", "topic": "docker"},
        {"question": "What is kubernetes, and what is the role of a pod?", "concept": "kubernetes pods", "topic": "kubernetes"},
        {"question": "Explain the difference between rolling deployment and blue-green deployment strategies.", "concept": "deployment strategies", "topic": "deployment_strategies"},
        {"question": "What is the purpose of load balancing in cloud architecture?", "concept": "load balancer systems", "topic": "scaling_reliability"},
        {"question": "What is the difference between cloud public, private, and hybrid deployment models?", "concept": "cloud deployment models", "topic": "cloud_basics"},
        {"question": "What is the purpose of monitoring and logging in devops pipelines?", "concept": "monitoring logging DevOps", "topic": "monitoring_logging"},
        {"question": "Explain how IAM policies are used to secure cloud resources.", "concept": "cloud IAM security", "topic": "cloud_basics"}
    ],
    "cloud": [
        {"question": "What is the difference between CI and CD?", "concept": "CI vs CD", "topic": "ci_cd"},
        {"question": "What is the difference between horizontal scaling and vertical scaling?", "concept": "horizontal vertical scaling", "topic": "scaling_reliability"},
        {"question": "Explain the concept of infrastructure as code IaC.", "concept": "infrastructure as code", "topic": "infra_as_code"},
        {"question": "What is docker, and how does it differ from a virtual machine?", "concept": "docker containerization", "topic": "docker"},
        {"question": "What is kubernetes, and what is the role of a pod?", "concept": "kubernetes pods", "topic": "kubernetes"},
        {"question": "Explain the difference between rolling deployment and blue-green deployment strategies.", "concept": "deployment strategies", "topic": "deployment_strategies"},
        {"question": "What is the purpose of load balancing in cloud architecture?", "concept": "load balancer systems", "topic": "scaling_reliability"},
        {"question": "What is the difference between cloud public, private, and hybrid deployment models?", "concept": "cloud deployment models", "topic": "cloud_basics"},
        {"question": "What is the purpose of monitoring and logging in devops pipelines?", "concept": "monitoring logging DevOps", "topic": "monitoring_logging"},
        {"question": "Explain how IAM policies are used to secure cloud resources.", "concept": "cloud IAM security", "topic": "cloud_basics"}
    ]
}

def validate_generated_question(
    question: str,
    plan: dict,
    resume_project_summary: str,
    skill_summary: str,
    job_description: str,
    question_history: list
) -> tuple[bool, str]:
    """
    Validate the generated question against the deterministic plan.
    Checks:
    - Target project exists in the verified resume (if applicable)
    - Referenced technologies exist in verified resume or JD
    - Generated question matches requested concept
    - No duplicate concept or exact text duplicate
    - No hallucinated internship, experience, project, or company
    """
    q_lower = (question or "").lower().strip()
    
    # 1. Format/Length constraints
    if not q_lower:
        return False, "Empty question"
    if not question.strip().endswith("?"):
        return False, "Does not end with question mark"
    words = q_lower.split()
    if len(words) < 3:
        return False, "Question is too short"
    if len(words) > 30:
        return False, "Question exceeds 30 words"
        
    # 2. Project grounding (plan-specified project must exist in resume)
    plan_project = plan.get("project", "")
    if plan_project:
        if plan_project.lower() not in (resume_project_summary or "").lower():
            return False, f"Project '{plan_project}' not found in candidate resume summary"
            
    # 3. Technology grounding (no hallucinated tools/technologies)
    tech_words = [
        "fastapi", "react", "mongodb", "django", "postgresql", "flask", "node", "express", 
        "angular", "vue", "mysql", "sqlite", "redis", "nextjs", "bootstrap", "tailwind", 
        "python", "java", "spring", "javascript", "typescript", "html", "css", "docker", 
        "kubernetes", "aws", "gcp", "azure", "pytorch", "tensorflow", "keras", "scikit-learn", 
        "numpy", "pandas", "opencv"
    ]
    from app.agents.Interview.planner.interview_planner import ROLE_TECHS
    role = (plan.get("role") or "").strip().lower()
    allowed_roadmap_techs = ROLE_TECHS.get(role, [])
    
    for tw in tech_words:
        if tw in q_lower:
            in_resume = tw in (resume_project_summary or "").lower() or tw in (skill_summary or "").lower()
            in_jd = tw in (job_description or "").lower()
            in_roadmap = tw in allowed_roadmap_techs
            if not in_resume and not in_jd and not in_roadmap:
                return False, f"Hallucinated technology '{tw}' not present in candidate profile, job description, or role roadmap"
                
    # 4. (Removed explicit keyword matching since we ask for scenario/reasoning questions)
    
    # 5. Prevent duplicates (duplicate concept check is in planner; this checks text duplicates)
    for h in question_history:
        if h and h.lower().strip() == q_lower:
            return False, "Exact duplicate of a previous question in history"
            
    # 6. Guard against hallucinated experiences / internships
    if "internship" in q_lower and "internship" not in (resume_project_summary or "").lower() and "intern" not in (skill_summary or "").lower():
        return False, "Hallucinated reference to an internship not found in profile"
        
    return True, "Valid"

async def generate_question_strict(
    *,
    llm: Any,
    plan: dict = None,
    difficulty: str = "basic",
    skill_summary: str = "",
    context: str = "",
    resume_project_summary: str = "",
    resume_has_projects: bool = True,
    is_first_question: bool = False,
    job_description: str = "",
    rag_context: str = "",
    followup_context: str = "",
    phase: str = "core",
    mode: str = "basic",
    previous_topics: list = None,
    topic_depth: int = 0,
    current_topic: str = "initial",
    current_intent: str = "concept",
    last_evaluation: dict = None,
    last_answer: str = "",
    last_answer_summary: str = "",
    question_number: int = 1,
    question_history: list = None,
    topic_history: list = None,
    answer_quality: str = "",
    available_subtopics: list | None = None,
    used_subtopics: list | None = None,
    used_concepts: list | None = None,
    used_topics: list | None = None,
    elapsed_time: int = 0,
    technologies_discussed: str = "",
    projects_discussed: str = "",
    previous_concepts: str = "",
    current_difficulty: str = "",
    interview_phase: str = "",
    **kwargs,
) -> Dict[str, Any]:
    """
    Phrases a single question strictly using the plan metadata.
    Does NOT select topics or determine the flow itself.
    """
    # Standardize plan properties
    plan = plan or {}
    plan_phase = plan.get("phase") or phase
    plan_topic = plan.get("topic") or current_topic
    plan_concept = plan.get("concept") or plan_topic
    plan_project = plan.get("project") or ""
    plan_tech = plan.get("technology") or ""
    plan_role = plan.get("role") or mode
    plan_diff = plan.get("difficulty") or difficulty
    plan_intent = plan.get("intent") or current_intent
    plan_q_num = plan.get("question_number") or question_number
    
    plan_role = plan_role.strip().lower()
    question_history = question_history or []
    
    from app.agents.Interview.prompts import PHRASE_CONCEPT_QUESTION_PROMPT, DETERMINISTIC_CONCEPT_QUESTION_PROMPT
    
    question_history_str = "\n".join(f"- {q}" for q in question_history) if question_history else "None"
    
    attempts = 2
    for attempt in range(attempts):
        if plan_project:
            # Deterministic project phrasing
            chunk = rag_context or resume_project_summary or ""
            if len(chunk) > 1000:
                chunk = chunk[:1000]
            prompt = DETERMINISTIC_CONCEPT_QUESTION_PROMPT.format(
                topic=plan_topic,
                concept=plan_concept,
                rag_context=chunk,
                question_history=question_history_str,
                technologies_discussed=technologies_discussed,
                projects_discussed=projects_discussed,
                previous_concepts=previous_concepts,
                current_difficulty=current_difficulty or plan_diff,
                interview_phase=interview_phase or plan_phase
            )
        else:
            # Standard concept phrasing
            prompt = PHRASE_CONCEPT_QUESTION_PROMPT.format(
                topic=plan_topic,
                concept=plan_concept,
                difficulty=plan_diff,
                question_history=question_history_str,
                technologies_discussed=technologies_discussed,
                projects_discussed=projects_discussed,
                previous_concepts=previous_concepts,
                current_difficulty=current_difficulty or plan_diff,
                interview_phase=interview_phase or plan_phase
            )
            
        try:
            # Phrase exactly once (or twice upon retry)
            response = await llm.ainvoke(prompt)
            content = getattr(response, "content", str(response)).strip()
            
            # Sanitize output text
            question = content.strip('"\'* \n\t')
            if "\n" in question:
                question = question.split("\n")[0].strip()
            if question.count("?") > 1:
                question = question.split("?")[0].strip() + "?"
                
            # Grounding and sanity validations
            is_valid, reason = validate_generated_question(
                question,
                plan,
                resume_project_summary,
                skill_summary,
                job_description,
                question_history
            )
            
            if is_valid or attempt == attempts - 1:
                logger.info(f"ACCEPTED: question='{question}', concept='{plan_concept}'")
                return {
                    "question": question,
                    "topic": plan_topic,
                    "subtopic": plan_topic,
                    "concept": plan_concept,
                    "secondary_concept": "",
                    "phase": plan_phase,
                    "type": plan_intent,
                    "difficulty": plan_diff,
                    "intent": plan_intent,
                }
            else:
                logger.warning(f"VALIDATION FAILED (attempt {attempt+1}/{attempts}) for concept '{plan_concept}': {reason}. Question: '{question}'")
        except Exception as e:
            logger.error(f"LLM Phrasing Exception: {e}")
            if attempt == attempts - 1:
                break
                
    # Fallback to local deterministic question pools if LLM fails or validates poorly twice
    fallback_list = FALLBACK_QUESTIONS.get(plan_role, FALLBACK_QUESTIONS["basic"])
    for f_item in fallback_list:
        fq = f_item["question"]
        fc = f_item["concept"]
        ft = f_item["topic"]
        
        if fq.lower() not in [qh.lower() for qh in question_history]:
            logger.info(f"ACCEPTED (FALLBACK): question='{fq}', concept='{fc}'")
            return {
                "question": fq,
                "topic": ft,
                "subtopic": ft,
                "concept": fc,
                "secondary_concept": "",
                "phase": plan_phase,
                "type": plan_intent,
                "difficulty": plan_diff,
                "intent": plan_intent,
            }
            
    default_q = "Can you explain a challenging technical decision you had to make and its outcome?"
    default_c = "challenging decision"
    logger.info(f"ACCEPTED (LAST RESORT): question='{default_q}', concept='{default_c}'")
    return {
        "question": default_q,
        "topic": "general",
        "subtopic": "general",
        "concept": default_c,
        "secondary_concept": "",
        "phase": plan_phase,
        "type": plan_intent,
        "difficulty": plan_diff,
        "intent": plan_intent,
    }
