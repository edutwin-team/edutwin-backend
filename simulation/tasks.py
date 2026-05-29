# from celery import shared_task
# from ..twins.models import Twin, TwinSimulation
# from .engine import simulate_quiz, simulate_course
# from .groc_llm import generate_quiz_feedback, generate_course_feedback
# from content.models import Quiz, Course


# @shared_task
# def run_twin_simulation(twin_id: int, content_type: str, content_id: int):
#     twin = Twin.objects.get(pk=twin_id)

#     if content_type == "quiz":
#         quiz = Quiz.objects.get(pk=content_id)
#         result = simulate_quiz(twin, quiz)
#         feedback = generate_quiz_feedback(twin, result)

#     elif content_type == "course":
#         course = Course.objects.get(pk=content_id)
#         result = simulate_course(twin, course)
#         feedback = generate_course_feedback(twin, course, result)

#     else:
#         raise ValueError(f"Unknown content_type: {content_type}")

#     TwinSimulation.objects.create(
#         twin=twin,
#         content_type=content_type,
#         content_id=content_id,
#         simulated_score=result["simulated_score"],
#         simulated_time_seconds=result["simulated_time_seconds"],
#         difficulty_perception=result["difficulty_perception"],
#         llm_feedback=feedback,
#     )
