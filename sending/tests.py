import datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from sending.models import Mailing, MailingAttempt, Message, MessageRecipient

User = get_user_model()


class MessageModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="testuser@example.com", password="testpass123", username="testuser")
        self.message = Message.objects.create(subject="Test Subject", body_text="Test message body", owner=self.user)

    def test_message_creation(self):
        self.assertEqual(self.message.subject, "Test Subject")
        self.assertEqual(self.message.body_text, "Test message body")
        self.assertEqual(self.message.owner, self.user)
        self.assertTrue(self.message.is_active)

    def test_message_str_representation(self):
        expected_str = f"Тема: {self.message.subject}. Содержание: {self.message.body_text}"
        self.assertEqual(str(self.message), expected_str)


class MessageRecipientModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="testuser@example.com", password="testpass123", username="testuser")
        self.recipient = MessageRecipient.objects.create(
            email="recipient@example.com", fullname="Test Recipient", comment="Test comment", owner=self.user
        )

    def test_recipient_creation(self):
        self.assertEqual(self.recipient.email, "recipient@example.com")
        self.assertEqual(self.recipient.fullname, "Test Recipient")
        self.assertEqual(self.recipient.comment, "Test comment")
        self.assertEqual(self.recipient.owner, self.user)
        self.assertTrue(self.recipient.is_active)

    def test_recipient_str_representation(self):
        expected_str = f"{self.recipient.fullname} - {self.recipient.email} - {self.recipient.comment}"
        self.assertEqual(str(self.recipient), expected_str)


class MailingModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="testuser@example.com", password="testpass123", username="testuser")
        self.message = Message.objects.create(subject="Test Subject", body_text="Test message body", owner=self.user)
        self.recipient1 = MessageRecipient.objects.create(
            email="recipient1@example.com", fullname="Test Recipient 1", comment="Test comment 1", owner=self.user
        )
        self.recipient2 = MessageRecipient.objects.create(
            email="recipient2@example.com", fullname="Test Recipient 2", comment="Test comment 2", owner=self.user
        )
        self.mailing = Mailing.objects.create(
            start_sending=timezone.now(),
            stop_sending=timezone.now() + timezone.timedelta(hours=1),
            message=self.message,
            owner=self.user,
        )
        self.mailing.recipients.add(self.recipient1, self.recipient2)

    def test_mailing_creation(self):
        self.assertEqual(self.mailing.message, self.message)
        self.assertEqual(self.mailing.owner, self.user)
        self.assertTrue(self.mailing.is_active)
        self.assertEqual(self.mailing.status, "CREATED")
        self.assertEqual(self.mailing.recipients.count(), 2)

    def test_mailing_str_representation(self):
        start_localized = timezone.localtime(self.mailing.start_sending)
        stop_localized = timezone.localtime(self.mailing.stop_sending)
        expected_str = f"""
        Рассылка № {self.mailing.id}:
        Старт:
            {start_localized.strftime('%d.%m.%Y %H:%M') if isinstance(start_localized, datetime.datetime) else '-'},
        Окончание:
            {stop_localized.strftime('%d.%m.%Y %H:%M') if isinstance(stop_localized, datetime.datetime) else '-'},
        Статус: {self.mailing.get_status_display()}
        """
        self.assertEqual(str(self.mailing).strip(), expected_str.strip())


class MailingAttemptModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="testuser@example.com", password="testpass123", username="testuser")
        self.message = Message.objects.create(subject="Test Subject", body_text="Test message body", owner=self.user)
        self.recipient = MessageRecipient.objects.create(
            email="recipient@example.com", fullname="Test Recipient", comment="Test comment", owner=self.user
        )
        self.mailing = Mailing.objects.create(
            start_sending=timezone.now(),
            stop_sending=timezone.now() + timezone.timedelta(hours=1),
            message=self.message,
            owner=self.user,
        )
        self.mailing.recipients.add(self.recipient)
        self.attempt = MailingAttempt.objects.create(mailing=self.mailing, recipient=self.recipient, owner=self.user)

    def test_attempt_creation(self):
        self.assertEqual(self.attempt.mailing, self.mailing)
        self.assertEqual(self.attempt.recipient, self.recipient)
        self.assertEqual(self.attempt.owner, self.user)
        self.assertEqual(self.attempt.status, "SUCCESSFULLY")
        self.assertIsNotNone(self.attempt.attempted_at)

    def test_attempt_str_representation(self):
        expected_str = f"""
        Email получателя - {self.attempt.recipient.email},\n
        статус отправки {self.attempt.get_status_display()}.\n
        Попытка принадлежит рассылке № {self.attempt.mailing.id}.
        """
        self.assertEqual(str(self.attempt).strip(), expected_str.strip())


