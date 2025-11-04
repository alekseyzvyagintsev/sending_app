#################################################################################################
import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.core.files.storage import FileSystemStorage
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import DetailView, UpdateView, DeleteView, ListView
from django.views.generic.edit import CreateView, FormMixin

from users.forms import CustomUserCreationForm, ProfileEditForm
from users.models import CustomUser
from users.utils import send_confirmation_email, send_activation_email

logger = logging.getLogger(__name__)


class AvatarHandlingMixin(FormMixin):
    def form_valid(self, form):
        """
        Общая логика обработки изображения и сохранение формы.
        """
        # проверяем, отмечено ли удаление изображения
        avatar_clear = self.request.POST.get("avatar-clear")
        # Получаем форму и добавляем обработку изображения
        uploaded_avatar = self.request.FILES.get("avatar")

        if uploaded_avatar:
            # Сохраняем изображение во временную директорию
            fs = FileSystemStorage(location="media/avatars")
            filename = fs.save(uploaded_avatar.name, uploaded_avatar)

            # Устанавливаем путь к изображению
            form.instance.avatar = f"avatars/{filename}"
        elif avatar_clear:
            # Если отметили удаление изображения, ставим None или пустую строку
            form.instance.avatar = ""
        else:
            # Если изображение не передано, устанавливаем базовую картинку
            form.instance.avatar = "avatars/base_avatar.jpeg"
        logger.info("Обработка изображения прошла успешно.")
        # Возвращаем стандартный процесс сохранения
        return super().form_valid(form)


class CustomLoginView(LoginView):
    model = CustomUser
    template_name = "users/login.html"

    def get_success_url(self):
        user_id = self.request.user.id  # Получаем id пользователя после успешной авторизации
        logger.info(f"{self.get_success_url.__qualname__}: Успешно")

        return reverse_lazy("users:profile", kwargs={"pk": user_id})  # Формируем URL с id пользователя


class RegisterView(CreateView, AvatarHandlingMixin):
    template_name = "users/register.html"
    form_class = CustomUserCreationForm
    success_url = reverse_lazy("users:login")

    def form_valid(self, form):
        user = form.save(commit=False)  # Создаем объект пользователя, но пока не сохраняем
        password = form.cleaned_data.get("password1")  # Берём введённый пароль
        user.set_password(password)  # Устанавливаем пароль с использованием set_password
        user.is_active = False  # Деактивируем пользователя до проверки почты
        user.save()  # Сохраняем пользователя
        send_confirmation_email(self, user)  # Отправляем пользователю инструкцию для активации профиля
        logger.info(f"{self.form_valid.__qualname__}: Успешно")
        return super().form_valid(form)


def activate_account(request, pk, token):
    user = get_object_or_404(CustomUser, pk=pk)

    try:
        user_group = Group.objects.get(name="Пользователь")
    except Group.DoesNotExist:
        user_group = Group.objects.create(name="Пользователь")
        logger.error("Группа 'Пользователь' не найдена. Создали группу для добавления в нее пользователя")
    # Проверяем токен и срок его действия
    if user.activation_token == token and user.token_expires_at > timezone.now():
        user.is_active = True
        user.activation_token = ""  # Очищаем токен после активации
        user.token_expires_at = None
        user.groups.add(user_group)  # Добавляем Пользователя в группу 'Пользователь'
        user.save()
        messages.success(request, "Аккаунт успешно активирован!")
        logger.info(user.email, "Аккаунт успешно активирован!")
        send_activation_email(user)  # Отправка приветственного письма
        return redirect("users:profile", pk=pk)
    else:
        logger.error(user.email, "Срок действия токена истек или неверный.")
        return redirect("users:activate")


class ProfileDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = CustomUser
    template_name = "users/profile.html"
    context_object_name = "user"
    permission_required = "users.can_view_user"

    def get_queryset(self):
        """
        Фильтруем объекты так, чтобы были видны только собственные записи.
        """
        if self.request.user.has_perm("users.can_view_user"):
            return CustomUser.objects.filter(pk=self.request.user.pk)
        else:
            raise PermissionDenied("Нет разрешения на просмотр профиля")


class ProfileDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = CustomUser
    template_name = "users/user_confirm_delete.html"
    context_object_name = "user"
    success_url = reverse_lazy("users:login")
    permission_required = "users.can_delete_user"

    def get_queryset(self):
        """
        Фильтруем объекты так, чтобы были видны только собственные записи.
        """
        return CustomUser.objects.filter(pk=self.request.user.pk)


class ProfileUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = CustomUser
    form_class = ProfileEditForm
    template_name = "users/register.html"
    permission_required = "users.can_change_user"

    def get_queryset(self):
        """
        Фильтруем объекты так, чтобы были видны только собственные записи.
        """
        return CustomUser.objects.filter(pk=self.request.user.pk)


class UsersListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = CustomUser
    template_name = "users/users.html"
    permission_required = "users.can_view_user"

    def get_context_data(self, **kwargs):
        """Добавляем дополнительные данные в контекст шаблона"""
        context = super().get_context_data(**kwargs)
        is_manager = Group.objects.filter(name="Менеджер", user=self.request.user).exists()

        if self.request.user.is_superuser or is_manager:
            users = CustomUser.objects.all()  # Все пользователи
        else:
            raise PermissionDenied("Нет разрешения на просмотр профиля")

        if users:
            all_users_count = len(users)
            active_users = users.filter(is_active=True)
            active_users_count = len(active_users)
            blocked_users = users.filter(is_active=False)
            blocked_users_count = len(blocked_users)
        else:
            all_users_count = 0
            active_users = 0
            active_users_count = 0
            blocked_users = 0
            blocked_users_count = 0

        context["all_users_count"] = all_users_count
        context["active_users"] = active_users
        context["active_users_count"] = active_users_count
        context["blocked_users"] = blocked_users
        context["blocked_users_count"] = blocked_users_count
        context["is_manager"] = is_manager
        logger.info(f"{self.get_context_data.__qualname__}: Успешно")
        return context


#################################################################################################
