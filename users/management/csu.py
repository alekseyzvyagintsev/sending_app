from django.core.management import BaseCommand

from users.models import CustomUser


class Command(BaseCommand):
    def handle(self, *args, **options):
        user = CustomUser.objects.create(email='admin@example.com')
        user.set_password('qwer1234')
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.save()