from rest_framework import viewsets, generics
from lms.models import Course, Lesson
from lms.serializers import (
    CourseSerializer, CourseCreateUpdateSerializer,
    LessonSerializer, LessonCreateUpdateSerializer
)


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.prefetch_related('lessons').all()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CourseCreateUpdateSerializer
        return CourseSerializer


class LessonListCreateView(generics.ListCreateAPIView):
    queryset = Lesson.objects.select_related('course').all()

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return LessonCreateUpdateSerializer
        return LessonSerializer


class LessonRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Lesson.objects.select_related('course').all()

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return LessonCreateUpdateSerializer
        return LessonSerializer


class LessonsByCourseView(generics.ListAPIView):
    serializer_class = LessonSerializer

    def get_queryset(self):
        course_id = self.kwargs.get('course_id')
        return Lesson.objects.filter(course_id=course_id).select_related('course')