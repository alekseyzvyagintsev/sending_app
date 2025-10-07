###############################################################################################################
from django.utils import timezone

from django.db import models
from django.db.models import CASCADE

from users.models import CustomUser


class MessageRecipient(models.Model):
    email = models.EmailField(unique=True)
    fullname = models.CharField(max_length=50)
    comment = models.TextField()
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name='Владелец рассылки', blank=True,
                              null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.fullname} - {self.email} - {self.comment}'

    class Meta:
        verbose_name = 'Получатель'
        verbose_name_plural = 'Получатели'
        db_table = "recipient"
        permissions = [('deactivate_recipient', 'Деактивация получателя'), ]


class Message(models.Model):
    subject = models.CharField(max_length=50, verbose_name='Тема сообщения')
    body_text = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(CustomUser, on_delete=CASCADE, verbose_name='Владелец рассылки', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'Тема - "{self.subject}",\nСодержание: {self.body_text}'

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        db_table = "message"
        permissions = [('block_message', 'Блокировка сообщения'), ]


class Mailing(models.Model):
    """
    Класс для управления массовой рассылкой сообщений.
    """
    STATUS_CHOICES = [
        ('CREATED', 'Создана'),
        ('STARTED', 'Запущена'),
        ('COMPLETED', 'Завершена'),
    ]

    start_sending = models.DateTimeField(blank=True, null=True, verbose_name='Дата начала рассылки')
    stop_sending = models.DateTimeField(blank=True, null=True, verbose_name='Дата завершения рассылки')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='CREATED')
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='mailings')
    recipients = models.ManyToManyField(MessageRecipient)
    owner = models.ForeignKey(CustomUser, on_delete=CASCADE, verbose_name='Владелец рассылки', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        # Локализуем дату начала и окончания рассылки
        start_localized = timezone.localtime(self.start_sending) if self.start_sending else None
        stop_localized = timezone.localtime(self.stop_sending) if self.stop_sending else None

        return f"""
        Рассылка {self.is_active}:\n
        Статус: {self.status},\n
        Начало рассылки: {start_localized},\n
        Окончание рассылки: {stop_localized}
        """

    class Meta:
        verbose_name = 'Рассылка'
        verbose_name_plural = 'Рассылки'
        ordering = ["start_sending", "status", "is_active"]
        db_table = "mailing"
        permissions = [('block_mailing', 'Блокировка рассылки'), ]


class MailingAttempt(models.Model):
    """
    Класс для контроля успешности рассылок сообщений.
    """
    STATUS_CHOICES = [
        ('SUCCESSFULLY', 'Успешно'),
        ('UNSUCCESSFULLY', 'Неуспешно'),
    ]

    attempted_at = models.DateTimeField(auto_now_add=True)
    end_at = models.DateTimeField(blank=True, null=True)
    recipient = models.ForeignKey(MessageRecipient, on_delete=models.CASCADE, related_name='recipient_attempts',
                                  blank=True, null=True)
    owner = models.ForeignKey(MessageRecipient, on_delete=CASCADE, related_name='owner_attempts', default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUCCESSFULLY')
    server_response = models.TextField(blank=True, null=True)
    mailing = models.ForeignKey(Mailing, on_delete=CASCADE, verbose_name='Рассылка', blank=True, null=True)

    def __str__(self):
        return(f'Получатель - {self.recipient}, статус отправки {self.status}.')

    class Meta:
        unique_together = ['mailing', 'recipient']
        verbose_name = 'Попытка рассылки'
        verbose_name_plural = 'Попытки рассылок'
        ordering = ["attempted_at", ]
        db_table = "mailing_attempt"
        permissions = [('block_mailing_attempt', 'Блокировка попытки рассылки'), ]

###############################################################################################################
