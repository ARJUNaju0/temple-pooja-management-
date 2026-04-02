# D:\Django Internship\tprmsystem\tprmsystem\urls.py 
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', include('main.urls')),  
    path('', include('pooja.urls')),  
    path('temple_admin/', include('temple_admin.urls')),
    path('', include('booking.urls')),
    path('admin/', admin.site.urls),
    path('', include(('family_tree.urls', 'family_tree'), namespace='family_tree'))    
]


# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)