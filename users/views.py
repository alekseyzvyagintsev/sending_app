#################################################################################################
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponseForbidden, Http404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import DetailView, UpdateView, DeleteView
from django.views.generic.edit import CreateView, FormMixin

from users.forms import CustomUserCreationForm, ProfileEditForm
from users.models import CustomUser
from users.utils import send_confirmation_email, send_activation_email


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

        # Возвращаем стандартный процесс сохранения
        return super().form_valid(form)


class CustomLoginView(LoginView):
    model = CustomUser
    template_name = 'users/login.html'  # Укажите ваш шаблон

    def get_success_url(self):
        # Получаем id пользователя после успешной авторизации
        user_id = self.request.user.id
        # Формируем URL с id пользователя
        return reverse_lazy('users:profile', kwargs={'pk': user_id})


class RegisterView(CreateView):
    template_name = 'users/register.html'
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('users:login')

    def form_valid(self, form):
        user = form.save(commit=False)  # Создаем объект пользователя, но пока не сохраняем
        password = form.cleaned_data.get("password1")  # Берём введённый пароль
        user.set_password(password)  # Устанавливаем пароль с использованием set_password
        user.is_active = False  # Деактивируем пользователя до проверки почты
        user.save()  # Сохраняем пользователя
        send_confirmation_email(self, user) # Отправляем пользователю инструкцию для активации профиля
        return super().form_valid(form)


def activate_account(request, pk, token):
    try:
        user = CustomUser.objects.get(pk=pk)

        # Проверяем токен и срок его действия
        if user.activation_token == token and user.token_expires_at > timezone.now():
            user.is_active = True
            user.activation_token = ''  # Очищаем токен после активации
            user.token_expires_at = None
            user.save()
            messages.success(request, 'Аккаунт успешно активирован!')
            # Отправка приветственного письма
            send_activation_email(user)
            return redirect('users:profile', pk=pk)
        else:
            messages.error(request, 'Срок действия токена истек или неверный.')
            return redirect('users:activate')
    except CustomUser.DoesNotExist:
        raise Http404("Пользователь не найден.")


class ProfileDetailView(LoginRequiredMixin, DetailView):
    model = CustomUser
    template_name = 'users/profile.html'
    context_object_name = "user"


class ProfileDeleteView(LoginRequiredMixin, DeleteView):
    model = CustomUser
    template_name = 'users/user_confirm_delete.html'
    context_object_name = "user"
    success_url = reverse_lazy('users:login')


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    form_class = ProfileEditForm
    template_name = "users/register.html"

    def dispatch(self, request, *args, **kwargs):
        # Получаем объект модели
        obj = self.get_object()

        # Если пользователь не является владельцем, запрещаем смену пароля
        if not obj.owner == self.request.user:
            return HttpResponseForbidden("Вы не имеете прав на смену пароля этого пользователя.")

        # Если проверка прошла успешно, выполняем стандартную смену пароля
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        # Определение URL после успешной операции
        return reverse_lazy("users:profile", kwargs={"pk": self.object.pk})

#################################################################################################
