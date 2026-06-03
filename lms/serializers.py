from rest_framework import serializers
from lms.models import Course, Lesson


class LessonSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.name', read_only=True)

    class Meta:
        model = Lesson
        fields = [
            'id', 'name', 'description', 'preview',
            'video_url', 'course', 'course_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LessonCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ['name', 'description', 'preview', 'video_url', 'course']


class CourseSerializer(serializers.ModelSerializer):
    lessons_count = serializers.SerializerMethodField()
    lessons = LessonSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = [
            'id', 'name', 'preview', 'description',
            'lessons_count', 'lessons', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_lessons_count(self, obj):
        return obj.lessons.count()


class CourseCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['name', 'preview', 'description']