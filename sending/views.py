################################################################################################
import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView, FormView, TemplateView

from sending.forms import MailingForm, BlockMailingForm, MessageForm, BlockMessageForm, MessageRecipientForm, \
    BlockMessageRecipientForm, SendMailingForm
from sending.models import Mailing, MailingAttempt, Message, MessageRecipient
from sending.operator import perform_send

logger = logging.getLogger(__name__)


class HomeView(LoginRequiredMixin, TemplateView):
    paginate_by = 20
    template_name = 'sending/home.html'
    context_object_name = 'mailings'

    def get_context_data(self, **kwargs):
        """Добавляем дополнительные данные в контекст шаблона"""
        context = super().get_context_data(**kwargs)
        global mailings, unique_recipients_count, started_mailings

        if self.request.user.is_superuser or self.request.user.has_perm('sending.view_mailing'):
            mailings = Mailing.objects.all()  # Все рассылки
        else:
            mailings = Mailing.objects.filter(owner=self.request.user)  # Рассылки авторизованного пользователя

        if mailings:
            for mailing in mailings:
                unique_recipients_count = mailing.attempt_set.values('recipient').distinct().count()
        else:
            unique_recipients_count = 0

        started_mailings = mailings.filter(status='STARTED').count()

        context['mailings'] = mailings
        context['unique_recipients_count'] = unique_recipients_count
        context['started_mailings'] = started_mailings
        context['mailings_count'] = len(mailings)
        logger.info(f"{self.get_context_data.__qualname__}: Успешно")
        return context


class ContactView(View):
    def get(self, request):
        logger.info(f"{self.get.__qualname__}: Успешно")

        return render(request, 'base_templates/contact.html')

    def post(self, request):
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        message = request.POST.get('message')
        logger.info(f'Получено сообщение от {name}({phone}): {message}')
        return render(request, 'base_templates/contact.html')


# CRUD для сообщений
class MessageListView(LoginRequiredMixin, ListView):
    model = Message
    paginate_by = 20
    template_name = 'sending/messages_list.html'
    context_object_name = 'messages'

    # permission_required = 'sending.view_message'

    def get_queryset(self):
        if self.request.user.is_superuser or self.request.user.has_perm('sending.view_message'):
            queryset = super().get_queryset()  # Показываем ВСЕ сообщения, если у пользователя есть соответствующее право
        else:
            queryset = super().get_queryset().filter(
                owner=self.request.user)  # Иначе показываем только собственные сообщения
        logger.info(f"{self.get_queryset.__qualname__}: Успешно")
        return queryset.order_by("owner")

    def get_context_data(self, **kwargs):
        """Добавляем дополнительные данные в контекст шаблона"""
        context = super().get_context_data(**kwargs)

        if self.request.user.is_superuser or self.request.user.has_perm('sending.view_message'):
            messages = Message.objects.all()  # Все рассылки
        else:
            messages = Message.objects.filter(owner=self.request.user)  # Сообщения авторизованного пользователя
        # Передаем сообщения
        context["messages"] = messages
        # Передаем количество рассылок
        context["messages_count"] = len(messages)

        logger.info(f"{self.get_context_data.__qualname__}: Успешно")
        return context


class MessageCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Message
    form_class = MessageForm
    template_name = 'sending/message_form.html'
    success_message = 'Вы успешно создали новое сообщение!'
    success_url = reverse_lazy('sending:messages_list')

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

        logger.info(f"{self.form_valid.__qualname__}: Успешно")

        # Возвращаем стандартный ответ родительского класса
        return super().form_valid(form)


class MessageDetailView(LoginRequiredMixin, DetailView):
    model = Message
    template_name = 'sending/message_detail.html'
    context_object_name = 'message'

    # def get_request(self):
    #     request = super().get_queryset()

    # request = cache.get('cached_request')
    # if not request:
    #     request = super().get_queryset()
    #     cache.set('cached_request', request, 60 * 15)
    #     logger.info(f"{self.get_request.__qualname__}: Успешно")
    # return request


