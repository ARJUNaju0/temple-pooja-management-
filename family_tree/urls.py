from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FamilyMemberViewSet, family_tree_view

router = DefaultRouter()
router.register(r'members', FamilyMemberViewSet)

urlpatterns = [
    path('family/', family_tree_view, name='family_tree'),
    path('api/', include(router.urls)),
]