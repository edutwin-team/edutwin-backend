from django.contrib import admin

from django.contrib import admin
from .models import PedagogicalContext, Objective, DigitalTwin, Behavior


class PedagogicalContextAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'level', 'school', 'country', 'academic_year')
    ordering = ('name',)
    search_fields = ('name', 'subject', 'school', 'country')

    fieldsets = (
        (None, {'fields': ('user', 'name')}),
        ('Details', {'fields': ('subject', 'level', 'school', 'country', 'academic_year', 'description')}),
    )


class ObjectiveAdmin(admin.ModelAdmin):
    list_display = ('label', 'context')
    ordering = ('label',)
    search_fields = ('label',)

    fieldsets = (
        (None, {'fields': ('context', 'label')}),
    )


class DigitalTwinAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'context', 'age', 'average_grade', 'created_at')
    ordering = ('name',)
    search_fields = ('name',)

    fieldsets = (
        (None, {'fields': ('user', 'context', 'name')}),
        ('Info', {'fields': ('age', 'average_grade', 'description')}),
        ('Important dates', {'fields': ('created_at',)}),
    )

    readonly_fields = ('created_at',)


class BehaviorAdmin(admin.ModelAdmin):
    list_display = ('twin', 'comprehension_level', 'motivation', 'learning_speed', 'error_rate', 'learning_style')
    ordering = ('twin',)
    search_fields = ('twin__name',)

    fieldsets = (
        (None, {'fields': ('twin',)}),
        ('Learning Profile', {'fields': ('learning_style', 'preferred_content_type', 'comprehension_level', 'learning_speed', 'error_rate')}),
        ('Emotional State', {'fields': ('motivation', 'fatigue_level', 'attention_level', 'stress_level')}),
        ('Personal Traits', {'fields': ('curiosity_level', 'autonomy_level', 'persistence_level', 'memory_retention')}),
        ('Other', {'fields': ('question_frequency', 'comment')}),
    )


admin.site.register(PedagogicalContext, PedagogicalContextAdmin)
admin.site.register(Objective, ObjectiveAdmin)
admin.site.register(DigitalTwin, DigitalTwinAdmin)
admin.site.register(Behavior, BehaviorAdmin)