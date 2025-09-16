from django import forms

from sending.models import Mailing


class MailingForm(forms.ModelForm):
    class Meta:
        model = Mailing
        fields = ['message', 'recipients',]


class BlockMailingForm(forms.ModelForm):
    class Meta:
        model = Mailing
        fields = ['is_active',]