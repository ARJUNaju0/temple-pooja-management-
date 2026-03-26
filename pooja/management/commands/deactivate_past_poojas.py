# C:\Users\USER\Desktop\temple-puja-management-testing\pooja\management\commands\deactivate_past_poojas.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from pooja.models import Pooja

class Command(BaseCommand):
    help = 'Deactivates poojas whose date has passed'

    def handle(self, *args, **options):
        today = timezone.now().date()
        # Only deactivate poojas that have a date and are still active
        count = Pooja.objects.filter(
            pooja_date__lt=today,
            is_active=True
        ).update(is_active=False)
        
        if count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully deactivated {count} past poojas')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('No poojas to deactivate')
            )
