from rest_framework import serializers
from users.models import User, Payment
from lms.serializers import CourseSerializer, LessonSerializer


class UserSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели пользователя
    """

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'phone', 'city', 'avatar', 'date_joined'
        ]
        read_only_fields = ['id', 'date_joined']


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания пользователя
    """
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'password', 'first_name', 'last_name',
            'phone', 'city', 'avatar'
        ]

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обновления профиля пользователя
    """

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone', 'city', 'avatar'
        ]


class PaymentSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели платежа
    """
    user_email = serializers.CharField(source='user.email', read_only=True)
    course_name = serializers.CharField(source='course.name', read_only=True, allow_null=True)
    lesson_name = serializers.CharField(source='lesson.name', read_only=True, allow_null=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'user', 'user_email', 'payment_date',
            'course', 'course_name', 'lesson', 'lesson_name',
            'amount', 'payment_method', 'created_at'
        ]
        read_only_fields = ['id', 'payment_date', 'created_at']


class PaymentCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания платежа
    """

    class Meta:
        model = Payment
        fields = ['user', 'course', 'lesson', 'amount', 'payment_method']

    def validate(self, data):
        """Проверка, что указан либо курс, либо урок"""
        if not data.get('course') and not data.get('lesson'):
            raise serializers.ValidationError('Должен быть указан либо курс, либо урок')
        if data.get('course') and data.get('lesson'):
            raise serializers.ValidationError('Нельзя указать одновременно курс и урок')
        return data


class UserWithPaymentsSerializer(UserSerializer):
    """
    * Дополнительное задание: Расширенный сериализатор пользователя с историей платежей
    """
    payments = PaymentSerializer(many=True, read_only=True)
    total_spent = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ['payments', 'total_spent']

    def get_total_spent(self, obj):
        """Общая сумма всех платежей пользователя"""
        return obj.payments.aggregate(total=models.Sum('amount'))['total'] or 0