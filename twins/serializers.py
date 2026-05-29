from rest_framework import serializers
from .models import PedagogicalContext, Objective


class ObjectiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Objective
        fields = ["id", "label"]


class PedagogicalContextSerializer(serializers.ModelSerializer):
    objectives = ObjectiveSerializer(many=True)

    class Meta:
        model = PedagogicalContext
        fields = [
            "id",
            "user",
            "name",
            "subject",
            "level",
            "school",
            "country",
            "academic_year",
            "description",
            "objectives",
        ]
        read_only_fields = ["user"]

    def create(self, validated_data):
        objectives_data = validated_data.pop("objectives", [])

        context = PedagogicalContext.objects.create(**validated_data)

        for objective_data in objectives_data:
            Objective.objects.create(
                context=context,
                **objective_data
            )

        return context