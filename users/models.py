from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator


class Payment(models.Model):
    """
    Модель платежа
    """
    CASH = 'cash'
    TRANSFER = 'transfer'

    PAYMENT_METHOD_CHOICES = [
        (CASH, 'Наличные'),
        (TRANSFER, 'Перевод на счет'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name='Пользователь'
    )
    payment_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата оплаты'
    )
    course = models.ForeignKey(
        'lms.Course',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='payments',
        verbose_name='Оплаченный курс'
    )
    lesson = models.ForeignKey(
        'lms.Lesson',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='payments',
        verbose_name='Оплаченный урок'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Сумма оплаты'
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        verbose_name='Способ оплаты'
    )

    # created_at - УДАЛЕНО, так как payment_date уже выполняет эту функцию

    class Meta:
        verbose_name = 'Платеж'
        verbose_name_plural = 'Платежи'
        ordering = ['-payment_date']

    def __str__(self):
        target = self.course if self.course else self.lesson
        return f"Платеж {self.user.email} - {target} - {self.amount} руб."

    def clean(self):
        """Проверка, что оплачен либо курс, либо урок"""
        if not self.course and not self.lesson:
            raise ValueError('Должен быть оплачен либо курс, либо урок')
        if self.course and self.lesson:
            raise ValueError('Нельзя оплатить одновременно курс и урок')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)