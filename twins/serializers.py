from rest_framework import serializers
from .models import PedagogicalContext, Objective,DigitalTwin,Behavior


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
        return DigitalTwin.objects.filter(context=obj).count()

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

class BehaviorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Behavior
        fields = [
            "id",
            "comprehension_level",
            "motivation",
            "learning_speed",
            "error_rate",
            "learning_style",
            "fatigue_level",
            "attention_level",
            "stress_level",
            "curiosity_level",
            "autonomy_level",
            "persistence_level",
            "memory_retention",
            "preferred_content_type",
            "question_frequency",
            "comment",
        ]

class DigitalTwinSerializer(serializers.ModelSerializer):
    behavior = BehaviorSerializer(required=False)
    context_name = serializers.CharField(source='context.name', read_only=True)

    class Meta:
        model = DigitalTwin
        fields = [
            "id",
            "context",
            "context_name", 
            "name",
            "age",
            "average_grade",
            "description",
            "behavior",
        ]
        read_only_fields = ["user"]

    def create(self, validated_data):
        behavior_data = validated_data.pop("behavior", None)

        twin = DigitalTwin.objects.create(**validated_data)

        if behavior_data:
            Behavior.objects.create(twin=twin, **behavior_data)

        return twin

    def update(self, instance, validated_data):
        behavior_data = validated_data.pop("behavior", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if behavior_data:
            Behavior.objects.update_or_create(
                twin=instance,
                defaults=behavior_data
            )

        return instance
    