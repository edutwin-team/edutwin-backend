from rest_framework import serializers
from .models import PedagogicalContext, Objective


class ObjectiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Objective
        fields = ["id", "label"]


class PedagogicalContextSerializer(serializers.ModelSerializer):
    objectives = ObjectiveSerializer(many=True)

    twins = serializers.SerializerMethodField()

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
            "twins",
        ]
        read_only_fields = ["user"]

    def get_twins(self, obj):
        return 0

    def create(self, validated_data):
        objectives_data = validated_data.pop("objectives", [])

        context = PedagogicalContext.objects.create(**validated_data)

        for objective_data in objectives_data:
            Objective.objects.create(
                context=context,
                **objective_data
            )

        return context
    
    def update(self, instance, validated_data):
        objectives_data = validated_data.pop("objectives", None)

        # update context fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if objectives_data is not None:
            # delete old objectives
            instance.objectives.all().delete()

            # recreate objectives
            for obj in objectives_data:
                Objective.objects.create(
                    context=instance,
                    **obj
                )

        return instance