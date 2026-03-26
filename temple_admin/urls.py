# temple_admin/urls.py
from django.urls import path
from .views import login_page, dashboard_view , add_member_view, update_settings
app_name = 'temple_admin'
urlpatterns = [
    # HTML Pages
    path('login/', login_page, name='temple_admin_login'),  
    path('dashboard/', dashboard_view, name='dashboard'),
    path('add_member/', add_member_view, name='add_member'),
    path('settings/update/', update_settings, name='update_settings'),
]