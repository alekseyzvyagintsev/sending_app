from django.contrib import admin

from sending.models import MessageRecipient, Message, Mailing, MailingAttempt


admin.site.register(MessageRecipient)
admin.site.register(Message)
admin.site.register(Mailing)
admin.site.register(MailingAttempt)