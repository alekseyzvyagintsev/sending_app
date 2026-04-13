from django.contrib import admin

from sending.models import Mailing, MailingAttempt, Message, MessageRecipient

admin.site.register(MessageRecipient)
admin.site.register(Message)
admin.site.register(Mailing)
admin.site.register(MailingAttempt)
