from rest_framework import serializers
from .models import Course, Quiz, Question, Answer



class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ["id", "text", "is_correct"]


class QuestionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "text",
            "question_type",
            "difficulty_level",
            "answers",
        ]


class QuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True)

    class Meta:
        model = Quiz
        fields = [
            "id",
            "title",
            "description",
            "passing_score",
            "time_limit_minutes",
            "source_type",
            "course",
            "questions",
            "created_at",
        ]
        read_only_fields = ["created_at"]


    def create(self, validated_data):
        questions_data = validated_data.pop("questions", [])

        quiz = Quiz.objects.create(**validated_data)

        for q_data in questions_data:
            answers_data = q_data.pop("answers", [])

            question = Question.objects.create(quiz=quiz, **q_data)

            for a_data in answers_data:
                Answer.objects.create(question=question, **a_data)

        return quiz


    def update(self, instance, validated_data):
        questions_data = validated_data.pop("questions", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        #recreate questino and answere for each quiz
        #todo : voi si on change vers une meilleur solution aprés
        if questions_data is not None:
            instance.questions.all().delete()

            for q_data in questions_data:
                answers_data = q_data.pop("answers", [])

                question = Question.objects.create(quiz=instance, **q_data)

                for a_data in answers_data:
                    Answer.objects.create(question=question, **a_data)

        return instance






class AnswerSubmitSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    answer_id = serializers.IntegerField()


class QuizSubmitSerializer(serializers.Serializer):
    answers = AnswerSubmitSerializer(many=True)

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "description",
            "content",
            "source_type",
            "created_at",
            "updated_at",
        ]
