################################################################################################
import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.messages.views import SuccessMessageMixin
from django.core.cache import cache
from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import cache_page
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView, FormView, TemplateView

from sending.forms import MailingForm, BlockMailingForm, MessageForm, BlockMessageForm, MessageRecipientForm, \
    BlockMessageRecipientForm, SendMailingForm
from sending.models import Mailing, MailingAttempt, Message, MessageRecipient
from sending.operator import perform_send

logger = logging.getLogger(__name__)


@method_decorator(cache_page(60 * 15), name='dispatch')
class HomeView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    paginate_by = 20
    template_name = 'sending/home.html'
    context_object_name = 'mailings'
    permission_required = 'sending.view_mailing'

    def get_context_data(self, **kwargs):
        """Добавляем дополнительные данные в контекст шаблона"""
        context = super().get_context_data(**kwargs)
        global mailings, unique_recipients_count, started_mailings
        is_manager = Group.objects.filter(name='Менеджер', user=self.request.user).exists()
        if self.request.user.is_superuser or is_manager:
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


@method_decorator(cache_page(60 * 15), name='dispatch')
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
class MessageListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Message
    paginate_by = 20
    template_name = 'sending/messages_list.html'
    context_object_name = 'messages'
    permission_required = 'sending.view_message'

    def get_queryset(self):
        key = f'message-list-{self.request.user.pk}'
        queryset = cache.get(key)
        if not queryset:
            is_manager = Group.objects.filter(name='Менеджер', user=self.request.user).exists()
            if self.request.user.is_superuser or is_manager:
                queryset = super().get_queryset()  # Показываем ВСЕ сообщения, если у пользователя есть соответствующее право
                sorted_queryset = queryset.order_by('owner')
                cache.set(key, sorted_queryset, timeout=60)
            else:
                queryset = super().get_queryset().filter(
                    owner=self.request.user)  # Иначе показываем только собственные сообщения
                cache.set(key, queryset, timeout=60)
        logger.info(f"{self.get_queryset.__qualname__}: Успешно")
        return queryset

    def get_context_data(self, **kwargs):
        """Добавляем дополнительные данные в контекст шаблона"""
        context = super().get_context_data(**kwargs)
        is_manager = Group.objects.filter(name='Менеджер', user=self.request.user).exists()

        if self.request.user.is_superuser or is_manager:
            messages = Message.objects.all()  # Все рассылки
        else:
            messages = Message.objects.filter(owner=self.request.user)  # Сообщения авторизованного пользователя
        # Передаем сообщения
        context["messages"] = messages
        # Передаем количество рассылок
        context["messages_count"] = len(messages)

        logger.info(f"{self.get_context_data.__qualname__}: Успешно")
        return context


class MessageCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = Message
    form_class = MessageForm
    template_name = 'sending/message_form.html'
    success_message = 'Вы успешно создали новое сообщение!'
    success_url = reverse_lazy('sending:messages_list')
    permission_required = 'sending.add_message'

    def form_valid(self, form):
        """
        Здесь мы добавляем текущего пользователя в качестве владельца сообщения.
        """
        obj = form.save(commit=False)  # Получаем объект сообщения из формы
        obj.owner = self.request.user  # Устанавливаем текущего пользователя в качестве владельца
        obj.save()  # Сохраняем объект сообщения в базе данных
        logger.info(f"{self.form_valid.__qualname__}: Успешно")
        return super().form_valid(form)  # Возвращаем стандартный ответ родительского класса


@method_decorator(cache_page(60), name='dispatch')
class MessageDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Message
    template_name = 'sending/message_detail.html'
    context_object_name = 'message'
    permission_required = 'sending.view_message'


class MessageUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Message
    form_class = MessageForm
    template_name = 'sending/message_form.html'
    success_url = reverse_lazy('sending:messages_list')
    permission_required = 'sending.change_message'


class MessageBlockingView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Message
    form_class = BlockMessageForm
    template_name = 'sending/block_message_form.html'
    success_url = reverse_lazy('sending:messages_list')
    permission_required = 'sending.can_block_message'

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


class MessageDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Message
    template_name = 'sending/message_confirm_delete.html'
    success_url = reverse_lazy('sending:messages_list')
    permission_required = 'sending.delete_message'

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
class MailingListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Mailing
    paginate_by = 20
    template_name = 'sending/mailing_list.html'
    context_object_name = 'mailings'
    permission_required = 'sending.view_mailing'

    def get_queryset(self):
        key = f'mailing-list-{self.request.user.id}'
        queryset = cache.get(key)
        if not queryset:
            is_manager = Group.objects.filter(name='Менеджер', user=self.request.user).exists()
            if self.request.user.is_superuser or is_manager:
                queryset = super().get_queryset()  # Показываем ВСЕ рассылки, если у пользователя есть соответствующее право
                sorted_queryset = queryset.order_by('owner')
                cache.set(key, sorted_queryset, timeout=60)
            else:
                queryset = super().get_queryset().filter(
                    owner=self.request.user)  # Иначе показываем только собственные рассылки
                cache.set(key, queryset, timeout=60)
        logger.info(f"{self.get_queryset.__qualname__}: Успешно")

        return queryset

    def get_context_data(self, **kwargs):
        """Добавляем дополнительные данные в контекст шаблона"""
        context = super().get_context_data(**kwargs)
        global mailings
        is_manager = Group.objects.filter(name='Менеджер', user=self.request.user).exists()
        if self.request.user.is_superuser or is_manager:
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
        context["mailings_count"] = len(mailings)  # Передаем количество рассылок
        logger.info(f"{self.get_context_data.__qualname__}: Успешно")

        return context


class MailingCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = Mailing
    form_class = MailingForm
    template_name = 'sending/mailing_form.html'
    success_message = 'Вы успешно создали новую рассылку!'
    success_url = reverse_lazy('sending:mailing_list')
    permission_required = 'sending.add_mailing'

    def form_valid(self, form):
        """
        Метод вызывается, когда форма прошла валидацию.
        Здесь мы добавляем текущего пользователя в качестве владельца рассылки.
        """
        obj = form.save(commit=False)  # Получаем объект рассылки из формы
        obj.owner = self.request.user  # Устанавливаем текущего пользователя в качестве владельца
        obj.save()  # Сохраняем объект рассылки в базе данных
        logger.info(f"{self.form_valid.__qualname__}: Успешно")
        return super().form_valid(form)  # Возвращаем стандартный ответ родительского класса

    def get_context_data(self, **kwargs):
        """Добавляем получателей в контекст шаблона"""
        context = super().get_context_data(**kwargs)
        context["recipients"] = MessageRecipient.objects.all()
        logger.info(f"{self.get_context_data.__qualname__}: Успешно")

        return context


@method_decorator(cache_page(60), name='dispatch')
class MailingDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Mailing
    template_name = 'sending/mailing_detail.html'
    context_object_name = 'mailing'
    permission_required = 'sending.view_mailing'

    def get_context_data(self, **kwargs):
        """Добавляем сообщения данной рассылки в контекст шаблона"""
        context = super().get_context_data(**kwargs)
        mailing_id = self.object.id  # Берём id текущей рассылки
        # Фильтруем получателей по текущей рассылки
        recipient_in_mailing = MessageRecipient.objects.filter(mailing=mailing_id)
        context['recipients'] = recipient_in_mailing  # Передаём получателей в контекст
        context['recipient_count'] = len(recipient_in_mailing)  # Передаем количество получателей в рассылки
        context['mailing_id'] = mailing_id
        logger.info(f"{self.get_context_data.__qualname__}: Успешно")

        return context


class MailingUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Mailing
    form_class = MailingForm
    template_name = 'sending/mailing_form.html'
    success_url = reverse_lazy('sending:mailing_list')
    permission_required = 'sending.change_mailing'


class MailingBlockingView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Mailing
    form_class = BlockMailingForm
    template_name = 'sending/block_mailing_form.html'
    success_url = reverse_lazy('sending:mailing_list')
    permission_required = 'sending.can_block_mailing'

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


class MailingDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Mailing
    template_name = 'sending/mailing_confirm_delete.html'
    success_url = reverse_lazy('sending:mailing_list')
    permission_required = 'sending.delete_mailing'

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()  # Получаем объект модели
        # Проверяем, принадлежит ли пользователь группе менеджеров
        is_manager = Group.objects.filter(name='Менеджер', user=self.request.user).exists()
        # Если пользователь не является ни владельцем, ни менеджером, запрещаем удаление
        if not (self.request.user.is_superuser or is_manager or obj.owner == self.request.user):
            return HttpResponseForbidden('Вы не имеете прав на удаление этой рассылки.')
        logger.info(f"{self.dispatch.__qualname__}: Успешно")
        # Если проверка прошла успешно, выполняем стандартное удаление
        return super().dispatch(request, *args, **kwargs)


