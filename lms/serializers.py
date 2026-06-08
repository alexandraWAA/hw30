from rest_framework import serializers
from lms.models import Course, Lesson, Subscription
from lms.validators import validate_youtube_url


class LessonSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели урока
    """
    course_name = serializers.CharField(source='course.name', read_only=True)

    class Meta:
        model = Lesson
        fields = [
            'id', 'name', 'description', 'preview',
            'video_url', 'course', 'course_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LessonCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания/обновления урока с валидацией
    """

    class Meta:
        model = Lesson
        fields = ['name', 'description', 'preview', 'video_url', 'course']

    def validate_video_url(self, value):
        """
        Валидация ссылки на видео через функцию-валидатор
        """
        validate_youtube_url(value)
        return value


class CourseSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели курса с выводом уроков и признаком подписки
    """
    lessons_count = serializers.SerializerMethodField()
    lessons = LessonSerializer(many=True, read_only=True)
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'name', 'preview', 'description',
            'lessons_count', 'lessons', 'is_subscribed',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_lessons_count(self, obj):
        """Количество уроков в курсе"""
        return obj.lessons.count()

    def get_is_subscribed(self, obj):
        """
        Проверка, подписан ли текущий пользователь на курс
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(
                user=request.user,
                course=obj
            ).exists()
        return False


class CourseCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания/обновления курса
    """

    class Meta:
        model = Course
        fields = ['name', 'preview', 'description']


class SubscriptionSerializer(serializers.ModelSerializer):
    """
    Сериализатор для подписки
    """
    course_name = serializers.CharField(source='course.name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Subscription
        fields = ['id', 'user', 'user_email', 'course', 'course_name', 'created_at']
        read_only_fields = ['id', 'created_at']


class PaymentSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели платежа
    """
    user_email = serializers.CharField(source='user.email', read_only=True)
    course_name = serializers.CharField(source='course.name', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'user', 'user_email', 'course', 'course_name',
            'amount', 'stripe_session_id', 'stripe_payment_intent_id',
            'payment_url', 'status', 'created_at', 'paid_at'
        ]
        read_only_fields = ['id', 'created_at', 'paid_at', 'stripe_session_id', 'payment_url']


class PaymentCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания платежа
    """

    class Meta:
        model = Payment
        fields = ['course', 'amount']

    def validate_course(self, value):
        """Проверка, что курс существует и имеет цену"""
        if value.price <= 0:
            raise serializers.ValidationError('У данного курса нет установленной цены')
        return value


class PaymentStatusSerializer(serializers.Serializer):
    """
    Сериализатор для проверки статуса платежа
    """
    session_id = serializers.CharField()