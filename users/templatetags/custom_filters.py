#########################################################################
from django import template
from django.contrib.auth.models import Group

register = template.Library()


@register.filter(name="in_group")
def in_group(user, group_name):
    """
    Фильтр, проверяющий, принадлежит ли пользователь указанной группе.
    True, если пользователь в группе, иначе False
    """
    try:
        group = Group.objects.get(name=group_name)
        return group in user.groups.all()
    except Group.DoesNotExist:
        return False

#########################################################################
