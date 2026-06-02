from django.contrib import admin
from lms.models import Course, Lesson


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'created_at', 'updated_at']
    list_display_links = ['id', 'name']
    search_fields = ['name']
    list_filter = ['created_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'course', 'created_at', 'updated_at']
    list_display_links = ['id', 'name']
    search_fields = ['name', 'course__name']
    list_filter = ['course', 'created_at']
    readonly_fields = ['created_at', 'updated_at']