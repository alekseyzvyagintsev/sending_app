######################################################################################
import os

from django.core.exceptions import ValidationError


def validate_forbidden_words(forbidden_words, value):
    """
    Валидатор для проверки наличия запрещенных слов в значении поля.
    """
    # Приводим значение к нижнему регистру для упрощенной проверки
    lower_value = value.lower()

    # Проверяем каждый элемент массива запрещенных слов
    for word in forbidden_words:
        if word in lower_value:
            raise ValidationError(f'Запрещено использование слова "{word}".')


def validate_max_size_mb(max_size_mb=5, value=None):
    """
    Валидатор для проверки, что загружаемый файл не превышает выбранный размер в мегабайтах.
    """
    if value:
        file_size = value.size / (1024 * 1024)  # Размер файла в МБ
        if file_size > max_size_mb:
            raise ValidationError("Размер файла превышает {} MB.".format(max_size_mb))


def validate_extensions(valid_extensions, value):
    """
    Валидатор для проверки, что загружаемый файл не превышает выбранный размер в мегабайтах.
    """
    if value:
        extension = os.path.splitext(value.name)[1].lstrip(".").lower()
        if extension not in valid_extensions:
            raise ValidationError(f"{extension}! Допускаются только файлы {valid_extensions}")


######################################################################################
