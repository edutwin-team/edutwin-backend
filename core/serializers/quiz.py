from rest_framework import serializers
from core.models import QuizAttempt


class StartQuizInputSerializer(serializers.Serializer):
    quiz_id = serializers.IntegerField(help_text="The ID of the quiz to start")


class GradeQuizInputSerializer(serializers.Serializer):
    user_answers = serializers.DictField(
        child=serializers.IntegerField(allow_null=True),
        help_text="Dictionary mapping question_id to choice_id. Example: {'1': 4, '2': None}",
    )


class QuizAttemptOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizAttempt
        fields = ["id", "quiz", "user", "score", "completed_at", "is_completed"]
