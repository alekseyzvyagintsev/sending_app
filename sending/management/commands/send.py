#####################################################################################################
import logging

from django.core.management import BaseCommand
from django.utils import timezone

from sending.models import Mailing
from sending.operator import perform_send

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Совершает рассылку если она активна,
    не установлены параметры старт и стоп
    и если установлен только один параметр, а второй входит в рамки установленных временных ограничений,
    а так же если оба параметра есть и входят в рамки установленных временных ограничений
    """

    def handle(self, *args, **options):
        now = timezone.localtime(timezone.now())
        matches = 0
        not_matches = 0
        mailings = Mailing.objects.filter(is_active=True)
        if len(mailings) > 0:
            for mailing in mailings:
                if (
                        (mailing.start_sending is None and mailing.stop_sending is None)
                        or (
                        mailing.start_sending is not None
                        and mailing.start_sending <= now
                        and mailing.stop_sending is None
                )
                        or (
                        mailing.stop_sending is not None
                        and mailing.stop_sending >= now
                        and mailing.start_sending is None
                )
                        or (mailing.start_sending <= now and mailing.stop_sending >= now)
                ):

                    perform_send(mailing.id)
                    matches += 1
                else:
                    not_matches += 1
        else:
            logger.info("Нет рассылок")
        logger.info(
            f"Всего рассылок {len(mailings)}шт. "
            f"Успешно отправлено {matches}шт. "
            f"Не подходят для отправки {not_matches}шт."
        )

#####################################################################################################
