######################################################################################
from django.urls import path

from sending.apps import SendingConfig
from sending.views import (HomeView, ContactView, MailingListView, MailingCreateView, MailingDetailView,
                           MailingUpdateView, MailingBlockingView, MailingDeleteView, MessageListView,
                           MessageCreateView, MessageDetailView, MessageUpdateView, MessageDeleteView,
                           MessageBlockingView, RecipientListView, RecipientCreateView, RecipientDetailView,
                           RecipientUpdateView, RecipientDeleteView, RecipientBlockingView, MailingAttemptsView,
                           MailingAttemptView, SendMailingView, StatisticsView)

app_name = SendingConfig.name


urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path("contact/", ContactView.as_view(), name="contact"),
    path('messages/', MessageListView.as_view(), name='messages_list'),
    path('message/create/', MessageCreateView.as_view(), name='message_create'),
    path('message/detail/<int:pk>/', MessageDetailView.as_view(), name='message_detail'),
    path("message/update/<int:pk>/", MessageUpdateView.as_view(), name="message_update"),
    path("message/delete/<int:pk>/", MessageDeleteView.as_view(), name="message_delete"),
    path("message/blocking/<int:pk>/", MessageBlockingView.as_view(), name="message_blocking"),
    path('mailing/list/', MailingListView.as_view(), name='mailing_list'),
    path('mailing/create/', MailingCreateView.as_view(), name='mailing_create'),
    path('mailing/detail/<int:pk>/', MailingDetailView.as_view(), name='mailing_detail'),
    path("mailing/update/<int:pk>/", MailingUpdateView.as_view(), name="mailing_update"),
    path("mailing/delete/<int:pk>/", MailingDeleteView.as_view(), name="mailing_delete"),
    path("mailing/blocking/<int:pk>/", MailingBlockingView.as_view(), name="mailing_blocking"),
    path('recipients/', RecipientListView.as_view(), name='recipients_list'),
    path('recipient/create/', RecipientCreateView.as_view(), name='recipient_create'),
    path('recipient/detail/<int:pk>/', RecipientDetailView.as_view(), name='recipient_detail'),
    path("recipient/update/<int:pk>/", RecipientUpdateView.as_view(), name="recipient_update"),
    path("recipient/delete/<int:pk>/", RecipientDeleteView.as_view(), name="recipient_delete"),
    path("recipient/blocking/<int:pk>/", RecipientBlockingView.as_view(), name="recipient_blocking"),
    path("attempts/<int:pk>/", MailingAttemptsView.as_view(), name="mailing_attempts"),
    path("attempt/<int:pk>/", MailingAttemptView.as_view(), name="attempt_detail"),
    path("send_mailing/<int:pk>/", SendMailingView.as_view(), name="send_mailing"),
    path("statistics/", StatisticsView.as_view(), name="statistics"),
]

######################################################################################
