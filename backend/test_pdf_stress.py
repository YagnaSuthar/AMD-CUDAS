"""
Phase 4B – PDF Stress Test Script.
Generates synthetic reports for 4, 10, and 20 question interviews
plus a long-answer stress test, and writes PDFs to disk for inspection.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.agents.Interview.report.report_builder import build_report
from app.agents.Interview.report.pdf_generator import generate_report_pdf

# ────────────────────────────────────────────────────────────
# Helper: build N synthetic turns
# ────────────────────────────────────────────────────────────

def _make_turns(n: int, long_answer: bool = False) -> list:
    topics = [
        "MongoDB Indexing", "REST API Design", "SQL Joins",
        "Docker Containers", "Python Decorators", "Git Branching",
        "Caching Strategies", "OAuth2 Flow", "Database Normalization",
        "Microservices vs Monolith", "CI/CD Pipelines", "WebSockets",
        "GraphQL vs REST", "Load Balancing", "Rate Limiting",
        "DNS Resolution", "TLS Handshake", "Event-Driven Architecture",
        "Message Queues", "Kubernetes Pods",
    ]
    difficulties = ["easy", "medium", "hard"]
    turns = []

    for i in range(n):
        topic = topics[i % len(topics)]
        diff  = difficulties[i % 3]
        corr  = max(1, min(10, 3 + (i * 7 % 8)))
        depth = max(1, min(10, 2 + (i * 5 % 9)))
        comm  = max(1, min(10, 4 + (i * 3 % 7)))
        conf  = max(1, min(10, 3 + (i * 4 % 8)))

        short_answer = (
            f"So basically, {topic.lower()} is about optimizing performance. "
            f"You need to understand the fundamentals and apply them correctly. "
            f"I think it relates to how systems handle data efficiently."
        )
        long_answer_text = short_answer * 20  # ~2600 chars

        if long_answer and i == 0:
            answer_text = short_answer * 40  # ~5200 chars
        elif long_answer and i == 1:
            answer_text = long_answer_text
        elif long_answer and i == 2:
            answer_text = "Yes."  # 50 chars
        else:
            answer_text = short_answer

        good = []
        mistakes = []
        missing = []
        misconceptions = []

        if corr >= 6:
            good.append(f"Demonstrated understanding of {topic} concepts")
        if corr >= 8:
            good.append(f"Excellent practical knowledge of {topic}")
        if corr <= 5:
            mistakes.append(f"Did not demonstrate a thorough understanding of {topic}")
            missing.append(f"Did not mention how {topic} improves performance")
        if corr <= 3:
            misconceptions.append(f"Importance of {topic} was not grasped")
        if corr <= 2:
            missing.append("None found")

        sev = "high" if corr <= 3 else ("medium" if corr <= 6 else "low")

        turns.append({
            "question": f"Explain {topic} and how it applies to real-world systems. Why is it important?",
            "answer": answer_text,
            "topic": topic,
            "difficulty": diff,
            "evaluation": {
                "correctness": corr,
                "concept_depth": depth,
                "communication": comm,
                "confidence": conf,
                "good_points": good,
                "mistakes": mistakes,
                "missing_points": missing,
                "misconceptions": misconceptions,
                "severity": sev,
                "final_feedback": f"Review {topic} fundamentals for deeper understanding.",
            },
        })

    return turns


def _write_pdf(name: str, n_questions: int, long_answer: bool = False, proctoring_violations: list = None):
    turns = _make_turns(n_questions, long_answer=long_answer)
    report = build_report(turns, proctoring_violations)
    meta = {
        "candidate_name": "Nirja Patel",
        "job_role": "Backend Developer",
        "interview_type": "Role-Based Interview",
        "interview_date": "June 13, 2026",
        "duration_minutes": 25 + n_questions * 3,
        "total_questions": n_questions,
    }
    pdf_bytes = generate_report_pdf(report, meta)
    out_dir = os.path.join(os.path.dirname(__file__), "test_reports")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{name}.pdf")
    with open(path, "wb") as f:
        f.write(pdf_bytes)
    print(f"  * {name}.pdf  ({len(pdf_bytes):,} bytes)  ->  {path}")


# ────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Phase 4B – PDF Stress Test\n")
    _write_pdf("case1_4q",       4, proctoring_violations=[
        {"type": "Tab Switch", "timestamp": "00:04:12", "count": 2},
        {"type": "Phone Detected", "timestamp": "00:08:45", "count": 1},
        {"type": "No Face Detected", "timestamp": "00:10:15", "count": 1},
    ])
    _write_pdf("case2_10q",     10)
    _write_pdf("case3_20q",     20)
    _write_pdf("case4_long_ans", 4, long_answer=True)
    print("\nAll reports generated successfully.")
