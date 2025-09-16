###############################################################################################################
from django.db import models
from django.db.models import CASCADE

from users.models import CustomUser


class MessageRecipient(models.Model):
    email = models.EmailField(unique=True)
    fullname = models.CharField(max_length=50)
    comment = models.TextField()

    def __str__(self):
        return f'Получатель: {self.fullname} - {self.email}'


class Message(models.Model):
    subject = models.CharField(max_length=50, verbose_name='Тема сообщения')
    body_text = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(CustomUser, on_delete=CASCADE, verbose_name='Владелец рассылки', blank=True, null=True)

    def __str__(self):
        return f'Тема - "{self.subject}",\nСодержание: {self.body_text}'

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'


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
    is_active = models.BooleanField(verbose_name='Заблокирована/Не заблокирована', default=True)


    def __str__(self):
        return f"""
        Рассылка {self.is_active}:\n
        Статус: {self.status},\n
        Начало рассылки: {self.start_sending},\n
        Окончание рассылки: {self.start_sending}
        """
    class Meta:
        verbose_name = 'Рассылка'
        verbose_name_plural = 'Рассылки'
        ordering = ["start_sending", "status", "is_active"]
        db_table = "mailing"
        permissions = [('block_mailing', 'Блокировка рассылки'),]


class MailingAttempt(models.Model):
    """
    Класс для контроля успешности рассылок сообщений.
    """
    STATUS_CHOICES = [
        ('SUCCESSFULLY', 'Успешно'),
        ('NOT SUCCESSFUL', 'Запущена'),
    ]

    date_attempt = models.DateTimeField(max_length=20, choices=STATUS_CHOICES, default='SUCCESSFULLY')
    server_response = models.TextField(blank=True, null=True)
    mailing = models.ForeignKey(Mailing, on_delete=CASCADE, verbose_name='Рассылка', blank=True, null=True)


###############################################################################################################
