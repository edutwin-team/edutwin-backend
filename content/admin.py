from django.contrib import admin

from django.contrib import admin
from .models import Course, Quiz, Question, Answer


class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'source_type', 'created_at', 'updated_at')
    ordering = ('title',)
    search_fields = ('title', 'user__email')

    fieldsets = (
        (None, {'fields': ('user', 'title')}),
        ('Content', {'fields': ('description', 'content', 'source_type')}),
        ('Important dates', {'fields': ('created_at', 'updated_at')}),
    )

    readonly_fields = ('created_at', 'updated_at')


class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'course', 'passing_score', 'time_limit_minutes', 'source_type', 'created_at')
    ordering = ('title',)
    search_fields = ('title', 'user__email')

    fieldsets = (
        (None, {'fields': ('user', 'course', 'title')}),
        ('Details', {'fields': ('description', 'passing_score', 'time_limit_minutes', 'source_type')}),
        ('Important dates', {'fields': ('created_at', 'updated_at')}),
    )

    readonly_fields = ('created_at', 'updated_at')


class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'quiz', 'question_type', 'difficulty_level')
    ordering = ('quiz',)
    search_fields = ('text',)

    fieldsets = (
        (None, {'fields': ('quiz', 'text')}),
        ('Settings', {'fields': ('question_type', 'difficulty_level')}),
    )


class AnswerAdmin(admin.ModelAdmin):
    list_display = ('text', 'question', 'is_correct')
    ordering = ('question',)
    search_fields = ('text',)

    fieldsets = (
        (None, {'fields': ('question', 'text', 'is_correct')}),
    )


admin.site.register(Course, CourseAdmin)
admin.site.register(Quiz, QuizAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Answer, AnswerAdmin)