# CRUD для Клиентов
class RecipientListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = MessageRecipient
    paginate_by = 20
    template_name = 'sending/recipients_list.html'
    context_object_name = 'recipients'
    permission_required = 'sending.can_view_recipient'

    def get_queryset(self):
        key = f'recipient-list-{self.request.user.id}'
        queryset = cache.get(key)
        if not queryset:
            is_manager = Group.objects.filter(name='Менеджер', user=self.request.user).exists()
            if self.request.user.is_superuser or is_manager:
                queryset = super().get_queryset()  # Показываем ВСЕХ получателей, если у пользователя есть соответствующее право
                sorted_queryset = queryset.order_by('owner')
                cache.set(key, sorted_queryset, timeout=60)
            else:
                queryset = super().get_queryset().filter(
                    owner=self.request.user)  # Иначе показываем только собственных получателей
                cache.set(key, queryset, timeout=60)
        logger.info(f"{self.get_queryset.__qualname__}: Успешно")

        return queryset

    def get_context_data(self, **kwargs):
        """Добавляем дополнительные данные в контекст шаблона"""
        context = super().get_context_data(**kwargs)
        is_manager = Group.objects.filter(name='Менеджер', user=self.request.user).exists()
        if self.request.user.is_superuser or is_manager:
            recipients = MessageRecipient.objects.all()
        else:
            recipients = MessageRecipient.objects.filter(owner=self.request.user)
        context['recipients'] = recipients
        context['recipients_count'] = len(recipients)  # Передаем количество сообщений
        logger.info(f"{self.get_context_data.__qualname__}: Успешно")
        return context


class RecipientCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = MessageRecipient
    form_class = MessageRecipientForm
    template_name = 'sending/recipient_form.html'
    success_message = 'Вы успешно создали нового получателя!'
    success_url = reverse_lazy('sending:recipients_list')
    permission_required = 'sending.can_add_recipient'

    def form_valid(self, form):
        """
        Здесь мы добавляем текущего пользователя в качестве владельца получателя.
        """
        obj = form.save(commit=False)  # Получаем объект получателя из формы
        obj.owner = self.request.user  # Устанавливаем текущего пользователя в качестве владельца
        try:
            obj.save()  # Сохраняем объект получателя в базе данных
        except Exception as e:
            messages.error(self.request, f"Произошла ошибка при создании получателя: {e}")
            logger.info(f"{self.form_valid.__qualname__}. Ошибка: {str(e)}")
            return redirect('sending:create_recipient')
        logger.info(f"{self.form_valid.__qualname__}: Успешно")
        return super().form_valid(form)  # Возвращаем стандартный ответ родительского класса


@method_decorator(cache_page(60), name='dispatch')
class RecipientDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = MessageRecipient
    template_name = 'sending/recipient_detail.html'
    context_object_name = 'recipient'
    permission_required = 'sending.can_view_recipient'

    def get_request(self):
        request = cache.get('cached_request')
        if not request:
            request = super().get_queryset()
            cache.set('cached_request', request, 60)
            logger.info(f"{self.get_request.__qualname__}: Успешно добавлено в кэш на 1мин.")
        logger.info(f"{self.get_request.__qualname__}: Успешно получено из кэша.")
        return request


class RecipientUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = MessageRecipient
    form_class = MessageRecipientForm
    template_name = 'sending/recipient_form.html'
    success_url = reverse_lazy('sending:recipients_list')
    permission_required = 'sending.can_change_recipient'

    def form_valid(self, form):
        """
        Здесь мы добавляем текущего пользователя в качестве владельца получателя.
        """
        obj = form.save(commit=False)  # Получаем объект получателя из формы
        if obj.owner is None:
            obj.owner = self.request.user  # Устанавливаем текущего пользователя в качестве владельца
        try:
            obj.save()  # Сохраняем объект получателя в базе данных
        except Exception as e:
            messages.error(self.request, f'Произошла ошибка при создании получателя: {e}')
            logger.info(f"{self.form_valid.__qualname__}. Ошибка: {str(e)}")
            return redirect('sending:create_recipient')
        logger.info(f"{self.form_valid.__qualname__}. Успешно")
        return super().form_valid(form)  # Возвращаем стандартный ответ родительского класса


