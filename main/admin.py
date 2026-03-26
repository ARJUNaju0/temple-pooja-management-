# D:\Django Internship\tprmsystem\main\admin.py
from django.contrib import admin
from .models import ActivityLog, Gallery

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'timestamp', 'ip_address', 'is_admin']
    list_filter = ['action', 'is_admin', 'timestamp']
    search_fields = ['user__username', 'ip_address', 'action']
    readonly_fields = ['user', 'action', 'timestamp', 'ip_address', 'user_agent', 'is_admin', 'details']
    ordering = ['-timestamp']
    
    def has_add_permission(self, request):
        # Prevent adding logs manually
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Allow admins to delete logs
        return request.user.is_superuser
        
admin.site.register(Gallery)
