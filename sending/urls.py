######################################################################################
from django.urls import path

from sending.apps import SendingConfig
from sending.views import ContactView, MailingListView, MailingCreateView

app_name = SendingConfig.name

urlpatterns = [
    path("contact/", ContactView.as_view(), name="contact"),
    path('', MailingListView.as_view(), name='mailing_list'),
    path('create/', MailingCreateView.as_view(), name='mailing_create'),
#     path('detail/<int:pk>/', MailingDetailView.as_view(), name='mailing_detail'),
#     path("update/<int:pk>/", MailingUpdateView.as_view(), name="mailing_update"),
#     path("delete/<int:pk>/", MailingDeleteView.as_view(), name="mailing_delete"),
#     path("blocking/<int:pk>/", MailingBlockingView.as_view(), name="mailing_blocking"),
#     path("attempts/<int:pk>/", MailingAttemptsView.as_view(), name="attempts_list"),
#     path("attempt/<int:pk>/", MailingAttemptView.as_view(), name="attempt_detail"),
#     path("statistics/", StatisticsView.as_view(), name="statistics"),
]

######################################################################################
