from celery import shared_task
from django.utils import timezone
from pooja.models import Pooja

@shared_task
def deactivate_past_poojas_task():
    today = timezone.now().date()
    count = Pooja.objects.filter(
        pooja_date__lt=today,
        is_active=True
    ).update(is_active=False)

    return f"Deactivated {count} poojas"
