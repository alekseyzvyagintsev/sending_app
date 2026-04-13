######################################################################################
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView, PasswordChangeView
from django.urls import path, reverse_lazy

from users.apps import UsersConfig
from users.views import (
    CustomLoginView,
    ProfileDeleteView,
    ProfileDetailView,
    ProfileUpdateView,
    RegisterView,
    UsersListView,
    activate_account,
)

app_name = UsersConfig.name

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(next_page="users:login"), name="logout"),
    path("profile/<int:pk>/", ProfileDetailView.as_view(), name="profile"),
    path("profile/update/<int:pk>/", ProfileUpdateView.as_view(), name="profile_update"),
    path("profile/delete/<int:pk>/", ProfileDeleteView.as_view(), name="profile_delete"),
    path("pwd_chng/", PasswordChangeView.as_view(success_url=reverse_lazy("users:login")), name="password_change"),
    path("activate/<int:pk>/<str:token>/", activate_account, name="activate"),
    path(
        "pwd_reset/",
        auth_views.PasswordResetView.as_view(
            template_name="users/password_reset_form.html",
            email_template_name="users/password_reset_email.html",
            success_url=reverse_lazy("users:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "pwd_reset/done/",
        auth_views.PasswordResetDoneView.as_view(template_name="users/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="users/password_reset_confirm.html",
            success_url=reverse_lazy("users:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(template_name="users/password_reset_complete.html"),
        name="password_reset_complete",
    ),
    path("list/", UsersListView.as_view(), name="users_list"),
]

######################################################################################
