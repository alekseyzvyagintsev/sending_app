##############################################################################################################
import datetime
import uuid

from django.core.mail import send_mail
from django.urls import reverse
from django.utils.timezone import now

from sending_app import settings


def generate_random_token():
    # Генерация случайного токена.
    return str(uuid.uuid4())

def create_and_save_token(user):
    """
    Создание и сохранение токена с указанием срока годности.
    """
    token = generate_random_token()
    expiration_time = now() + datetime.timedelta(hours=24)  # Действует сутки
    user.activation_token = token
    user.token_expires_at = expiration_time
    user.save(update_fields=['activation_token', 'token_expires_at'])
    return token

def send_confirmation_email(self, user):
    """Отправляет электронное письмо с инструкциями по подтверждению."""
    try:
        # Генерируем и сохраняем токен
        token = create_and_save_token(user)
        # Создаем активационную ссылку перед отправкой.
        activation_link = self.request.build_absolute_uri(
            reverse('users:activate', args=(user.id, token)))
        # Генерируем сообщение со ссылкой перед отправкой
        subject = 'Подтверждение вашего аккаунта'
        message = f'''Привет {user.username}, пожалуйста перейдите по ссылке для завершения регистрации:\n\n
        {activation_link}\n\nСпасибо!'''
        # Отправляем письмо
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email,], fail_silently=False)
    except Exception as e:
        print(e)

def send_activation_email(user):
    # Отправка приветственного письма
    subject = 'Добро пожаловать в наш сервис'
    message = 'Спасибо, что зарегистрировались в нашем сервисе!'
    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [user.email],
        fail_silently=False
    )

##############################################################################################################