class OperatorFunctionTest(TestCase):
    @patch("sending.operator.send_mail")
    def test_perform_send_success(self, mock_send_mail):
        mock_send_mail.return_value = 1

        user = User.objects.create_user(email="testuser@example.com", password="testpass123", username="testuser")
        message = Message.objects.create(subject="Test Subject", body_text="Test message body", owner=user)
        recipient = MessageRecipient.objects.create(
            email="recipient@example.com", fullname="Test Recipient", comment="Test comment", owner=user
        )
        mailing = Mailing.objects.create(
            start_sending=timezone.now(),
            stop_sending=timezone.now() + timezone.timedelta(hours=1),
            message=message,
            owner=user,
        )
        mailing.recipients.add(recipient)

        from sending.operator import perform_send

        result = perform_send(mailing.id)

        self.assertIsNotNone(result)
        successful_count, failed_count, attempts = result
        self.assertEqual(successful_count, 1)
        self.assertEqual(failed_count, 0)
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0].status, "SUCCESSFULLY")
        self.assertEqual(attempts[0].mailing, mailing)
        self.assertEqual(attempts[0].recipient, recipient)

    @patch("sending.operator.send_mail")
    def test_perform_send_smtp_error(self, mock_send_mail):
        mock_send_mail.side_effect = Exception("SMTP Error")

        user = User.objects.create_user(email="testuser@example.com", password="testpass123", username="testuser")
        message = Message.objects.create(subject="Test Subject", body_text="Test message body", owner=user)
        recipient = MessageRecipient.objects.create(
            email="recipient@example.com", fullname="Test Recipient", comment="Test comment", owner=user
        )
        mailing = Mailing.objects.create(
            start_sending=timezone.now(),
            stop_sending=timezone.now() + timezone.timedelta(hours=1),
            message=message,
            owner=user,
        )
        mailing.recipients.add(recipient)

        from sending.operator import perform_send

        result = perform_send(mailing.id)

        self.assertIsNotNone(result)
        successful_count, failed_count, attempts = result
        self.assertEqual(successful_count, 0)
        self.assertEqual(failed_count, 1)
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0].status, "UNSUCCESSFULLY")
        self.assertEqual(attempts[0].server_response, "SMTP Error")
        self.assertEqual(attempts[0].mailing, mailing)
        self.assertEqual(attempts[0].recipient, recipient)

    @patch("sending.operator.validate_email")
    @patch("sending.operator.send_mail")
    def test_perform_send_invalid_email(self, mock_send_mail, mock_validate_email):
        mock_validate_email.side_effect = Exception("Invalid email")

        user = User.objects.create_user(email="testuser@example.com", password="testpass123", username="testuser")
        message = Message.objects.create(subject="Test Subject", body_text="Test message body", owner=user)
        recipient = MessageRecipient.objects.create(
            email="invalid-email", fullname="Test Recipient", comment="Test comment", owner=user
        )
        mailing = Mailing.objects.create(
            start_sending=timezone.now(),
            stop_sending=timezone.now() + timezone.timedelta(hours=1),
            message=message,
            owner=user,
        )
        mailing.recipients.add(recipient)

        from sending.operator import perform_send

        result = perform_send(mailing.id)

        self.assertIsNotNone(result)
        successful_count, failed_count, attempts = result
        self.assertEqual(successful_count, 0)
        self.assertEqual(failed_count, 1)
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0].status, "UNSUCCESSFULLY")
        self.assertEqual(attempts[0].server_response, "Invalid email address: Invalid email")
        self.assertEqual(attempts[0].mailing, mailing)
        self.assertEqual(attempts[0].recipient, recipient)

    def test_sender_function(self):
        from sending.operator import sender

        user = User.objects.create_user(email="testuser@example.com", password="testpass123", username="testuser")
        message = Message.objects.create(subject="Test Subject", body_text="Test message body", owner=user)
        recipient = MessageRecipient.objects.create(
            email="recipient@example.com", fullname="Test Recipient", comment="Test comment", owner=user
        )
        mailing = Mailing.objects.create(
            start_sending=timezone.now(),
            stop_sending=timezone.now() + timezone.timedelta(hours=1),
            message=message,
            owner=user,
        )
        mailing.recipients.add(recipient)

        with self.assertRaises(ValueError):
            sender()

        with patch("sending.operator.perform_send") as mock_perform_send:
            mock_perform_send.return_value = (1, 0, [])
            result = sender(mailing.id)
            self.assertEqual(result, (1, 0, []))
            mock_perform_send.assert_called_once_with(mailing.id)
