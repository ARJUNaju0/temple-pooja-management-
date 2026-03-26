# D:\Django Internship\tprmsystem\temple_admin\admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import TempleAdmin, AdminActivityLog

@admin.register(TempleAdmin)
class TempleAdminAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_staff', 'is_superuser', 'phone_number')
    list_filter = ('role', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'phone_number')
    ordering = ('username',)

@admin.register(AdminActivityLog)
class AdminActivityLogAdmin(admin.ModelAdmin):
    list_display = ('admin', 'action', 'timestamp', 'ip_address')
    readonly_fields = ('admin', 'action', 'timestamp', 'ip_address', 'user_agent')
    ordering = ('-timestamp',)
