from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

User = get_user_model()


class CustomUserModelTest(TestCase):
    def test_user_creation(self):
        user = User.objects.create_user(email="testuser@example.com", password="testpass123", username="testuser")
        user.is_active = False
        user.save()
        from users.utils import create_and_save_token

        create_and_save_token(user)

        self.assertEqual(user.email, "testuser@example.com")
        self.assertEqual(user.username, "testuser")
        self.assertTrue(user.check_password("testpass123"))
        self.assertFalse(user.is_active)
        self.assertIsNotNone(user.activation_token)
        self.assertIsNotNone(user.token_expires_at)

    def test_user_str_representation(self):
        user = User.objects.create_user(email="testuser@example.com", password="testpass123", username="testuser")
        self.assertEqual(str(user), "testuser@example.com")

    def test_user_activation(self):
        user = User.objects.create_user(email="testuser@example.com", password="testpass123", username="testuser")
        user.is_active = False
        user.save()
        from users.utils import create_and_save_token

        create_and_save_token(user)

        # Сохраняем текущее значение токена для использования в тесте
        token = user.activation_token

        # Активируем пользователя
        user.is_active = True
        user.activation_token = ""
        user.token_expires_at = None
        user.save()

        # Проверяем, что пользователь активирован
        updated_user = User.objects.get(email="testuser@example.com")
        self.assertTrue(updated_user.is_active)
        self.assertEqual(updated_user.activation_token, "")
        self.assertIsNone(updated_user.token_expires_at)
        self.assertIsNotNone(token)
        self.assertNotEqual(token, "")


class CustomLoginViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="testuser@example.com", password="testpass123", username="testuser")
        # По умолчанию пользователь активен для тестов входа
        self.user.is_active = True
        self.user.save()

    def test_login_success(self):
        response = self.client.login(email="testuser@example.com", password="testpass123")
        self.assertTrue(response)

    def test_login_failure(self):
        # Проверяем вход с неправильным паролем
        response = self.client.login(email="testuser@example.com", password="wrongpass")
        self.assertFalse(response)

        # Проверяем вход с неактивным пользователем
        self.user.is_active = False
        self.user.save()
        response = self.client.login(email="testuser@example.com", password="testpass123")
        self.assertFalse(response)


class RegisterViewTest(TestCase):
    @patch("users.views.send_confirmation_email")
    def test_register_success(self, mock_send_email):
        response = self.client.post(
            reverse("users:register"),
            {
                "email": "newuser@example.com",
                "username": "newuser",
                "password1": "testpass123",
                "password2": "testpass123",
            },
        )

        # Проверяем редирект на страницу логина
        self.assertRedirects(response, reverse("users:login"))

        # Проверяем, что пользователь создан и неактивен
        user = User.objects.get(email="newuser@example.com")
        self.assertFalse(user.is_active)

        # Активируем пользователя и создаем токен
        from users.utils import create_and_save_token

        create_and_save_token(user)

        self.assertIsNotNone(user.activation_token)
        self.assertIsNotNone(user.token_expires_at)

        # Проверяем, что отправлено письмо с подтверждением
        mock_send_email.assert_called_once()

    def test_register_password_mismatch(self):
        response = self.client.post(
            reverse("users:register"),
            {
                "email": "newuser@example.com",
                "username": "newuser",
                "password1": "testpass123",
                "password2": "differentpass",
            },
        )

        # Проверяем, что пользователь не создан
        self.assertEqual(response.status_code, 200)
        with self.assertRaises(User.DoesNotExist):
            User.objects.get(email="newuser@example.com")


class ActivateAccountViewTest(TestCase):
    @patch("users.views.messages")
    @patch("users.views.send_activation_email")
    def test_activate_account_success(self, mock_send_activation, mock_messages):
        user = User.objects.create_user(email="testuser@example.com", password="testpass123", username="testuser")
        user.is_active = False
        user.save()
        from users.utils import create_and_save_token

        token = create_and_save_token(user)

        response = self.client.get(reverse("users:activate", kwargs={"pk": user.pk, "token": token}))

        # Проверяем редирект на профиль
        self.assertEqual(response.status_code, 302)
        self.assertIn("/users/profile/", response.url)

        # Проверяем, что пользователь активирован
        updated_user = User.objects.get(email="testuser@example.com")
        self.assertTrue(updated_user.is_active)
        self.assertEqual(updated_user.activation_token, "")
        self.assertIsNone(updated_user.token_expires_at)

        # Проверяем, что отправлено приветственное письмо
        mock_send_activation.assert_called_once_with(updated_user)

    def test_activate_account_expired_token(self):
        user = User.objects.create_user(email="testuser@example.com", password="testpass123", username="testuser")
        user.is_active = False
        user.save()
        from users.utils import create_and_save_token

        create_and_save_token(user)
        # Устанавливаем срок действия токена в прошлое
        user.token_expires_at = timezone.now() - timezone.timedelta(hours=1)
        user.save()

        response = self.client.get(reverse("users:activate", kwargs={"pk": user.pk, "token": user.activation_token}))

        # Проверяем редирект на страницу входа
        self.assertEqual(response.status_code, 302)
        self.assertIn("/users/login/", response.url)

        # Проверяем, что пользователь не активирован
        updated_user = User.objects.get(email="testuser@example.com")
        self.assertFalse(updated_user.is_active)

    def test_activate_account_invalid_token(self):
        user = User.objects.create_user(email="testuser@example.com", password="testpass123", username="testuser")
        user.is_active = False
        user.save()
        from users.utils import create_and_save_token

        create_and_save_token(user)

        response = self.client.get(reverse("users:activate", kwargs={"pk": user.pk, "token": "invalid-token"}))

        # Проверяем редирект на страницу входа
        self.assertEqual(response.status_code, 302)
        self.assertIn("/users/login/", response.url)

        # Проверяем, что пользователь не активирован
        updated_user = User.objects.get(email="testuser@example.com")
        self.assertFalse(updated_user.is_active)


class ProfileViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="testuser@example.com", password="testpass123", username="testuser")
        self.user.is_active = True
        self.user.save()

        # Создаем группу Пользователь
        self.user_group, created = Group.objects.get_or_create(name="Пользователь")

    def test_profile_detail_view(self):
        # Назначаем пользователю необходимое разрешение
        from django.contrib.auth.models import Permission

        can_view_user_perm = Permission.objects.get(codename="can_view_user")
        self.user.user_permissions.add(can_view_user_perm)
        self.client.force_login(self.user)
        response = self.client.get(reverse("users:profile", kwargs={"pk": self.user.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "testuser@example.com")

    def test_profile_update_view(self):
        # Назначаем пользователю необходимые разрешения
        from django.contrib.auth.models import Permission

        can_change_user_perm = Permission.objects.get(codename="can_change_user")
        can_view_user_perm = Permission.objects.get(codename="can_view_user")
        self.user.user_permissions.add(can_change_user_perm)
        self.user.user_permissions.add(can_view_user_perm)
        self.client.force_login(self.user)

        # Отправляем POST-запрос с обновленными данными
        response = self.client.post(
            reverse("users:profile_update", kwargs={"pk": self.user.pk}),
            {
                "email": "updated@example.com",
                "username": "updateduser",
                "phone_number": "+79991234567",
                "country": "Russia",
            },
        )

        # Проверяем редирект
        self.assertRedirects(response, reverse("users:profile", kwargs={"pk": self.user.pk}))

        # Проверяем обновление данных
        updated_user = User.objects.get(email="updated@example.com")
        self.assertEqual(updated_user.username, "updateduser")
        self.assertEqual(updated_user.phone_number, "+79991234567")
        self.assertEqual(updated_user.country, "Russia")

    def test_profile_delete_view(self):
        # Назначаем пользователю необходимое разрешение
        from django.contrib.auth.models import Permission

        can_delete_user_perm = Permission.objects.get(codename="can_delete_user")
        self.user.user_permissions.add(can_delete_user_perm)
        self.client.force_login(self.user)
        response = self.client.post(reverse("users:profile_delete", kwargs={"pk": self.user.pk}))

        self.assertRedirects(response, reverse("users:login"))

        # Проверяем, что пользователь удален
        with self.assertRaises(User.DoesNotExist):
            User.objects.get(email="testuser@example.com")


class UsersListViewTest(TestCase):
    def setUp(self):
        # Создаем суперпользователя
        self.superuser = User.objects.create_superuser(
            email="admin@example.com", password="adminpass123", username="admin"
        )
        self.superuser.is_superuser = True
        self.superuser.is_active = True
        self.superuser.save()

        # Создаем обычного пользователя
        self.user = User.objects.create_user(email="testuser@example.com", password="testpass123", username="testuser")
        self.user.is_active = True
        self.user.save()

        # Создаем менеджера
        self.manager_group, created = Group.objects.get_or_create(name="Менеджер")
        self.manager = User.objects.create_user(
            email="manager@example.com", password="managerpass123", username="manager"
        )
        self.manager.is_active = True
        self.manager.save()
        self.manager.groups.add(self.manager_group)
        # Назначаем менеджеру необходимое разрешение
        can_view_user_perm = Permission.objects.get(codename="can_view_user")
        self.manager.user_permissions.add(can_view_user_perm)

    def test_users_list_view_for_superuser(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("users:users_list"))

        # Проверяем, что нет редиректа
        self.assertEqual(response.status_code, 200)

        # Проверяем содержимое ответа
        self.assertContains(response, "admin@example.com")
        self.assertContains(response, "testuser@example.com")
        self.assertContains(response, "manager@example.com")

    def test_users_list_view_for_manager(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("users:users_list"))

        # Проверяем, что нет редиректа
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "admin@example.com")
        self.assertContains(response, "testuser@example.com")
        self.assertContains(response, "manager@example.com")

    def test_users_list_view_for_regular_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("users:users_list"))

        self.assertEqual(response.status_code, 403)  # Доступ запрещен
