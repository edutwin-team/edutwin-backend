from django.db.models import QuerySet
from rest_framework import permissions, viewsets
from .models import Answer, Course, Question, Quiz
from .serializers import (
    AnswerSerializer,
    CourseSerializer,
    QuestionSerializer,
    QuizSerializer,
    QuizSubmitSerializer,
)
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from user.permissions import IsAdminOrTeacherOrReadOnly, IsOwnerOrAdmin


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAdminOrTeacherOrReadOnly, IsOwnerOrAdmin]


class QuizViewSet(viewsets.ModelViewSet):
    queryset = Quiz.objects.prefetch_related("questions__answers")
    serializer_class = QuizSerializer
    permission_classes = [IsAdminOrTeacherOrReadOnly, IsOwnerOrAdmin]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    # POST /api/content/quizzes/{id}/submit/

    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, pk=None):
        quiz = Quiz.objects.get(pk=pk)

        serializer = QuizSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        submissions = serializer.validated_data["answers"]  # type: ignore
        total = len(submissions)
        correct = 0

        for sub in submissions:
            answer = Answer.objects.filter(
                id=sub["answer_id"], question_id=sub["question_id"], is_correct=True
            ).exists()
            if answer:
                correct += 1

        score = int((correct / total) * 100) if total else 0
        passed = score >= quiz.passing_score

        return Response(
            {
                "score": score,
                "correct": correct,
                "total": total,
                "passed": passed,
                "passing_score": quiz.passing_score,
            },
            status=status.HTTP_200_OK,
        )


class QuestionViewSet(viewsets.ModelViewSet):  # type: ignore[override]
    queryset = Question.objects.none()
    serializer_class = QuestionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self) -> QuerySet:
        return Question.objects.filter(quiz_id=self.kwargs["quiz_pk"]).prefetch_related(
            "answers"
        )


class AnswerViewSet(viewsets.ModelViewSet):  # type: ignore[override]
    queryset = Answer.objects.none()
    serializer_class = AnswerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self) -> QuerySet:
        return Answer.objects.filter(question_id=self.kwargs["question_pk"])
