from rest_framework import viewsets, generics
from lms.models import Course, Lesson
from lms.serializers import (
    CourseSerializer, CourseCreateUpdateSerializer,
    LessonSerializer, LessonCreateUpdateSerializer
)


class CourseViewSet(viewsets.ModelViewSet):
    """
    ViewSet для CRUD операций с курсами
    """
    queryset = Course.objects.all()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CourseCreateUpdateSerializer
        return CourseSerializer


class LessonListCreateView(generics.ListCreateAPIView):
    """
    Generic класс для получения списка уроков и создания нового урока
    GET /api/lms/lessons/ - список всех уроков
    POST /api/lms/lessons/ - создание нового урока
    """
    queryset = Lesson.objects.select_related('course').all()

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return LessonCreateUpdateSerializer
        return LessonSerializer


class LessonRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    """
    Generic класс для получения, обновления и удаления одного урока
    GET /api/lms/lessons/<id>/ - получение урока
    PUT /api/lms/lessons/<id>/ - полное обновление урока
    PATCH /api/lms/lessons/<id>/ - частичное обновление урока
    DELETE /api/lms/lessons/<id>/ - удаление урока
    """
    queryset = Lesson.objects.select_related('course').all()

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return LessonCreateUpdateSerializer
        return LessonSerializer


class LessonsByCourseView(generics.ListAPIView):
    """
    Дополнительный эндпоинт: список уроков по конкретному курсу
    GET /api/lms/courses/<course_id>/lessons/
    """
    serializer_class = LessonSerializer

    def get_queryset(self):
        course_id = self.kwargs.get('course_id')
        return Lesson.objects.filter(course_id=course_id).select_related('course')