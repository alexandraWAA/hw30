from django.urls import path, include
from rest_framework.routers import DefaultRouter
from lms.views import (
    CourseViewSet, LessonListCreateView, LessonRetrieveUpdateDeleteView,
    LessonsByCourseView, SubscriptionView
)

router = DefaultRouter()
router.register(r'courses', CourseViewSet, basename='course')

urlpatterns = [
    path('', include(router.urls)),

    # CRUD для уроков
    path('lessons/', LessonListCreateView.as_view(), name='lesson-list-create'),
    path('lessons/<int:pk>/', LessonRetrieveUpdateDeleteView.as_view(), name='lesson-detail'),

    # Уроки по курсу
    path('courses/<int:course_id>/lessons/', LessonsByCourseView.as_view(), name='course-lessons'),

    # Подписка на курс
    path('subscribe/', SubscriptionView.as_view(), name='subscription'),
]