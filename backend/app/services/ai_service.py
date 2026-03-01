"""
AI Service for generating career roadmaps and other AI-powered features.
"""

import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def generate_career_roadmap(student_data: Dict[str, Any]) -> str:
    """
    Generate a personalized career roadmap based on student's profile.
    
    Args:
        student_data: Dictionary containing student's goal, academics, skills, etc.
        
    Returns:
        A formatted career roadmap string.
    """
    try:
        goal = student_data['goal'].lower()
        department = student_data['department'].lower()
        
        # Create goal-specific prompts and recommendations
        goal_specific_content = _get_goal_specific_content(goal, department, student_data)
        
        # Create a comprehensive prompt for the AI
        prompt = f"""
As an expert career counselor, create a highly personalized career roadmap for this student:

STUDENT PROFILE:
- Career Goal: {student_data['goal']}
- Department: {student_data['department']}
- Current Semester: {student_data['semester']}
- Skills: {', '.join(student_data['skills']) if student_data['skills'] else 'None specified'}
- Academic Performance: {student_data['average_percentage']}% average
- Certificates Earned: {student_data['total_certificates']} (Total points: {student_data['certificate_points']})

SUBJECT PERFORMANCE:
{chr(10).join([f"- {subject['name']}: {subject['percentage']}%" for subject in student_data['subjects']]) if student_data['subjects'] else 'No academic data available'}

TASK:
Create a comprehensive career roadmap with the following sections:
1. **Career Goal Analysis**: Brief analysis of their stated goal and its feasibility
2. **Skill Development**: {goal_specific_content['skill_focus']}
3. **Academic Focus**: {goal_specific_content['academic_focus']}
4. **Short-term Goals** (Next 6 months): {goal_specific_content['short_term_goals']}
5. **Medium-term Goals** (6-18 months): {goal_specific_content['medium_term_goals']}
6. **Long-term Goals** (18+ months): {goal_specific_content['long_term_goals']}
7. **Recommended Resources**: {goal_specific_content['resources']}
8. **Potential Challenges**: {goal_specific_content['challenges']}

Format the response with clear headings, bullet points, and actionable advice. Be encouraging but realistic.
Make it specific to their goal and current academic performance. Provide concrete, actionable steps.
"""

        # Generate a highly personalized roadmap based on the goal
        roadmap = _generate_personalized_roadmap(student_data, goal_specific_content)
        
        return roadmap
        
    except Exception as e:
        logger.error(f"Error generating career roadmap: {str(e)}")
        raise Exception("Failed to generate career roadmap")

