######################################################################################
import logging
import smtplib

# from apscheduler.schedulers.background import BackgroundScheduler
from django.core.mail import send_mail
from django.db import IntegrityError
from django.utils import timezone
# from django_apscheduler.jobstores import DjangoJobStore

from email_validator import validate_email, EmailNotValidError


from sending_app import settings
from sending.models import Mailing, MailingAttempt

logger = logging.getLogger(__name__)
# # Создаем экземпляр планировщика
# scheduler = BackgroundScheduler()
# scheduler.add_jobstore(DjangoJobStore(), 'djangojobstore')


# def create_attempt(mailing_id=None):
#     if mailing_id is None:
#         raise ValueError("Требуется аргумент mailing_id")
#     mailing = Mailing.objects.get(id=mailing_id)
#     attempt = MailingAttempt(mailing=mailing)
#     attempt.save()
#     return attempt


def perform_send(mailing_id):
    mailing = Mailing.objects.get(id=mailing_id)
    print(f"Объект рассылки по id: {mailing.id} - {mailing}")
    mailing.status = 'STARTED'
    mailing.save()
    print(f"Установили {mailing.status}")
    recipients = mailing.recipients.all()
    print(f"Получатели из рассылки {recipients}")

    if not recipients:
        print('Список получателей пуст')
        return None

    attempts = []
    successful_count = 0
    failed_count = 0

    for recipient in recipients:
        try:
            attempt = MailingAttempt(mailing=mailing, recipient=recipient, end_at=timezone.now())
            attempt.save()
            print(f"Создали объект попытки {attempt}")
            try:
                validation_result = validate_email(recipient.email)
                normalized_email = validation_result.normalized  # Используем нормализованный адрес
                recipient.email = normalized_email  # Нормализация email-адреса
            except EmailNotValidError as e:
                print(f"Некорректный email адрес: {str(e)}")
                attempt.server_response = f"Invalid email address: {str(e)}"
                attempt.status = 'UNSUCCESSFULLY'
                attempt.save()
                print(f"Status: {attempt.status}, Server response: {attempt.server_response}, End at: {attempt.end_at}")
                failed_count += 1
                continue  # Переходим к следующему получателю
            try:
                send_mail(
                    subject=f"{mailing.message.subject}",
                    message=f"Здравствуйте {recipient.fullname}. {mailing.message.body_text}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient.email],
                    fail_silently=False
                )
                print(f"Отправлено письмо получателю {recipient}")
                attempt.status = 'SUCCESSFULLY'
                successful_count += 1
            except smtplib.SMTPException as e:
                print(f"Ошибка отправки SMTP: {str(e)}")
                attempt.server_response = str(e)
                attempt.status = 'UNSUCCESSFULLY'
                failed_count += 1
            except Exception as e:
                print(f"Возникла ошибка во время отправки письма: {str(e)}")
                attempt.server_response = str(e)
                attempt.status = 'UNSUCCESSFULLY'
                failed_count += 1
            finally:
                attempt.save()
                attempts.append(attempt)
                print(f"Status: {attempt.status}, Server response: {attempt.server_response}, End at: {attempt.end_at}")
        except IntegrityError:
            failed_count += 1

    mailing.status = 'COMPLETED'
    mailing.save()
    print(f"Рассылка завершена. Всего успешных отправок: {successful_count}, неудачных: {failed_count}")
    return successful_count, failed_count, attempts

def sender(mailing_id=None):
    if mailing_id is None:
        raise ValueError("Требуется аргумент mailing_id")
    logger.debug(f"Отправка началась для рассылки с ID: {mailing_id}")
    result = perform_send(mailing_id)
    successful_count, failed_count, attempts = result
    return successful_count, failed_count, attempts

#
#
# # Основная задача рассылки email каждые 6 часов
# def sending_planner(mailing_id=None):
#     if mailing_id is None:
#         raise ValueError("Требуется аргумент mailing_id")
#     scheduler.add_job(sending_planner, trigger='interval', hours=6, args=[mailing_id])
#     logger.debug(f"Задача отправки запущена для рассылки с ID: {mailing_id}")
#     try:
#         sender(mailing_id)
#     except Exception as e:
#         logger.error(f"Произошла ошибка во время отправки письма: {e}")
#
#
# # Запускаем планировщик
# try:
#     scheduler.start()
#     logger.info("Запущен планировщик.")
#
#     # Для удержания процесса открытым
#     import time
#
#     while True:
#         time.sleep(1)
# except KeyboardInterrupt:
#     logger.info("Остановка планировщика.")
#     scheduler.shutdown()


######################################################################################
