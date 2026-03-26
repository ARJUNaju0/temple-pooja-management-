# D:\Django Internship\tprmsystem\main\urls.py 
from django.urls import path
from . import views

app_name = 'pooja'
urlpatterns = [
    path("poojas/", views.pooja_services, name="pooja_services"),
    path("calendar/", views.calendar_view, name="calendar"),
    path("api/calendar/<int:year>/<int:month>/", views.api_ml_calendar),


    # API (JWT PROTECTED)
    path("api/", views.api_pooja_list, name="api_pooja_list"),
    path("api/<int:pooja_id>/", views.api_pooja_detail, name="api_pooja_detail"),
    path("api/pooja-calendar-events/", views.api_pooja_calendar_events, name="api_pooja_calendar_events"),
    path("api/search-pooja/", views.search_pooja, name="search_pooja"),


     # ADMIN PAGES (HTML)
    path("manage/", views.admin_manage_poojas, name="admin_manage_poojas"),
    path("add/", views.admin_add_pooja, name="admin_add_pooja"),
    path("edit/<int:pooja_id>/", views.admin_edit_pooja, name="admin_edit_pooja"),
    path("delete/<int:pooja_id>/", views.admin_delete_pooja, name="admin_delete_pooja"),
    
   
    
    # MEMBER pooja service page (HTML)
    path("services/", views.member_pooja_services, name="services"),
    
   
]