################################################################################################
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView

from sending.forms import MailingForm, BlockMailingForm, MessageForm, BlockMessageForm
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


# CRUD для сообщений
class MessageListView(LoginRequiredMixin, ListView):
    model = Message
    paginate_by = 20
    template_name = 'sending/messages_list.html'
    context_object_name = 'messages'
    # permission_required = 'sending.view_mailing'

    def get_queryset(self):
        if self.request.user.is_superuser or self.request.user.has_perm('sending.view_message'):
            queryset = super().get_queryset()  # Показываем ВСЕ сообщения, если у пользователя есть соответствующее право
        else:
            queryset = super().get_queryset().filter(
                owner=self.request.user)  # Иначе показываем только собственные сообщения
        return queryset.order_by("owner")

    def get_context_data(self, **kwargs):
        """Добавляем дополнительные данные в контекст шаблона"""
        context = super().get_context_data(**kwargs)
        messages = Message.objects.all()
        context["messages"] = messages
        # Передаем количество сообщений
        context["messages_count"] = len(messages)
        return context


class MessageCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Message
    form_class = MessageForm
    template_name = "sending/message_form.html"
    success_message = "Вы успешно создали новое сообщение!"
    success_url = reverse_lazy("sending:messages_list")
    # permission_required = 'catalog.add_mailing'

    def form_valid(self, form):
        """
        Метод вызывается, когда форма прошла валидацию.
        Здесь мы добавляем текущего пользователя в качестве владельца сообщения.
        """
        # Получаем объект сообщения из формы
        obj = form.save(commit=False)

        # Устанавливаем текущего пользователя в качестве владельца
        obj.owner = self.request.user

        # Сохраняем объект сообщения в базе данных
        obj.save()

        # Возвращаем стандартный ответ родительского класса
        return super().form_valid(form)



class MessageDetailView(LoginRequiredMixin, DetailView):
    model = Message
    template_name = "sending/message_detail.html"
    context_object_name = "message"

    # def get_request(self):
    #     request = super().get_queryset()

        # request = cache.get('cached_request')
        # if not request:
        #     request = super().get_queryset()
        #     cache.set('cached_request', request, 60 * 15)
        # return request


class MessageUpdateView(LoginRequiredMixin, UpdateView):
    model = Message
    form_class = MessageForm
    template_name = "sending/message_form.html"
    success_url = reverse_lazy("sending:messages_list")


class MessageBlockingView(LoginRequiredMixin, UpdateView):
    model = Message
    form_class = BlockMessageForm
    template_name = "sending/block_message_form.html"
    success_url = reverse_lazy("sending:messages_list")

    def post(self, request, *args, **kwargs):
        message = get_object_or_404(Message, pk=self.kwargs['pk'])
        user = self.request.user
        if user == message.owner or request.user.has_perm('sending.can_block_message'):
            if message.is_active:
                message.is_active = False
            else:
                message.is_active = True
            message.save()

        return redirect('sending:messages_list')


class MessageDeleteView(LoginRequiredMixin, DeleteView):
    model = Message
    template_name = "sending/message_confirm_delete.html"
    success_url = reverse_lazy("sending:messages_list")

    def dispatch(self, request, *args, **kwargs):
        # Получаем объект модели
        obj = self.get_object()

        # Проверяем, принадлежит ли пользователь группе менеджеров
        is_manager = Group.objects.filter(name='Менеджер', user=self.request.user).exists()

        # Если пользователь не является ни владельцем, ни менеджером, запрещаем удаление
        if not (self.request.user.is_superuser or is_manager or obj.owner == self.request.user):
            return HttpResponseForbidden("Вы не имеете прав на удаление этого сообщения.")

        # Если проверка прошла успешно, выполняем стандартное удаление
        return super().dispatch(request, *args, **kwargs)


# CRUD для рассылок
class MailingListView(LoginRequiredMixin, ListView):
    model = Mailing
    paginate_by = 20
    template_name = 'sending/mailing_list.html'
    context_object_name = 'mailings'
    # permission_required = 'sending.view_mailing'

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
        # Передаем количество рассылок
        context["mailings_count"] = len(mailings)
        return context


class MailingCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Mailing
    form_class = MailingForm
    template_name = "sending/mailing_form.html"
    success_message = "Вы успешно создали новую рассылку!"
    success_url = reverse_lazy("sending:mailing_list")
    # permission_required = 'catalog.add_mailing'

    def form_valid(self, form):
        """
        Метод вызывается, когда форма прошла валидацию.
        Здесь мы добавляем текущего пользователя в качестве владельца рассылки.
        """
        # Получаем объект рассылки из формы
        obj = form.save(commit=False)

        # Устанавливаем текущего пользователя в качестве владельца
        obj.owner = self.request.user

        # Сохраняем объект рассылки в базе данных
        obj.save()

        # Возвращаем стандартный ответ родительского класса
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Добавляем получателей в контекст шаблона"""
        context = super().get_context_data(**kwargs)
        context["recipients"] = MessageRecipient.objects.all()
        return context


class MailingDetailView(LoginRequiredMixin, DetailView):
    model = Mailing
    template_name = "sending/mailing_detail.html"
    context_object_name = "mailing"

    def get_context_data(self, **kwargs):
        """Добавляем сообщения данной рассылки в контекст шаблона"""
        context = super().get_context_data(**kwargs)
        # Берём id текущей рассылки
        mailing_id = self.object.id
        # Фильтруем получателей по текущей рассылки
        recipient_in_mailing = MessageRecipient.objects.filter(mailing=mailing_id)
        # Передаём получателей в контекст
        context["recipients"] = recipient_in_mailing
        # Передаем количество получателей в рассылки
        context["recipient_count"] = len(recipient_in_mailing)
        return context

    # def get_request(self):
    #     request = super().get_queryset()

        # request = cache.get('cached_request')
        # if not request:
        #     request = super().get_queryset()
        #     cache.set('cached_request', request, 60 * 15)
        # return request


class MailingUpdateView(LoginRequiredMixin, UpdateView):
    model = Mailing
    form_class = MailingForm
    template_name = "sending/mailing_form.html"
    success_url = reverse_lazy("sending:mailing_list")

class MailingBlockingView(LoginRequiredMixin, UpdateView):
    model = Mailing
    form_class = BlockMailingForm
    template_name = "sending/block_mailing_form.html"
    success_url = reverse_lazy("sending:mailing_list")

    def post(self, request, *args, **kwargs):
        mailing = get_object_or_404(Mailing, pk=self.kwargs['pk'])
        user = self.request.user
        if user == mailing.owner or request.user.has_perm('sending.can_block_mailing'):
            if mailing.is_active:
                mailing.is_active = False
            else:
                mailing.is_active = True
            mailing.save()

        return redirect('sending:mailing_list')


class MailingDeleteView(LoginRequiredMixin, DeleteView):
    model = Mailing
    template_name = "sending/mailing_confirm_delete.html"
    success_url = reverse_lazy("sending:mailing_list")

    def dispatch(self, request, *args, **kwargs):
        # Получаем объект модели
        obj = self.get_object()

        # Проверяем, принадлежит ли пользователь группе менеджеров
        is_manager = Group.objects.filter(name='Менеджер', user=self.request.user).exists()

        # Если пользователь не является ни владельцем, ни менеджером, запрещаем удаление
        if not (self.request.user.is_superuser or is_manager or obj.owner == self.request.user):
            return HttpResponseForbidden("Вы не имеете прав на удаление этой рассылки.")

        # Если проверка прошла успешно, выполняем стандартное удаление
        return super().dispatch(request, *args, **kwargs)


################################################################################################
