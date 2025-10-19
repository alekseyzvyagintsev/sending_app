#########################################################################################################
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, UserChangeForm
from django.db.models import BooleanField

from sending.validators import validate_extensions, validate_max_size_mb
from users.models import CustomUser


class StileFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field, BooleanField):
                field.widget.attrs["class"] = "form-check-input"
            else:
                field.widget.attrs["class"] = "form-control"


class CustomUserCreationForm(StileFormMixin, UserCreationForm):
    phone_number = forms.CharField(max_length=15, required=False,
                                   help_text='Необязательное поле. Введите ваш номер телефона.')
    username = forms.CharField(max_length=50, required=True)
    usable_password = None

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('email', 'username', 'first_name', 'last_name', 'phone_number', 'avatar', 'password1', 'password2',)

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number and not phone_number.isdigit():
            raise forms.ValidationError('Номер телефона должен содержать только цифры.')
        return phone_number

    def clean_avatar(self):
        """Метод очистки и проверки поля 'avatar'"""
        avatar_field = self.cleaned_data["avatar"]
        # пропускаем пустое поле
        if not avatar_field:
            return None
        # Проверяем файлы на соответствие допустимым расширениям
        valid_extensions = ["jpg", "jpeg", "png"]
        validate_extensions(valid_extensions, avatar_field)
        # Проверяем, что размер файла не превышает допустимый размер
        max_size_mb = 5 * 1024 * 1024
        validate_max_size_mb(max_size_mb, avatar_field)

        return avatar_field


class ProfileEditForm(StileFormMixin, UserChangeForm):
    password = None  # Чтобы убрать пароль из формы редактирования

    class Meta(UserChangeForm.Meta):
        model = CustomUser
        fields = ('email', 'username', 'first_name', 'last_name', 'phone_number', 'avatar',)

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number and not phone_number.isdigit():
            raise forms.ValidationError('Номер телефона должен содержать только цифры.')
        return phone_number

    def clean_avatar(self):
        """Метод очистки и проверки поля 'avatar'"""
        avatar_field = self.cleaned_data["avatar"]
        # пропускаем пустое поле
        if not avatar_field:
            return None
        # Проверяем файлы на соответствие допустимым расширениям
        valid_extensions = ["jpeg", "png"]
        validate_extensions(valid_extensions, avatar_field)
        # Проверяем, что размер файла не превышает допустимый размер
        max_size_mb = 5
        validate_max_size_mb(max_size_mb, avatar_field)

        return avatar_field


class CustomAuthenticationForm(StileFormMixin, AuthenticationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('email', 'password1', 'password2',)

#########################################################################################################
