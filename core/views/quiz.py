from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from core.serializers.quiz import (
    StartQuizInputSerializer,
    QuizAttemptOutputSerializer,
    GradeQuizInputSerializer,
)
from core.services.quiz_service import start_quiz_attempt, grade_quiz_attempt


class StartQuizView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StartQuizInputSerializer  # Helps drf-spectacular

    @extend_schema(
        tags=["Quiz"],
        summary="Start a new quiz attempt",
        request=StartQuizInputSerializer,
        responses={201: QuizAttemptOutputSerializer, 400: None},
    )
    def post(self, request):
        serializer = StartQuizInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            attempt = start_quiz_attempt(
                user=request.user, quiz_id=serializer.validated_data["quiz_id"]
            )
            return Response(
                QuizAttemptOutputSerializer(attempt).data,
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SubmitQuizView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GradeQuizInputSerializer  # Helps drf-spectacular

    @extend_schema(
        tags=["Quiz"],
        summary="Submit answers and grade quiz",
        request=GradeQuizInputSerializer,
        responses={200: QuizAttemptOutputSerializer, 400: None},
    )
    def post(self, request, attempt_id):
        serializer = GradeQuizInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Convert string keys from DictField back to integers for the service layer
        user_answers = {
            int(k): v for k, v in serializer.validated_data["user_answers"].items()
        }

        try:
            attempt = grade_quiz_attempt(
                attempt_id=attempt_id, user_answers=user_answers
            )
            return Response(QuizAttemptOutputSerializer(attempt).data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