class MessageUpdateView(LoginRequiredMixin, UpdateView):
    model = Message
    form_class = MessageForm
    template_name = 'sending/message_form.html'
    success_url = reverse_lazy('sending:messages_list')


class MessageBlockingView(LoginRequiredMixin, UpdateView):
    model = Message
    form_class = BlockMessageForm
    template_name = 'sending/block_message_form.html'
    success_url = reverse_lazy('sending:messages_list')

    def post(self, request, *args, **kwargs):
        message = get_object_or_404(Message, pk=self.kwargs['pk'])
        user = self.request.user
        if user == message.owner or request.user.has_perm('sending.can_block_message'):
            if message.is_active:
                message.is_active = False
            else:
                message.is_active = True
            message.save()
        logger.info(f"{self.post.__qualname__}: Успешно")
        return redirect('sending:messages_list')


class MessageDeleteView(LoginRequiredMixin, DeleteView):
    model = Message
    template_name = 'sending/message_confirm_delete.html'
    success_url = reverse_lazy('sending:messages_list')

    def dispatch(self, request, *args, **kwargs):
        # Получаем объект модели
        obj = self.get_object()

        # Проверяем, принадлежит ли пользователь группе менеджеров
        is_manager = Group.objects.filter(name='Менеджер', user=self.request.user).exists()

        # Если пользователь не является ни владельцем, ни менеджером, запрещаем удаление
        if not (self.request.user.is_superuser or is_manager or obj.owner == self.request.user):
            return HttpResponseForbidden('Вы не имеете прав на удаление этого сообщения.')
        logger.info(f"{self.dispatch.__qualname__}: Успешно")

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
        logger.info(f"{self.get_queryset.__qualname__}: Успешно")

        return queryset.order_by('owner')

    def get_context_data(self, **kwargs):
        """Добавляем дополнительные данные в контекст шаблона"""
        context = super().get_context_data(**kwargs)
        global mailings

        if self.request.user.is_superuser or self.request.user.has_perm('sending.view_mailing'):
            mailings = Mailing.objects.all()  # Все рассылки
        else:
            mailings = Mailing.objects.filter(owner=self.request.user)  # Рассылки авторизованного пользователя
        data = []
        for mailing in mailings:
            total_attempts_count = mailing.attempt_set.count()  # Подсчет общего числа попыток
            data.append({
                'mailing': mailing,
                'total_attempts_count': total_attempts_count
            })
        context['data'] = data
        context["mailings"] = mailings
        # Передаем количество рассылок
        context["mailings_count"] = len(mailings)
        logger.info(f"{self.get_context_data.__qualname__}: Успешно")

        return context


class MailingCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Mailing
    form_class = MailingForm
    template_name = 'sending/mailing_form.html'
    success_message = 'Вы успешно создали новую рассылку!'
    success_url = reverse_lazy('sending:mailing_list')

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
        logger.info(f"{self.form_valid.__qualname__}: Успешно")

        # Возвращаем стандартный ответ родительского класса
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Добавляем получателей в контекст шаблона"""
        context = super().get_context_data(**kwargs)
        context["recipients"] = MessageRecipient.objects.all()
        logger.info(f"{self.get_context_data.__qualname__}: Успешно")

        return context


class MailingDetailView(LoginRequiredMixin, DetailView):
    model = Mailing
    template_name = 'sending/mailing_detail.html'
    context_object_name = 'mailing'

    def get_context_data(self, **kwargs):
        """Добавляем сообщения данной рассылки в контекст шаблона"""
        context = super().get_context_data(**kwargs)
        # Берём id текущей рассылки
        mailing_id = self.object.id
        # Фильтруем получателей по текущей рассылки
        recipient_in_mailing = MessageRecipient.objects.filter(mailing=mailing_id)
        # Передаём получателей в контекст
        context['recipients'] = recipient_in_mailing
        # Передаем количество получателей в рассылки
        context['recipient_count'] = len(recipient_in_mailing)
        context['mailing_id'] = mailing_id
        logger.info(f"{self.get_context_data.__qualname__}: Успешно")

        return context


class MailingUpdateView(LoginRequiredMixin, UpdateView):
    model = Mailing
    form_class = MailingForm
    template_name = 'sending/mailing_form.html'
    success_url = reverse_lazy('sending:mailing_list')


class MailingBlockingView(LoginRequiredMixin, UpdateView):
    model = Mailing
    form_class = BlockMailingForm
    template_name = 'sending/block_mailing_form.html'
    success_url = reverse_lazy('sending:mailing_list')

    def post(self, request, *args, **kwargs):
        mailing = get_object_or_404(Mailing, pk=self.kwargs['pk'])
        user = self.request.user
        if user == mailing.owner or request.user.has_perm('sending.can_block_mailing'):
            if mailing.is_active:
                mailing.is_active = False
            else:
                mailing.is_active = True
            mailing.save()
        logger.info(f"{self.post.__qualname__}: Успешно")

        return redirect('sending:mailing_list')


class MailingDeleteView(LoginRequiredMixin, DeleteView):
    model = Mailing
    template_name = 'sending/mailing_confirm_delete.html'
    success_url = reverse_lazy('sending:mailing_list')

    def dispatch(self, request, *args, **kwargs):
        # Получаем объект модели
        obj = self.get_object()

        # Проверяем, принадлежит ли пользователь группе менеджеров
        is_manager = Group.objects.filter(name='Менеджер', user=self.request.user).exists()

        # Если пользователь не является ни владельцем, ни менеджером, запрещаем удаление
        if not (self.request.user.is_superuser or is_manager or obj.owner == self.request.user):
            return HttpResponseForbidden('Вы не имеете прав на удаление этой рассылки.')
        logger.info(f"{self.dispatch.__qualname__}: Успешно")

        # Если проверка прошла успешно, выполняем стандартное удаление
        return super().dispatch(request, *args, **kwargs)


# CRUD для Клиентов
class RecipientListView(LoginRequiredMixin, ListView):
    model = MessageRecipient
    paginate_by = 20
    template_name = 'sending/recipients_list.html'
    context_object_name = 'recipients'

    # permission_required = 'sending.view_recipient'

    def get_queryset(self):
        if self.request.user.is_superuser or self.request.user.has_perm('sending.view_recipients'):
            queryset = super().get_queryset()  # Показываем ВСЕХ получателей, если у пользователя есть соответствующее право
        else:
            queryset = super().get_queryset().filter(
                owner=self.request.user)  # Иначе показываем только собственных получателей
        logger.info(f"{self.get_queryset.__qualname__}: Успешно")

        return queryset.order_by('owner')

    def get_context_data(self, **kwargs):
        """Добавляем дополнительные данные в контекст шаблона"""
        context = super().get_context_data(**kwargs)
        if self.request.user.is_superuser or self.request.user.has_perm('sending.view_recipients'):
            recipients = MessageRecipient.objects.all()
        else:
            recipients = MessageRecipient.objects.filter(owner=self.request.user)
        context['recipients'] = recipients
        # Передаем количество сообщений
        context['recipients_count'] = len(recipients)
        logger.info(f"{self.get_context_data.__qualname__}: Успешно")

        return context


class RecipientCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = MessageRecipient
    form_class = MessageRecipientForm
    template_name = 'sending/recipient_form.html'
    success_message = 'Вы успешно создали нового получателя!'
    success_url = reverse_lazy('sending:recipients_list')

    # permission_required = 'catalog.add_recipient'

    def form_valid(self, form):
        """
        Метод вызывается, когда форма прошла валидацию.
        Здесь мы добавляем текущего пользователя в качестве владельца получателя.
        """
        # Получаем объект получателя из формы
        obj = form.save(commit=False)
        # Устанавливаем текущего пользователя в качестве владельца
        obj.owner = self.request.user
        # Сохраняем объект получателя в базе данных
        try:
            obj.save()
        except Exception as e:
            messages.error(self.request, f"Произошла ошибка при создании получателя: {e}")
            logger.info(f"{self.form_valid.__qualname__}. Ошибка: {str(e)}")

            return redirect('sending:create_recipient')
        logger.info(f"{self.form_valid.__qualname__}: Успешно")

        # Возвращаем стандартный ответ родительского класса
        return super().form_valid(form)


class RecipientDetailView(LoginRequiredMixin, DetailView):
    model = MessageRecipient
    template_name = 'sending/recipient_detail.html'
    context_object_name = 'recipient'


class RecipientUpdateView(LoginRequiredMixin, UpdateView):
    model = MessageRecipient
    form_class = MessageRecipientForm
    template_name = 'sending/recipient_form.html'
    success_url = reverse_lazy('sending:recipients_list')

    def form_valid(self, form):
        """
        Метод вызывается, когда форма прошла валидацию.
        Здесь мы добавляем текущего пользователя в качестве владельца получателя.
        """
        # Получаем объект получателя из формы
        obj = form.save(commit=False)
        if obj.owner is None:
            # Устанавливаем текущего пользователя в качестве владельца
            obj.owner = self.request.user
        # Сохраняем объект получателя в базе данных
        try:
            obj.save()
        except Exception as e:
            messages.error(self.request, f'Произошла ошибка при создании получателя: {e}')
            logger.info(f"{self.form_valid.__qualname__}. Ошибка: {str(e)}")

            return redirect('sending:create_recipient')
        logger.info(f"{self.form_valid.__qualname__}. Успешно")

        # Возвращаем стандартный ответ родительского класса
        return super().form_valid(form)


class RecipientBlockingView(LoginRequiredMixin, UpdateView):
    model = MessageRecipient
    form_class = BlockMessageRecipientForm
    template_name = 'sending/block_recipient_form.html'
    success_url = reverse_lazy('sending:recipients_list')
    context_object_name = 'recipient'

    def post(self, request, *args, **kwargs):
        recipient = get_object_or_404(MessageRecipient, pk=self.kwargs['pk'])
        user = self.request.user
        if user == recipient.owner or request.user.has_perm('sending.deactivate_recipient'):
            if recipient.is_active:
                recipient.is_active = False
            else:
                recipient.is_active = True
            recipient.save()
        logger.info(f"{self.post.__qualname__}. Успешно")

        return redirect('sending:recipients_list')


class RecipientDeleteView(LoginRequiredMixin, DeleteView):
    model = MessageRecipient
    template_name = 'sending/recipient_confirm_delete.html'
    success_url = reverse_lazy('sending:recipients_list')
    context_object_name = 'recipient'

    def dispatch(self, request, *args, **kwargs):
        # Получаем объект модели
        obj = self.get_object()

        # Проверяем, принадлежит ли пользователь группе менеджеров
        is_manager = Group.objects.filter(name='Менеджер', user=self.request.user).exists()

        # Если пользователь не является ни владельцем, ни менеджером, запрещаем удаление
        if not (self.request.user.is_superuser or is_manager or obj.owner == self.request.user):
            return HttpResponseForbidden('Вы не имеете прав на удаление этого получателя.')
        logger.info(f"{self.dispatch.__qualname__}. Успешно")

        # Если проверка прошла успешно, выполняем стандартное удаление
        return super().dispatch(request, *args, **kwargs)


# # CRUD для попыток рассылок
class MailingAttemptsView(LoginRequiredMixin, ListView):
    model = MailingAttempt
    paginate_by = 20
    template_name = 'sending/mailing_attempts.html'
    context_object_name = 'mailing_attempts'

    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        mailing_id = self.kwargs.get('pk')
        mailing = Mailing.objects.get(pk=mailing_id)
        owner = mailing.owner

        # Проверяем разрешения пользователя
        if not (user.is_superuser or user.has_perm('sending.view_mailing_attempt') or user == owner):
            return HttpResponseForbidden('Вы не имеете права просматривать данный контент')
        logger.info(f"{self.dispatch.__qualname__}. Успешно")

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        mailing_id = self.kwargs.get('pk', None)

        if mailing_id is not None:
            queryset = queryset.filter(mailing_id=mailing_id)
        logger.info(f"{self.get_queryset.__qualname__}. Успешно")

        return queryset.order_by('attempted_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mailing_attempts = context['mailing_attempts']
        mailing_id = self.kwargs.get('pk', None)
        attempts_count = MailingAttempt.objects.filter(mailing_id=mailing_id).count()
        context['attempts_count'] = attempts_count  # Добавляем количество попыток
        context['mailing_attempts'] = mailing_attempts
        logger.info(f"{self.get_context_data.__qualname__}. Успешно")

        return context


class MailingAttemptView(LoginRequiredMixin, DetailView):
    model = MailingAttempt
    template_name = 'sending/attempt_detail.html'
    context_object_name = 'attempt'

    def get_queryset(self):
        user = self.request.user
        attempt_id = self.kwargs.get('pk', None)
        if user.is_superuser or user.has_perm('sending.view_attempt'):
            queryset = super().get_queryset()
            # Показываем ВСЕ попытки рассылок, если у пользователя есть соответствующее право
            if attempt_id is not None:
                queryset = super().get_queryset().filter(pk=attempt_id)
        else:
            queryset = super().get_queryset().filter(owner=user)
            # Иначе показываем только собственные попытки рассылок
            if attempt_id is not None:
                queryset = super().get_queryset().filter(pk=attempt_id)
        logger.info(f"{self.get_queryset.__qualname__}. Успешно")

        return queryset


class SendMailingView(LoginRequiredMixin, FormView):
    form_class = SendMailingForm
    template_name = 'sending/send_mailing.html'

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            mailing_id = form.cleaned_data['mailing_id']
            perform_send(mailing_id)
            logger.info(f"{self.post.__qualname__}. Успешно")

            return redirect(reverse_lazy('sending:mailing_attempts', args=(mailing_id,)))
        else:
            logger.info(f"{self.post.__qualname__}. Не успешно")

            return self.form_invalid(form)


class StatisticsView(LoginRequiredMixin, TemplateView):
    paginate_by = 20
    template_name = 'sending/statistics.html'
    context_object_name = 'statistics'

    def get_context_data(self, **kwargs):
        """Добавляем дополнительные данные в контекст шаблона"""
        context = super().get_context_data(**kwargs)

        if self.request.user.is_superuser or (
                self.request.user.has_perm('sending.view_mailing') and
                self.request.user.has_perm('sending.view_mailing_attempts')
        ):
            mailings = Mailing.objects.all()  # Все рассылки
            attempts = MailingAttempt.objects.all()  # Все сообщения
        else:
            mailings = Mailing.objects.filter(owner=self.request.user)  # Рассылки авторизованного пользователя
            attempts = MailingAttempt.objects.filter(owner=self.request.user)  # Сообщения авторизованного пользователя

        # Количество всех уникальных успешных отправок
        if mailings.exists():
            total_unique_sent_messages = attempts.filter(status='SUCCESSFULLY').values('mailing_id').distinct().count()
        else:
            total_unique_sent_messages = 0

        if attempts.exists():
            good_attempts_count = attempts.filter(status='SUCCESSFULLY').count()
            bad_attempts_count = attempts.filter(status='UNSUCCESSFULLY').count()
        else:
            good_attempts_count = 0
            bad_attempts_count = 0

        context['good_attempts_count'] = good_attempts_count
        context['bad_attempts_count'] = bad_attempts_count
        context['total_unique_sent_messages'] = total_unique_sent_messages
        logger.info(f"{self.get_context_data.__qualname__}: Успешно")
        return context

################################################################################################