def _get_goal_specific_content(goal: str, department: str, student_data: Dict[str, Any]) -> Dict[str, str]:
    """Get goal-specific content for different career paths."""
    
    goal_mapping = {
        'machine learning': {
            'skill_focus': """
            **Technical Skills to Focus On:**
            - **Python Programming**: Master Python with focus on ML libraries (NumPy, Pandas, Scikit-learn)
            - **Mathematics**: Linear algebra, calculus, probability, and statistics
            - **ML Frameworks**: TensorFlow, PyTorch, Keras for deep learning
            - **Data Processing**: SQL, data wrangling, feature engineering
            - **Cloud Platforms**: AWS SageMaker, Google Cloud ML, Azure ML
            
            **Soft Skills:**
            - Statistical thinking and analytical mindset
            - Problem decomposition and algorithmic thinking
            - Data visualization and communication
            - Research methodology and experimentation
            - Business acumen for ML applications
            """,
            'academic_focus': """
            Focus on mathematics-heavy courses, statistics, algorithms, and data structures.
            Take electives in artificial intelligence, data mining, and computational statistics.
            Work on ML projects and participate in Kaggle competitions.
            """,
            'short_term_goals': """
            1. **Master Python for ML**: Complete Python for Data Science course, implement 5 ML algorithms from scratch
            2. **Build Foundation**: Complete Linear Algebra and Calculus courses with 85%+ grades
            3. **Start Projects**: Create 2-3 ML projects (regression, classification, clustering) for portfolio
            4. **Learn Tools**: Master Pandas, NumPy, and Scikit-learn through hands-on practice
            5. **Join Community**: Participate in Kaggle competitions and ML meetups
            """,
            'medium_term_goals': """
            1. **Deep Learning Specialization**: Complete Andrew Ng's Deep Learning courses or similar
            2. **Advanced Projects**: Build end-to-end ML systems with deployment capabilities
            3. **Research Experience**: Assist professors with ML research or publish a paper
            4. **Internship**: Secure ML/Data Science internship at tech company
            5. **Certifications**: Obtain TensorFlow Developer Certificate or AWS ML Specialty
            """,
            'long_term_goals': """
            1. **Graduate Studies**: Apply to MS/PhD programs in ML/AI at top universities
            2. **Industry Role**: Target ML Engineer, Data Scientist, or Research Scientist positions
            3. **Specialization**: Focus on NLP, Computer Vision, or Reinforcement Learning
            4. **Contribution**: Publish research papers or contribute to open-source ML projects
            5. **Leadership**: Lead ML teams or start ML-focused startup
            """,
            'resources': """
            **Online Learning:**
            - Andrew Ng's Machine Learning and Deep Learning courses (Coursera)
            - Fast.ai Practical Deep Learning for Coders
            - MIT Introduction to Deep Learning
            - Python for Data Science Handbook (online)
            
            **Books:**
            - "Hands-On Machine Learning with Scikit-Learn, Keras & TensorFlow"
            - "Pattern Recognition and Machine Learning" by Bishop
            - "Deep Learning" by Goodfellow, Bengio, and Courville
            
            **Practice Platforms:**
            - Kaggle for competitions and datasets
            - HackerRank for Python and algorithms
            - LeetCode for coding interviews
            - GitHub for ML project portfolios
            
            **Certifications:**
            - TensorFlow Developer Certificate
            - AWS Certified Machine Learning Specialist
            - Microsoft Certified: Azure Data Scientist Associate
            """,
            'challenges': """
            **Challenge 1: Mathematical Complexity**
            **Solution:** Dedicate specific time for math fundamentals, use visual learning tools, join study groups
            
            **Challenge 2: Keeping Up with Rapid Advancements**
            **Solution:** Follow arXiv papers, join ML communities, attend conferences, continuous learning
            
            **Challenge 3: Computational Resource Requirements**
            **Solution:** Use cloud platforms, Google Colab, optimize code efficiency, apply for research credits
            
            **Challenge 4: Theory vs Practice Gap**
            **Solution:** Balance theoretical learning with hands-on projects, participate in hackathons, seek internships
            """
        },
        'full stack': {
            'skill_focus': """
            **Technical Skills to Focus On:**
            - **Frontend**: React, Vue.js, TypeScript, HTML5, CSS3, responsive design
            - **Backend**: Node.js, Express, Python/Django, REST APIs, GraphQL
            - **Databases**: SQL (PostgreSQL, MySQL), NoSQL (MongoDB, Redis)
            - **DevOps**: Docker, CI/CD, AWS/Azure/GCP, Git, Linux
            - **Tools**: Webpack, testing frameworks, authentication systems
            
            **Soft Skills:**
            - Full-system thinking and architecture
            - Problem-solving and debugging
            - Communication with technical and non-technical teams
            - Project management and prioritization
            - User experience understanding
            """,
            'academic_focus': """
            Focus on software engineering, database systems, web technologies, and algorithms.
            Take courses in system design, network programming, and human-computer interaction.
            Build full-stack projects for portfolio.
            """,
            'short_term_goals': """
            1. **Master Frontend**: Learn React and build 3 responsive web applications
            2. **Backend Development**: Learn Node.js/Express and create RESTful APIs
            3. **Database Skills**: Master SQL and work with PostgreSQL and MongoDB
            4. **Portfolio Projects**: Build 2-3 full-stack applications with real features
            5. **Git & Deployment**: Learn version control and deploy apps to cloud platforms
            """,
            'medium_term_goals': """
            1. **Advanced Architecture**: Learn microservices, system design, and scalability
            2. **DevOps Skills**: Master Docker, CI/CD pipelines, and cloud deployment
            3. **Open Source**: Contribute to significant open-source projects
            4. **Internship**: Secure full-stack developer internship
            5. **Specialization**: Focus on frontend, backend, or DevOps based on interest
            """,
            'long_term_goals': """
            1. **Senior Developer Role**: Target senior full-stack or tech lead positions
            2. **Architecture Expertise**: Design large-scale distributed systems
            3. **Technical Leadership**: Lead development teams and mentor junior developers
            4. **Startup/Consulting**: Consider freelance work or starting a tech company
            5. **Continuous Growth**: Stay updated with emerging technologies and best practices
            """,
            'resources': """
            **Online Learning:**
            - The Odin Project (full-stack curriculum)
            - FreeCodeCamp's full-stack development
            - React Documentation and Tutorials
            - Node.js Best Practices (online guide)
            
            **Books:**
            - "Clean Code" by Robert Martin
            - "Designing Data-Intensive Applications" by Kleppmann
            - "You Don't Know JS" series by Kyle Simpson
            
            **Practice Platforms:**
            - LeetCode for coding interviews
            - HackerRank for full-stack challenges
            - CodeSignal for technical assessments
            - GitHub for project portfolios
            
            **Certifications:**
            - AWS Certified Developer
            - Google Cloud Professional Developer
            - Microsoft Certified: Azure Developer Associate
            """,
            'challenges': """
            **Challenge 1: Technology Overload**
            **Solution:** Focus on fundamentals, choose one stack to master, gradual learning approach
            
            **Challenge 2: Frontend vs Backend Dilemma**
            **Solution:** Build full-stack projects, understand both sides, specialize based on interest
            
            **Challenge 3: Keeping Up with Framework Changes**
            **Solution:** Focus on core concepts, follow official docs, join developer communities
            
            **Challenge 4: Imposter Syndrome**
            **Solution:** Build confidence through projects, contribute to open source, seek mentorship
            """
        },
        'data science': {
            'skill_focus': """
            **Technical Skills to Focus On:**
            - **Programming**: Python (Pandas, NumPy, Scikit-learn), R for statistical analysis
            - **Statistics**: Hypothesis testing, regression analysis, experimental design
            - **Data Visualization**: Tableau, Power BI, Matplotlib, Seaborn, D3.js
            - **Big Data**: Spark, Hadoop, SQL optimization, data warehousing
            - **Business Intelligence**: Excel advanced features, dashboard creation
            
            **Soft Skills:**
            - Statistical thinking and analytical reasoning
            - Business acumen and domain knowledge
            - Data storytelling and presentation
            - Critical thinking and problem-solving
            - Communication with non-technical stakeholders
            """,
            'academic_focus': """
            Focus on statistics, probability, data analysis, and business courses.
            Take electives in data mining, business analytics, and predictive modeling.
            Work on real-world data analysis projects.
            """,
            'short_term_goals': """
            1. **Master Python for Data**: Complete Data Science track, master Pandas and NumPy
            2. **Statistics Foundation**: Complete statistics courses with practical applications
            3. **Visualization Skills**: Learn Tableau and create interactive dashboards
            4. **SQL Mastery**: Advanced SQL queries, database optimization, and data extraction
            5. **Portfolio Projects**: Analyze 3-5 real datasets and publish findings
            """,
            'medium_term_goals': """
            1. **Advanced Analytics**: Learn machine learning for predictive modeling
            2. **Big Data Technologies**: Master Spark and handle large-scale data processing
            3. **Domain Expertise**: Specialize in finance, healthcare, or marketing analytics
            4. **Business Impact**: Work on projects that drive business decisions
            5. **Certifications**: Obtain Google Data Analytics or IBM Data Science certificates
            """,
            'long_term_goals': """
            1. **Senior Data Scientist**: Lead data science teams and strategic initiatives
            2. **Analytics Leadership**: Become Head of Data or Chief Data Officer
            3. **Specialization**: Expert in specific domain (healthcare, finance, etc.)
            4. **Consulting/Advisory**: Provide data strategy consulting to organizations
            5. **Innovation**: Develop new analytical methodologies or start data-driven company
            """,
            'resources': """
            **Online Learning:**
            - Google Data Analytics Certificate
            - IBM Data Science Professional Certificate
            - DataCamp's Data Scientist Track
            - Khan Academy's Statistics and Probability
            
            **Books:**
            - "Practical Statistics for Data Scientists" by Bruce & Bruce
            - "Storytelling with Data" by Cole Nussbaumer Knaflic
            - "Data Science for Business" by Provost & Fawcett
            
            **Practice Platforms:**
            - Kaggle for datasets and competitions
            - DrivenData for social impact challenges
            - GitHub for data analysis portfolios
            - Tableau Public for visualization portfolios
            
            **Certifications:**
            - Google Data Analytics Certificate
            - IBM Data Science Professional Certificate
            - Microsoft Certified: Data Analyst Associate
            """,
            'challenges': """
            **Challenge 1: Data Quality and Cleaning**
            **Solution:** Develop systematic data cleaning workflows, use automation tools, document processes
            
            **Challenge 2: Communicating Insights**
            **Solution:** Practice data storytelling, learn visualization best practices, understand business context
            
            **Challenge 3: Technical vs Business Balance**
            **Solution:** Develop business acumen, understand stakeholder needs, focus on impact
            
            **Challenge 4: Ethical Considerations**
            **Solution:** Study data ethics, ensure privacy, consider bias in analysis and models
            """
        }
    }
    
    # Find the best matching goal
    for key, content in goal_mapping.items():
        if key in goal:
            return content
    
    # Default content for unspecified goals
    return {
        'skill_focus': """
        **Technical Skills to Focus On:**
        - **Core Programming**: Master at least one programming language relevant to your goal
        - **Data Structures & Algorithms**: Essential for technical interviews and problem-solving
        - **System Design**: Important for senior roles and architecting solutions
        - **Domain-specific tools**: Research and learn tools specific to your career goal
        
        **Soft Skills:**
        - Communication and presentation skills
        - Team collaboration and leadership
        - Problem-solving and critical thinking
        - Time management and organization
        - Adaptability and continuous learning
        """,
        'academic_focus': """
        Focus on core computer science fundamentals, mathematics, and domain-specific courses.
        Take electives that align with your career goals and work on practical projects.
        Maintain strong academic performance while gaining hands-on experience.
        """,
        'short_term_goals': """
        1. **Skill Building**: Complete 2-3 online courses relevant to your career goal
        2. **Project Development**: Build 1-2 personal projects to showcase your abilities
        3. **Networking**: Join relevant student clubs and attend industry events
        4. **Academic Excellence**: Aim for high grades in relevant courses
        5. **Portfolio Creation**: Start building a professional portfolio
        """,
        'medium_term_goals': """
        1. **Experience Building**: Apply for internships in your target field
        2. **Advanced Skills**: Learn advanced concepts and specialized technologies
        3. **Open Source**: Contribute to open-source projects
        4. **Certifications**: Obtain relevant professional certifications
        5. **Leadership**: Take on leadership roles in projects or organizations
        """,
        'long_term_goals': """
        1. **Career Entry**: Apply for entry-level positions in your target field
        2. **Graduate Studies**: Consider advanced degrees if relevant to your goal
        3. **Professional Network**: Build a strong professional network
        4. **Continuous Learning**: Stay updated with industry trends and technologies
        5. **Career Advancement**: Plan for growth into senior or specialized roles
        """,
        'resources': """
        **Online Learning:**
        - Coursera, edX, or Udemy courses relevant to your field
        - Industry-specific tutorials and documentation
        - Technical blogs and online communities
        
        **Books:**
        - Field-specific textbooks and reference materials
        - Industry best practices and case studies
        
        **Practice Platforms:**
        - LeetCode, HackerRank for coding practice
        - GitHub for project collaboration
        - Field-specific challenge platforms
        
        **Certifications:**
        - Industry-recognized certifications in your field
        - Cloud computing certifications (AWS, Azure, GCP)
        - Domain-specific professional certifications
        """,
        'challenges': """
        **Challenge 1: Skill Gap**
        **Solution:** Continuous learning, practice, seeking feedback, mentorship
        
        **Challenge 2: Competition**
        **Solution:** Differentiate with unique projects, specialized skills, personal branding
        
        **Challenge 3: Work-Life Balance**
        **Solution:** Time management, setting boundaries, prioritizing health
        
        **Challenge 4: Keeping Current**
        **Solution:** Continuous learning, professional development, industry engagement
        """
    }

