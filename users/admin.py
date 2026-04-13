from django.contrib import admin

from users.models import CustomUser


# admin.site.register(CustomUser)
@admin.register(CustomUser)
class UserAdmin(admin.ModelAdmin):
    exclude = ("password",)
