# from rest_framework import serializers
# from ..twins.models import Twin, TwinSimulation


# class TwinSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Twin
#         fields = [
#             "id",
#             "name",
#             "level",
#             "reading_speed",
#             "strong_domains",
#             "weak_domains",
#             "reading_speed",
#             "created_at",
#         ]


# class TwinSimulationSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = TwinSimulation
#         fields = [
#             "id",
#             "twin",
#             "content_type",
#             "content_id",
#             "simulated_score",
#             "simulated_time_seconds",
#             "difficulty_perception",
#             "llm_feedback",
#             "created_at",
#         ]
#         read_only_fields = [
#             "simulated_score",
#             "simulated_time_seconds",
#             "difficulty_perception",
#             "llm_feedback",
#         ]
