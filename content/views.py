from django.db.models import QuerySet
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .models import Answer, Course, Question, Quiz, ContentType
from .serializers import (
    AnswerSerializer,
    CourseSerializer,
    QuestionSerializer,
    QuizSerializer,
    QuizSubmitSerializer,
)
from user.permissions import IsAdminOrTeacherOrReadOnly, IsOwnerOrAdmin


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.AllowAny]

    # permission_classes = [IsAdminOrTeacherOrReadOnly, IsOwnerOrAdmin]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, content_type=ContentType.course)


class QuizViewSet(viewsets.ModelViewSet):
    queryset = Quiz.objects.prefetch_related("questions__answers")
    serializer_class = QuizSerializer
    permission_classes = [permissions.AllowAny]
    # permission_classes = [IsAdminOrTeacherOrReadOnly, IsOwnerOrAdmin]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, content_type=ContentType.quiz)

    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, pk=None):
        quiz = Quiz.objects.get(pk=pk)
        serializer = QuizSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submissions = serializer.validated_data["answers"]  # type: ignore
        total = len(submissions)
        correct = sum(
            1
            for sub in submissions
            if Answer.objects.filter(
                id=sub["answer_id"], question_id=sub["question_id"], is_correct=True
            ).exists()
        )
        score = int((correct / total) * 100) if total else 0
        return Response(
            {
                "score": score,
                "correct": correct,
                "total": total,
                "passed": score >= quiz.passing_score,
                "passing_score": quiz.passing_score,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    parameters=[
        OpenApiParameter("quiz_pk", int, OpenApiParameter.PATH),
    ]
)
class QuestionViewSet(viewsets.ModelViewSet):  # type: ignore[override]
    queryset = Question.objects.none()
    serializer_class = QuestionSerializer
    # permission_classes = [permissions.IsAuthenticated]
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        serializer.save(quiz_id=self.kwargs["quiz_pk"])

    def get_queryset(self) -> QuerySet:  # type: ignore[override]
        return Question.objects.filter(quiz_id=self.kwargs["quiz_pk"]).prefetch_related(
            "answers"
        )


@extend_schema(
    parameters=[
        OpenApiParameter("quiz_pk", int, OpenApiParameter.PATH),
        OpenApiParameter("question_pk", int, OpenApiParameter.PATH),
    ]
)
class AnswerViewSet(viewsets.ModelViewSet):  # type: ignore[override]
    queryset = Answer.objects.none()
    serializer_class = AnswerSerializer
    permission_classes = [permissions.AllowAny]
    # permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(question_id=self.kwargs["question_pk"])

    def get_queryset(self) -> QuerySet:  # type: ignore[override]
        return Answer.objects.filter(question_id=self.kwargs["question_pk"])
