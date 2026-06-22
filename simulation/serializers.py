from rest_framework import serializers
from .models import SimulationResult


class QuizSimulationRequestSerializer(serializers.Serializer):
    twin_id = serializers.IntegerField()
    quiz_id = serializers.IntegerField()


class CourseSimulationRequestSerializer(serializers.Serializer):
    twin_id = serializers.IntegerField()
    course_id = serializers.IntegerField()


class BehaviorSnapshotSerializer(serializers.Serializer):
    comprehension_level = serializers.IntegerField()
    motivation = serializers.IntegerField()
    fatigue_level = serializers.IntegerField()
    attention_level = serializers.IntegerField(required=False)
    memory_retention = serializers.IntegerField(required=False)
    error_rate = serializers.IntegerField(required=False)
    stress_level = serializers.IntegerField(required=False)
    learning_speed = serializers.IntegerField(required=False)
    learning_style = serializers.CharField(required=False)
    curiosity_level = serializers.IntegerField(required=False)
    persistence_level = serializers.IntegerField(required=False)
    autonomy_level = serializers.IntegerField(required=False)


class LLMAnswerSerializer(serializers.Serializer):
    question_index = serializers.IntegerField()
    chosen_index = serializers.IntegerField()
    reasoning = serializers.CharField()


class QuizSimulationResultSerializer(serializers.Serializer):
    result_id = serializers.IntegerField(required=False)
    twin_id = serializers.IntegerField()
    twin_name = serializers.CharField()
    quiz_id = serializers.IntegerField()
    quiz_title = serializers.CharField()
    simulated_score = serializers.FloatField()
    correct = serializers.IntegerField()
    total = serializers.IntegerField()
    simulated_time_seconds = serializers.IntegerField()
    passed = serializers.BooleanField()
    feedback = serializers.CharField()
    llm_answers = LLMAnswerSerializer(many=True, required=False)
    behavior_snapshot = BehaviorSnapshotSerializer()


class CourseSimulationResultSerializer(serializers.Serializer):
    result_id = serializers.IntegerField(required=False)
    twin_id = serializers.IntegerField()
    twin_name = serializers.CharField()
    course_id = serializers.IntegerField()
    course_title = serializers.CharField()
    simulated_score = serializers.FloatField()
    simulated_time_seconds = serializers.IntegerField()
    feedback = serializers.CharField()
    behavior_snapshot = BehaviorSnapshotSerializer()


class SimulationResultSerializer(serializers.ModelSerializer):
    twin_name = serializers.CharField(source="twin.name", read_only=True)
    quiz_title = serializers.CharField(
        source="quiz.title", read_only=True, default=None
    )
    course_title = serializers.CharField(
        source="course.title", read_only=True, default=None
    )

    class Meta:
        model = SimulationResult
        fields = [
            "id",
            "simulation_type",
            "twin_name",
            "quiz_title",
            "course_title",
            "simulated_score",
            "simulated_time_seconds",
            "passed",
            "correct",
            "total",
            "feedback",
            "behavior_snapshot",
            "created_at",
        ]
        read_only_fields = fields
