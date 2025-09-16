######################################################################################
from django.urls import path
from django.contrib.auth.views import LogoutView
from users.apps import UsersConfig

from users.views import (RegisterView, ProfileDetailView, ProfileUpdateView, ProfileDeleteView, CustomLoginView,)

app_name = UsersConfig.name

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='users:login'), name='logout'),
    path('accounts/profile/<int:pk>/', ProfileDetailView.as_view(), name='profile'),
    path("accounts/profile/update/<int:pk>/", ProfileUpdateView.as_view(), name="profile_update"),
    path("accounts/profile/delete/<int:pk>/", ProfileDeleteView.as_view(), name="profile_delete"),
]

######################################################################################
