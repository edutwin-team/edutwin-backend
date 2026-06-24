from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from twins.models import DigitalTwin
from content.models import Quiz, Course

from .models import SimulationResult
from .serializers import (
    QuizSimulationRequestSerializer,
    CourseSimulationRequestSerializer,
    QuizSimulationResultSerializer,
    CourseSimulationResultSerializer,
    SimulationResultSerializer,
)
from .groq_client import simulate_quiz_with_llm, simulate_course_with_llm


@extend_schema(
    request=QuizSimulationRequestSerializer,
    responses={201: QuizSimulationResultSerializer},
)
class SimulateQuizView(APIView):
    """
    POST /api/simulations/quiz/
    { "twin_id": <int>, "quiz_id": <int> }

    LLM incarnates the twin, answers every question,
    score is computed from is_correct flags, feedback written by LLM.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        req = QuizSimulationRequestSerializer(data=request.data)
        if not req.is_valid():
            return Response(req.errors, status=status.HTTP_400_BAD_REQUEST)

        twin = get_object_or_404(
            DigitalTwin,
            pk=req.validated_data["twin_id"],
            user=request.user,
        )
        quiz = get_object_or_404(Quiz, pk=req.validated_data["quiz_id"])

        if not hasattr(twin, "behavior"):
            return Response(
                {"detail": f"Twin '{twin.name}' has no Behavior profile."},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        try:
            result = simulate_quiz_with_llm(twin, quiz)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except EnvironmentError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        saved = SimulationResult.objects.create(
            user=request.user,
            twin=twin,
            simulation_type=SimulationResult.SimulationType.QUIZ,
            quiz=quiz,
            simulated_score=result["simulated_score"],
            simulated_time_seconds=result["simulated_time_seconds"],
            passed=result["passed"],
            correct=result["correct"],
            total=result["total"],
            feedback=result["feedback"],
            behavior_snapshot=result["behavior_snapshot"],
            answer_details=result["llm_answers"],
        )

        out = QuizSimulationResultSerializer(
            data={
                "twin_id": twin.id,
                "twin_name": twin.name,
                "quiz_id": quiz.id,
                "quiz_title": quiz.title,
                **result,
                "result_id": saved.pk,
            }
        )
        out.is_valid()
        return Response(out.data, status=status.HTTP_201_CREATED)


@extend_schema(
    request=QuizSimulationRequestSerializer,
    responses={201: QuizSimulationResultSerializer},
)
class SimulateCourseView(APIView):
    """
    POST /api/simulations/course/
    { "twin_id": <int>, "course_id": <int> }

    LLM reads the course as the twin, gives comprehension score + feedback.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        req = CourseSimulationRequestSerializer(data=request.data)
        if not req.is_valid():
            return Response(req.errors, status=status.HTTP_400_BAD_REQUEST)

        twin = get_object_or_404(
            DigitalTwin,
            pk=req.validated_data["twin_id"],
            user=request.user,
        )
        course = get_object_or_404(Course, pk=req.validated_data["course_id"])

        if not hasattr(twin, "behavior"):
            return Response(
                {"detail": f"Twin '{twin.name}' has no Behavior profile."},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        try:
            result = simulate_course_with_llm(twin, course)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except EnvironmentError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        saved = SimulationResult.objects.create(
            user=request.user,
            twin=twin,
            simulation_type=SimulationResult.SimulationType.COURSE,
            course=course,
            simulated_score=result["simulated_score"],
            simulated_time_seconds=result["simulated_time_seconds"],
            feedback=result["feedback"],
            behavior_snapshot=result["behavior_snapshot"],
            answer_details=result["llm_answers"],
        )

        out = CourseSimulationResultSerializer(
            data={
                "twin_id": twin.id,
                "twin_name": twin.name,
                "course_id": course.id,
                "course_title": course.title,
                **result,
                "result_id": saved.pk,
            }
        )
        out.is_valid()
        return Response(out.data, status=status.HTTP_201_CREATED)


class SimulationHistoryView(ListAPIView):
    """
    GET /api/simulations/history/
    Optional: ?twin_id=<int>  ?type=quiz|course
    """

    permission_classes = [IsAuthenticated]
    serializer_class = SimulationResultSerializer

    def get_queryset(self):
        qs = SimulationResult.objects.filter(user=self.request.user).select_related(
            "twin", "quiz", "course"
        )

        twin_id = self.request.query_params.get("twin_id")
        sim_type = self.request.query_params.get("type")

        if twin_id:
            qs = qs.filter(twin_id=twin_id)
        if sim_type in ("quiz", "course"):
            qs = qs.filter(simulation_type=sim_type)

        return qs