class RecipientBlockingView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = MessageRecipient
    form_class = BlockMessageRecipientForm
    template_name = 'sending/block_recipient_form.html'
    success_url = reverse_lazy('sending:recipients_list')
    context_object_name = 'recipient'
    permission_required = 'sending.can_deactivate_recipient'

    def post(self, request, *args, **kwargs):
        recipient = get_object_or_404(MessageRecipient, pk=self.kwargs['pk'])
        user = self.request.user
        is_manager = Group.objects.filter(name='Менеджер', user=self.request.user).exists()
        if user == recipient.owner or is_manager:
            if recipient.is_active:
                recipient.is_active = False
            else:
                recipient.is_active = True
            recipient.save()
        logger.info(f"{self.post.__qualname__}. Успешно")

        return redirect('sending:recipients_list')


class RecipientDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = MessageRecipient
    template_name = 'sending/recipient_confirm_delete.html'
    success_url = reverse_lazy('sending:recipients_list')
    context_object_name = 'recipient'
    permission_required = 'sending.can_delete_recipient'

    def dispatch(self, request, *args, **kwargs):
        # Получаем объект модели
        obj = self.get_object()

        # Если пользователь не является ни владельцем, ни менеджером, запрещаем удаление
        if not (self.request.user.is_superuser or obj.owner == self.request.user):
            return HttpResponseForbidden('Вы не имеете прав на удаление этого получателя.')
        logger.info(f"{self.dispatch.__qualname__}. Успешно")

        # Если проверка прошла успешно, выполняем стандартное удаление
        return super().dispatch(request, *args, **kwargs)


# Создание и просмотр для попыток рассылок
@method_decorator(cache_page(60), name='dispatch')
class MailingAttemptsListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = MailingAttempt
    paginate_by = 20
    template_name = 'sending/mailing_attempts.html'
    context_object_name = 'mailing_attempts'
    permission_required = 'sending.can_view_mailing_attempt'

    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        mailing_id = self.kwargs.get('pk')
        mailing = Mailing.objects.get(pk=mailing_id)
        owner = mailing.owner

        # Проверяем разрешения пользователя
        is_manager = Group.objects.filter(name='Менеджер', user=self.request.user).exists()
        if not (user.is_superuser or is_manager or user == owner):
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


@method_decorator(cache_page(60), name='dispatch')
class MailingAttemptDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = MailingAttempt
    template_name = 'sending/attempt_detail.html'
    context_object_name = 'attempt'
    permission_required = 'sending.can_view_mailing_attempt'

    def get_queryset(self):
        global queryset
        user = self.request.user
        attempt_id = self.kwargs.get('pk', None)
        if attempt_id is not None:
            if user.is_superuser or user.has_perm('sending.can_view_mailing_attempt'):
                # Показываем ВСЕ попытки рассылок, если у пользователя есть соответствующее право
                queryset = super().get_queryset().filter(pk=attempt_id)
            else:
                # Иначе показываем только собственные попытки рассылок
                queryset = super().get_queryset().filter(owner=user, pk=attempt_id)
        logger.info(f"{self.get_queryset.__qualname__}. Успешно")

        return queryset


class SendMailingView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    form_class = SendMailingForm
    template_name = 'sending/send_mailing.html'
    permission_required = 'sending.change_mailing'

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


@method_decorator(cache_page(60), name='dispatch')
class StatisticsView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    paginate_by = 20
    template_name = 'sending/statistics.html'
    context_object_name = 'statistics'
    permission_required = 'sending.view_mailing'

    def get_context_data(self, **kwargs):
        """Добавляем дополнительные данные в контекст шаблона"""
        context = super().get_context_data(**kwargs)
        is_manager = Group.objects.filter(name='Менеджер', user=self.request.user).exists()
        if self.request.user.is_superuser or is_manager:
            mailings = Mailing.objects.all()  # Все рассылки
            attempts = MailingAttempt.objects.all()  # Все сообщения
        else:
            mailings = Mailing.objects.filter(owner=self.request.user)  # Рассылки авторизованного пользователя
            attempts = MailingAttempt.objects.filter(mailing__in=mailings)  # Сообщения авторизованного пользователя

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
