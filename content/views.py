from django.db.models import QuerySet
from rest_framework import  viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .models import Answer, Course, Question, Quiz
from .serializers import (
    AnswerSerializer,
    CourseSerializer,
    QuestionSerializer,
    QuizSerializer,
    QuizSubmitSerializer,
)

from .utils import export_quiz_to_csv,import_quiz_from_csv,CSVImportError



class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer


    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class QuizViewSet(viewsets.ModelViewSet):
    queryset = Quiz.objects.all()
    serializer_class = QuizSerializer
    def get_queryset(self):
        return Quiz.objects.filter(user=self.request.user).order_by("id")


    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        
        # export quiz csv
    @action(detail=True, methods=["get"])
    def export(self, request, pk=None):
        quiz = self.get_object()
        return export_quiz_to_csv(quiz)

    #  import quiz csv
    @action(detail=False, methods=["post"], url_path="import")
    def import_quiz(self, request):
        file = request.FILES.get("file")

        if not file:
            return Response(
                {"error": "No file provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            quiz = import_quiz_from_csv(file, request.user)

            return Response({
                "id": quiz.id, #type: ignore
                "title": quiz.title
            }, status=status.HTTP_201_CREATED)

        except CSVImportError as e:
            return Response({
                "error": e.message
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "error": "Erreur serveur inattendue"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    #todo : i didnt modify this , A verifier si on a besoin
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

    def perform_create(self, serializer):
        serializer.save(question_id=self.kwargs["question_pk"])

    def get_queryset(self) -> QuerySet:  # type: ignore[override]
        return Answer.objects.filter(question_id=self.kwargs["question_pk"])
