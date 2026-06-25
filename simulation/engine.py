"""
Simulation engine: derives quiz & course results from a DigitalTwin's Behavior.
Deterministic — same twin+quiz always yields the same score (seeded noise).
"""

import random


def _noise(seed: int, amplitude: float = 5.0) -> float:
    rng = random.Random(seed)
    return rng.uniform(-amplitude, amplitude)


def simulate_quiz(twin, quiz) -> dict:
    b = twin.behavior

    base = (
        b.comprehension_level * 0.35
        + b.motivation * 0.15
        + b.attention_level * 0.20
        + b.memory_retention * 0.15
        + b.persistence_level * 0.10
        + (100 - b.error_rate) * 0.05
    )

    fatigue_penalty = b.fatigue_level * 0.10
    stress_penalty = b.stress_level * 0.05
    raw_score = max(0.0, min(100.0, base - fatigue_penalty - stress_penalty))

    noise = _noise(twin.id ^ quiz.id, amplitude=6.0)
    simulated_score = round(max(0.0, min(100.0, raw_score + noise)), 1)

    # Difficulty modifier from actual Question records
    questions = quiz.questions.all()
    total_questions = questions.count() or 1

    difficulty_weights = {"easy": 0.0, "medium": -3.0, "hard": -7.0}
    diff_penalty = (
        sum(difficulty_weights.get(q.difficulty_level, 0.0) for q in questions)
        / total_questions
    )
    simulated_score = round(max(0.0, min(100.0, simulated_score + diff_penalty)), 1)

    # Time (seconds)
    speed_factor = b.learning_speed / 100.0
    base_time_per_q = 30
    time_factor = 2.0 - speed_factor  # 1.0 (fast) .. 2.0 (slow)
    simulated_time = int(total_questions * base_time_per_q * time_factor)
    simulated_time += int(_noise(twin.id + quiz.id, amplitude=30))
    simulated_time = max(30, simulated_time)

    # Cap to quiz time limit if set
    if quiz.time_limit_minutes:
        simulated_time = min(simulated_time, quiz.time_limit_minutes * 60)

    # Pass/fail — uses quiz.passing_score (your actual field name)
    passed = simulated_score >= quiz.passing_score
    correct = round((simulated_score / 100) * total_questions)

    return {
        "simulated_score": simulated_score,
        "correct": correct,
        "total": total_questions,
        "simulated_time_seconds": simulated_time,
        "passed": passed,
        "behavior_snapshot": {
            "comprehension_level": b.comprehension_level,
            "motivation": b.motivation,
            "attention_level": b.attention_level,
            "memory_retention": b.memory_retention,
            "error_rate": b.error_rate,
            "fatigue_level": b.fatigue_level,
            "stress_level": b.stress_level,
            "learning_speed": b.learning_speed,
            "learning_style": b.learning_style,
            "persistence_level": b.persistence_level,
        },
    }


def simulate_course(twin, course) -> dict:
    b = twin.behavior

    base = (
        b.comprehension_level * 0.40
        + b.motivation * 0.20
        + b.attention_level * 0.20
        + b.memory_retention * 0.10
        + b.curiosity_level * 0.10
    )
    fatigue_penalty = b.fatigue_level * 0.12
    raw_score = max(0.0, min(100.0, base - fatigue_penalty))

    noise = _noise(twin.id ^ (course.id * 31), amplitude=6.0)
    simulated_score = round(max(0.0, min(100.0, raw_score + noise)), 1)

    # Derive word count from course.content TextField
    word_count = len(course.content.split()) if course.content else 500

    speed_factor = b.learning_speed / 100.0
    wpm = int(150 + speed_factor * 100)  # 150..250 wpm
    simulated_time = int((word_count / wpm) * 60)
    simulated_time += int(_noise(twin.id + course.id, amplitude=20))
    simulated_time = max(30, simulated_time)

    return {
        "simulated_score": simulated_score,
        "simulated_time_seconds": simulated_time,
        "behavior_snapshot": {
            "comprehension_level": b.comprehension_level,
            "motivation": b.motivation,
            "attention_level": b.attention_level,
            "curiosity_level": b.curiosity_level,
            "fatigue_level": b.fatigue_level,
        },
    }
