from rest_framework import serializers
from .models import User,EducationalProfile
from django.contrib.auth.password_validation import validate_password

class EducationalProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationalProfile
        fields = [
            "school",
            "diploma",
            "institution_type",
            "education_level",
            "experience_years"
        ]
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    educational_profile = EducationalProfileSerializer(required=False)
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'profile_picture', 'birthdate',
            'role', 
            'password', 'educational_profile'
        ]
    def get_role(self, obj):
        return obj.role.name

    def create(self, validated_data):
        edu_data = validated_data.pop("educational_profile", None)

        user = User(
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            profile_picture=validated_data.get('profile_picture'),
            birthdate=validated_data.get('birthdate'),
            is_active=False 
        )

        user.set_password(validated_data['password'])
        user.save()

        # 👇 CREATE EDUCATIONAL PROFILE
        if edu_data:
            EducationalProfile.objects.create(user=user, **edu_data)

        return user
    
    def update(self, instance, validated_data):
        edu_data = validated_data.pop("educational_profile", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if edu_data:
            profile, _ = EducationalProfile.objects.get_or_create(user=instance)
            for attr, value in edu_data.items():
                setattr(profile, attr, value)
            profile.save()

        return instance
