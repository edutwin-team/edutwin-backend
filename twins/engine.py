from content.models import Answer, Course, Question, Quiz
import random


def simulate_quiz(twin, quiz: quiz) -> dict:
    questions = quiz.questions.prefetch_related("answers").all()
    total = questions.count()
    correct = 0

    for question in questions:
        correct_answers = question.answers.filter(is_correct=true)
        # probabilité de bonne réponse basée sur le niveau du twin
        base_chance = twin.level / 10.0  # 0.1 à 1.0

        # bonus/malus selon domaines forts/faibles
        # (basé sur les tags du quiz)
        title_lower = quiz.title.lower()
        for domain in twin.strong_domains:
            if domain.lower() in title_lower:
                base_chance = min(1.0, base_chance + 0.2)
        for domain in twin.weak_domains:
            if domain.lower() in title_lower:
                base_chance = max(0.0, base_chance - 0.2)

        if random.random() < base_chance and correct_answers.exists():
            correct += 1

    score = int((correct / total) * 100) if total else 0
    passed = score >= quiz.passing_score

    # temps simulé (secondes) — basé sur time_limit et niveau
    simulated_time = int(quiz.time_limit_minutes * 60 * (1.2 - twin.level / 10))

    match score:
        case s if s >= 80:
            perception = 1
        case s if s >= 70:
            perception = 2
        case s if s >= 55:
            perception = 3
        case s if s >= 40:
            perception = 4
        case _:
            perception = 5
    return {
        "simulated_score": score,
        "simulated_time_seconds": simulated_time,
        "difficulty_perception": perception,
        "correct": correct,
        "total": total,
        "passed": passed,
    }


def simulate_course(twin, course: course) -> dict:
    # temps de lecture estimé selon vitesse du twin
    word_count = len(course.body.split())
    avg_wpm = 200  # mots/minute moyen
    reading_time = int((word_count / avg_wpm) * 60 / twin.reading_speed)

    # compréhension estimée basée sur le niveau
    comprehension = int(twin.level * 10)
    for domain in twin.strong_domains:
        if domain.lower() in course.title.lower():
            comprehension = min(100, comprehension + 15)
    for domain in twin.weak_domains:
        if domain.lower() in course.title.lower():
            comprehension = max(0, comprehension - 15)

    match comprehension:
        case c if c >= 90:
            perception = 1  # too_easy
        case c if c >= 70:
            perception = 2  # easy
        case c if c >= 50:
            perception = 3  # appropriate
        case c if c >= 30:
            perception = 4  # hard
        case _:
            perception = 5  # too_hard

    return {
        "simulated_score": comprehension,
        "simulated_time_seconds": reading_time,
        "difficulty_perception": perception,
    }
