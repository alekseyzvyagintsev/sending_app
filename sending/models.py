###############################################################################################################
import datetime

from django.db import models
from django.db.models import CASCADE
from django.utils import timezone

from users.models import CustomUser


class MessageRecipient(models.Model):
    email = models.EmailField(unique=True)
    fullname = models.CharField(max_length=50)
    comment = models.TextField()
    owner = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, verbose_name="Владелец получателя", blank=True, null=True
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.fullname} - {self.email} - {self.comment}"

    class Meta:
        verbose_name = "Получатель"
        verbose_name_plural = "Получатели"
        db_table = "recipient"
        permissions = [
            ("can_deactivate_recipient", "can_deactivate_recipient"),
            ("can_add_recipient", "can_add_recipient"),
            ("can_view_recipient", "can_view_recipient"),
            ("can_change_recipient", "can_change_recipient"),
            ("can_delete_recipient", "can_delete_recipient"),
        ]


class Message(models.Model):
    subject = models.CharField(max_length=50, verbose_name="Тема сообщения")
    body_text = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(CustomUser, on_delete=CASCADE, verbose_name="Владелец сообщения", blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Тема: {self.subject}. Содержание: {self.body_text}"

    class Meta:
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"
        db_table = "message"
        permissions = [
            ("can_block_message", "can_block_message"),
        ]


class Mailing(models.Model):
    """
    Класс для управления массовой рассылкой сообщений.
    """

    STATUS_CHOICES = [
        ("CREATED", "Создана"),
        ("STARTED", "Запущена"),
        ("COMPLETED", "Завершена"),
    ]

    start_sending = models.DateTimeField(blank=True, null=True, verbose_name="Дата начала рассылки")
    stop_sending = models.DateTimeField(blank=True, null=True, verbose_name="Дата завершения рассылки")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="CREATED")
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="mailings")
    recipients = models.ManyToManyField(MessageRecipient)
    owner = models.ForeignKey(CustomUser, on_delete=CASCADE, verbose_name="Владелец рассылки", blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        # Локализуем дату начала и окончания рассылки
        start_localized = timezone.localtime(self.start_sending) if self.start_sending else None
        stop_localized = timezone.localtime(self.stop_sending) if self.stop_sending else None

        return f"""
        Рассылка № {self.id}:
        Старт:
            {start_localized.strftime('%d.%m.%Y %H:%M') if isinstance(start_localized, datetime.datetime) else '-'},
        Окончание:
            {stop_localized.strftime('%d.%m.%Y %H:%M') if isinstance(stop_localized, datetime.datetime) else '-'},
        Статус: {self.get_status_display()}
        """

    class Meta:
        verbose_name = "Рассылка"
        verbose_name_plural = "Рассылки"
        ordering = ["start_sending", "status", "is_active"]
        db_table = "mailing"
        permissions = [
            ("can_block_mailing", "can_block_mailing"),
        ]


class MailingAttempt(models.Model):
    """
    Класс для контроля успешности рассылок сообщений.
    """

    STATUS_CHOICES = [
        ("SUCCESSFULLY", "Успешно"),
        ("UNSUCCESSFULLY", "Неуспешно"),
    ]

    attempted_at = models.DateTimeField(auto_now_add=True)
    end_at = models.DateTimeField(blank=True, null=True)
    recipient = models.ForeignKey(
        MessageRecipient, on_delete=models.CASCADE, related_name="recipient_attempts", blank=True, null=True
    )
    owner = models.ForeignKey(
        CustomUser, on_delete=CASCADE, related_name="owner_attempts", default=1, verbose_name="Владелец попытки"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="SUCCESSFULLY")
    server_response = models.TextField(blank=True, null=True)
    mailing = models.ForeignKey(
        Mailing, on_delete=CASCADE, verbose_name="Рассылка", related_name="attempt_set", blank=True, null=True
    )

    def __str__(self):
        return f"""
        Email получателя - {self.recipient.email},\n
        статус отправки {self.get_status_display()}.\n
        Попытка принадлежит рассылке № {self.mailing.id}.
        """

    class Meta:
        unique_together = ["mailing", "recipient"]
        verbose_name = "Попытка рассылки"
        verbose_name_plural = "Попытки рассылок"
        ordering = [
            "attempted_at",
        ]
        db_table = "mailing_attempt"
        permissions = [
            ("can_block_mailing_attempt", "can_block_mailing_attempt"),
            ("can_add_mailing_attempt", "can_add_mailing_attempt"),
            ("can_view_mailing_attempt", "can_view_mailing_attempt"),
            ("can_change_mailing_attempt", "can_change_mailing_attempt"),
            ("can_delete_mailing_attempt", "can_delete_mailing_attempt"),
        ]


###############################################################################################################
