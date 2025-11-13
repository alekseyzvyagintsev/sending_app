####################################################################################################
from django import forms

from sending.models import Mailing, Message, MessageRecipient


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['subject', 'body_text', 'is_active']
        widgets = {'is_active': forms.CheckboxInput(), }


class BlockMessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['is_active', ]
        widgets = {'is_active': forms.CheckboxInput(), }


class MailingForm(forms.ModelForm):
    class Meta:
        model = Mailing
        fields = ['start_sending', 'stop_sending', 'message', 'recipients', 'is_active', ]
        widgets = {
            'is_active': forms.CheckboxInput(),
            'start_sending': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'stop_sending': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


class BlockMailingForm(forms.ModelForm):
    class Meta:
        model = Mailing
        fields = ['is_active', ]
        widgets = {'is_active': forms.CheckboxInput(), }


class MessageRecipientForm(forms.ModelForm):
    class Meta:
        model = MessageRecipient
        fields = ['email', 'fullname', 'comment', 'is_active', 'owner']
        widgets = {'is_active': forms.CheckboxInput(), }


class BlockMessageRecipientForm(forms.ModelForm):
    class Meta:
        model = MessageRecipient
        fields = ['is_active', ]
        widgets = {'is_active': forms.CheckboxInput(), }


class SendMailingForm(forms.Form):
    mailing_id = forms.IntegerField(widget=forms.HiddenInput())

####################################################################################################
