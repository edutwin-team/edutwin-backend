from rest_framework.decorators import api_view
from rest_framework.response import Response

from datetime import timedelta

from django.utils import timezone

from content.models import Quiz
from twins.models import DigitalTwin,PedagogicalContext
from simulation.models import SimulationResult


@api_view(['GET'])
def dashboard(request):
    user = request.user

    simulations_qs = SimulationResult.objects.filter(user=user)

    now = timezone.now()
    start_7_days = now - timedelta(days=7)

    # COUNTS
    contexts_count = PedagogicalContext.objects.filter(user=user).count()
    twins_count = DigitalTwin.objects.filter(user=user).count()
    quizzes_count = Quiz.objects.filter(user=user).count()
    simulations_count = simulations_qs.count()

    # LAST 7 DAYS
    last_7_days_count = simulations_qs.filter(
        created_at__gte=start_7_days
    ).count()

    # weekley chart
    daily_data = []

    for i in range(7):
        day = now - timedelta(days=6 - i)

        count = simulations_qs.filter(
            created_at__date=day.date()
        ).count()

        daily_data.append({
            "day": day.strftime("%A"),
            "count": count
        })

    # last 3 twins
    last_twins = DigitalTwin.objects.filter(user=user).order_by("-created_at")[:3]

    last_twins_data = [
        {
            "id": t.id, #type: ignore
            "name": t.name,
            "description": t.description,
            "average_grade": t.average_grade,
        }
        for t in last_twins
    ]

    return Response({
        "counts": {
            "contexts": contexts_count,
            "twins": twins_count,
            "quizzes": quizzes_count,
            "simulations": simulations_count,
        },

        "last_7_days_total": last_7_days_count,

        "weekly_simulations": daily_data,

        "last_twins": last_twins_data
    })