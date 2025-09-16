from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View
from django.views.generic import ListView, CreateView

from sending.models import Mailing, MailingAttempt, Message, MessageRecipient


class ContactView(View):
    def get(self, request):
        return render(request, "base_templates/contact.html")

    def post(self, request):
        name = request.POST.get("name")
        phone = request.POST.get("phone")
        message = request.POST.get("message")
        print(f"You have new message from {name}({phone}): {message}")
        return render(request, "base_templates/contact.html")


class MailingListView(LoginRequiredMixin, ListView):
    model = Mailing
    paginate_by = 20
    template_name = 'sending/mailing_list.hyml'
    context_object_name = 'mailings'
    permission_required = 'sending.view_mailing'

    def get_queryset(self):
        if self.request.user.is_superuser or self.request.user.has_perm('sending.view_mailing'):
            queryset = super().get_queryset()  # Показываем ВСЕ рассылки, если у пользователя есть соответствующее право
        else:
            queryset = super().get_queryset().filter(
                owner=self.request.user)  # Иначе показываем только собственные рассылки
        return queryset.order_by("owner")

    def get_context_data(self, **kwargs):
        """Добавляем дополнительные данные в контекст шаблона"""
        context = super().get_context_data(**kwargs)
        mailings = Mailing.objects.all()
        context["mailings"] = mailings
        # Передаем количество товаров в категории
        context["mailings_count"] = len(mailings)
        return context


class MailingCreateView(LoginRequiredMixin, CreateView):
    ...
