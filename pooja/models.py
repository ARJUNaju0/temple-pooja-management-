# D:\Django Internship\tprmsystem\pooja\models.py
from django.db import models
from django.conf import settings
from django.core.validators import MaxValueValidator
from decimal import Decimal



class Pooja(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    amount = models.DecimalField(
        max_digits=7, 
        decimal_places=2,
        validators=[MaxValueValidator(Decimal("10000000"))], 
        default=0
    )
    pooja_date = models.DateField(null=True, blank=True, help_text="Select the pooja Date")
    is_special_pooja = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    enable_slots = models.BooleanField(default=False, help_text='Enable/disable slot booking for this pooja')
    allow_multiple_bookings = models.BooleanField(default=False, help_text='Allow multiple bookings for this pooja by the same user')
    max_slots = models.PositiveIntegerField(default=1)
    available_slots = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='pooja_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='pooja_updated')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['pooja_date', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'pooja_date'],
                name='unique_pooja_name_date'
            )
        ]

    def __str__(self):
        return self.name

