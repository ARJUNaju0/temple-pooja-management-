# D:\Django Internship\tprmsystem\main\urls.py 
from django.urls import path
from . import views


urlpatterns = [
    # Traditional views (renders HTML pages)
    path('', views.home, name='home'),
    path('login/', views.login_page, name='login'),
    
    # JWT API endpoints with correct URL names
    path('api/login/', views.jwt_login, name='jwt_login'),
    path('api/refresh/', views.jwt_refresh, name='jwt_refresh'),
    path('api/logout/', views.jwt_logout, name='jwt_logout'),  
    
    # User info API
    path('api/user/', views.get_current_user, name='current_user'),
    path('api/protected/', views.protected_view, name='protected'),
    
    # Admin endpoints
    path('api/members/create/', views.create_member, name='create_member'),
    
    # Member-Protected APIs
    path('api/member/profile/', views.member_profile, name='member_profile_api'),
    path('api/member/change-password/', views.change_password, name='change_password'),
    path('api/member/activities/', views.member_activity_logs, name='member_activities'),
    
    # Member-Protected Pages (HTML views)
    path('member/profile/', views.member_profile_view, name='member_profile'),
    path('unauthorized/', views.unauthorized_view, name='unauthorized'),
    
    # DevTools config
    path('.well-known/appspecific/com.chrome.devtools.json', views.devtools_config, name='devtools_config'),

     path('api/gallery/upload/', views.upload_gallery_image, name='upload_gallery_image'),
    path('api/gallery/delete/<int:image_id>/', views.delete_gallery_image, name='delete_gallery_image'),
    path('gallery/', views.gallery_view, name='gallery'),
    path('upload/', views.upload_page, name='upload_page'),
    path('api/gallery/approve/<int:image_id>/', views.approve_gallery_image, name='approve_gallery_image'),
    path('api/gallery/reject/<int:image_id>/', views.reject_gallery_image, name='reject_gallery_image'),
    path('admin/gallery/pending/', views.admin_pending_gallery_view, name='admin_pending_gallery'),
    path('forgot-password/', views.forgot_password_page, name='forgot_password_page'),
    path("api/password/forgot/", views.forgot_password, name="forgot_password"),
    path("api/password/reset/", views.reset_password, name="reset_password"),
    path('reset-password/<uuid:token>/',views.reset_password_page,name='reset_password_page'),


]
