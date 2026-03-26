from django.contrib import admin
from booking.models import PoojaBooking, EmailLog

@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'subject', 'status', 'created_at', 'sent_at', 'attempts')
    list_filter = ('status', 'created_at')
    search_fields = ('recipient', 'subject', 'error_message')
    readonly_fields = ('created_at', 'sent_at')
    date_hierarchy = 'created_at'
    list_per_page = 20
    
    fieldsets = (
        ('Email Details', {
            'fields': ('recipient', 'subject', 'status')
        }),
        ('Delivery Info', {
            'fields': ('attempts', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'sent_at'),
            'classes': ('collapse',)
        }),
        ('Related Booking', {
            'fields': ('booking',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        return False  # Prevent manual addition of logs

# Register other models if needed
admin.site.register(PoojaBooking)
