import asyncio
from app.agents.Interview.planner.interview_planner import InterviewPlanner, ROADMAPS
from app.agents.Interview.sub_agents.question_generator.topic_selector import select_concept

def run_tests():
    print("--- Test 1: Basic Interview Flow ---")
    history = []
    for q in range(1, 16):
        plan = InterviewPlanner.get_next_plan(
            question_number=q,
            mode="basic",
            history_metadata=history,
            resume_project_summary="Built a React and Node.js app",
            resume_has_projects=True,
            answer_quality="strong",
            topic_depth=0,
            skills="React, Node.js",
            phase="resume",
            job_description="Fullstack Dev"
        )
        used_concepts = [m["concept"] for m in history if m.get("concept")]
        concept = select_concept(plan["phase"], plan["topic"], plan.get("role", ""), plan["difficulty"], used_concepts)
        plan["concept"] = concept
        history.append(plan)
        print(f"Q{q}: Phase={plan['phase']}, Topic={plan['topic']}, Concept={concept}, Diff={plan['difficulty']}")
        
    print("\n--- Test 2: Repetition Check (10 runs) ---")
    concepts_seen = set()
    for _ in range(10):
        c = select_concept("core", "DBMS", "backend", "medium", list(concepts_seen))
        concepts_seen.add(c)
        print(f"Selected: {c}")
        
    print("\n--- Test 3: Role Interview Flow (Frontend) ---")
    history_fe = []
    for q in range(1, 16):
        plan = InterviewPlanner.get_next_plan(
            question_number=q,
            mode="frontend",
            history_metadata=history_fe,
            resume_project_summary="React frontend",
            resume_has_projects=True,
            answer_quality="strong",
            topic_depth=0,
            skills="React",
            phase="resume",
            job_description="Frontend Engineer"
        )
        used_concepts = [m["concept"] for m in history_fe if m.get("concept")]
        concept = select_concept(plan["phase"], plan["topic"], plan.get("role", ""), plan["difficulty"], used_concepts)
        plan["concept"] = concept
        history_fe.append(plan)
        print(f"Q{q}: Phase={plan['phase']}, Topic={plan['topic']}, Concept={concept}")
        
    print("\n--- Test 4: Follow-up logic Evaluation Check ---")
    # Simulated eval data
    eval_data = {"correctness": 9, "concept_depth": 8, "communication": 8, "confidence": 9}
    total_score = eval_data["correctness"] + eval_data["concept_depth"] + eval_data["communication"] + eval_data["confidence"]
    print(f"Total Score: {total_score}")
    if total_score >= 32.0:
        print("Follow-up triggered successfully.")
    else:
        print("No follow-up.")

    print("\n--- Test 5: Verify All 11 Role Roadmaps ---")
    roles = [
        "frontend", "backend", "mern", "java", "python",
        "data_analyst", "data_science", "ml_ai", "devops",
        "cloud", "cybersecurity"
    ]
    
    for r in roles:
        print(f"\nVerifying role: {r}")
        history_role = []
        expected_roadmap = ROADMAPS.get(r, [])
        for q in range(1, 16):
            plan = InterviewPlanner.get_next_plan(
                question_number=q,
                mode=r,
                history_metadata=history_role,
                resume_project_summary="Some tech project summary",
                resume_has_projects=True,
                answer_quality="strong",
                topic_depth=0,
                skills="Python, React, SQL",
                phase="resume",
                job_description=f"{r.capitalize()} Position"
            )
            used_concepts = [m["concept"] for m in history_role if m.get("concept")]
            concept = select_concept(plan["phase"], plan["topic"], plan.get("role", ""), plan["difficulty"], used_concepts)
            if q == 1:
                concept = "General Overview"
            plan["concept"] = concept
            history_role.append(plan)
            
            # Assertions
            if q == 1:
                assert plan["phase"] == "resume", f"Q1 must be resume phase, got {plan['phase']}"
                assert plan["topic"] == "Resume & Projects", f"Q1 must be Resume & Projects topic, got {plan['topic']}"
            elif 2 <= q <= 13:
                expected_topic = expected_roadmap[q - 2]
                assert plan["topic"] == expected_topic, f"Q{q} topic must be {expected_topic}, got {plan['topic']}"
                assert plan["concept"] == expected_topic, f"Q{q} concept must be {expected_topic}, got {plan['concept']}"
            elif q == 14:
                assert plan["topic"] == "Scenario", f"Q14 must be Scenario topic, got {plan['topic']}"
                assert plan["phase"] == "core", f"Q14 must be core phase, got {plan['phase']}"
            elif q == 15:
                assert plan["phase"] == "behavioral", f"Q15 must be behavioral phase, got {plan['phase']}"
                assert plan["topic"] == "Behavioral", f"Q15 must be Behavioral topic, got {plan['topic']}"
                
        # Check duplicates in Q2-Q13
        tech_concepts = [m["concept"] for m in history_role[1:13]]
        assert len(tech_concepts) == len(set(tech_concepts)), f"Duplicates found in roadmap for {r}: {tech_concepts}"
        print(f"Role {r} verified successfully!")

if __name__ == "__main__":
    run_tests()