def _generate_personalized_roadmap(student_data: Dict[str, Any], goal_content: Dict[str, str]) -> str:
    """Generate a highly personalized roadmap based on student data and goal-specific content."""
    
    goal = student_data['goal']
    avg_percentage = student_data['average_percentage']
    skills = student_data['skills']
    semester = student_data['semester']
    
    # Determine performance level and tailor advice
    if avg_percentage >= 80:
        performance_level = "Excellent"
        performance_advice = "Your academic performance is outstanding. You're well-positioned for competitive opportunities and advanced roles."
        intensity = "aggressive"
    elif avg_percentage >= 60:
        performance_level = "Good"
        performance_advice = "Your academic performance is solid. Focus on consistency and skill development to reach the next level."
        intensity = "moderate"
    else:
        performance_level = "Needs Improvement"
        performance_advice = "Focus on strengthening your academic foundation while developing practical skills."
        intensity = "steady"
    
    # Customize based on current skills
    skills_advice = ""
    if skills:
        if len(skills) >= 5:
            skills_advice = f"You already have a strong foundation with skills like {', '.join(skills[:3])}. Focus on advanced applications and specialization."
        elif len(skills) >= 3:
            skills_advice = f"You have some relevant skills including {', '.join(skills)}. Build upon these with more advanced topics."
        else:
            skills_advice = f"You're starting with {skills if skills else 'limited skills'}. Focus on building fundamental technical skills first."
    else:
        skills_advice = "Focus on building fundamental technical skills relevant to your career goal."
    
    # Customize based on academic level
    if semester and semester <= 4:
        timeline_advice = "You're in your early semesters. Focus on building strong fundamentals and exploring different areas."
    elif semester and semester <= 6:
        timeline_advice = "You're in the middle of your program. Time to specialize and gain practical experience."
    else:
        timeline_advice = "You're in your final semesters. Focus on advanced topics, projects, and career preparation."
    
    roadmap = f"""
# Career Roadmap: {goal.title()}

## 🎯 Career Goal Analysis
Your goal to become a {goal} is ambitious and achievable with the right strategy. Based on your profile in {student_data['department']}, you have a solid foundation to build upon. {performance_advice} {timeline_advice} {skills_advice}

## 📊 Current Academic Performance
**Performance Level:** {performance_level} ({avg_percentage}% average)
{performance_advice}
**Current Standing:** {semester and f"Semester {semester}" or "Academic level not specified"}
**Skills Assessment:** {len(skills) if skills else 0} technical skills identified

## 🛠️ Skill Development Plan

{goal_content['skill_focus']}

## 📚 Academic Focus Areas

{goal_content['academic_focus']}

**Current Semester Focus:**
- Maintain or improve your GPA in core subjects
- Focus on practical projects and assignments
- Participate in technical workshops and seminars
- {timeline_advice}

## 🎯 Short-term Goals (Next 6 months)

{goal_content['short_term_goals']}

**Academic Targets:**
- Aim for {min(avg_percentage + 10, 95)}% average in relevant courses
- Complete at least 2 projects related to your goal
- Join relevant student organizations or study groups

## 🚀 Medium-term Goals (6-18 months)

{goal_content['medium_term_goals']}

**Milestones:**
- Complete {intensity == 'aggressive' and '3' or intensity == 'moderate' and '2' or '1'} significant projects
- Obtain {intensity == 'aggressive' and '2' or '1'} relevant certifications
- Secure internship or research opportunity

## 🌟 Long-term Goals (18+ months)

{goal_content['long_term_goals']}

**Career Preparation:**
- Build professional resume and portfolio
- Prepare for technical interviews
- Network with industry professionals
- Consider graduate studies if relevant to your goal

## 📚 Recommended Resources

{goal_content['resources']}

## ⚠️ Potential Challenges & Solutions

{goal_content['challenges']}

## 💡 Success Tips

1. **Stay Consistent**: Small, daily efforts lead to significant results
2. **Seek Feedback**: Regular feedback helps you improve faster
3. **Build Projects**: Practical experience is invaluable
4. **Network**: Connections can open unexpected opportunities
5. **Stay Curious**: Continuous learning is key in tech
6. **Track Progress**: Monitor your goals and adjust strategies as needed
7. **Find Mentors**: Learn from experienced professionals in your field

---

*This roadmap is personalized based on your current profile and goals. Review and update it every 3-4 months based on your progress and changing aspirations.*

**Next Steps:** Start with your short-term goals and focus on building momentum. Your journey to becoming a {goal} begins today!

**Remember:** Your journey is unique. Focus on progress, not perfection. Every step forward counts!
"""
    
    return roadmap.strip()
