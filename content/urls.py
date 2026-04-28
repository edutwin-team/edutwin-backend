from rest_framework_nested import routers
from .views import CourseViewSet, QuizViewSet, QuestionViewSet, AnswerViewSet

router = routers.DefaultRouter()
router.register("courses", CourseViewSet)
router.register("quizzes", QuizViewSet)

quiz_router = routers.NestedDefaultRouter(router, "quizzes", lookup="quiz")
quiz_router.register("questions", QuestionViewSet, basename="quiz-questions")

question_router = routers.NestedDefaultRouter(
    quiz_router, "questions", lookup="question"
)
question_router.register("answers", AnswerViewSet, basename="question-answers")

urlpatterns = router.urls + quiz_router.urls + question_router.urls
