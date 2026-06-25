from django.contrib import admin
from .models import SimulationResult


@admin.register(SimulationResult)
class SimulationResultAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "twin",
        "simulation_type",
        "simulated_score",
        "passed",
        "created_at",
    ]
    list_filter = ["simulation_type", "passed"]
    search_fields = ["twin__name", "quiz__title", "course__title"]
    readonly_fields = ["behavior_snapshot", "feedback", "created_at"]
