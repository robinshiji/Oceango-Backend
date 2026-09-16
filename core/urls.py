from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, HubViewSet, CustomerViewSet, 
    ParcelViewSet, ParcelTrackingLogViewSet, 
    WhatsAppLogViewSet, SettingViewSet, DashboardStatsView
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'hubs', HubViewSet)
router.register(r'customers', CustomerViewSet)
router.register(r'parcels', ParcelViewSet)
router.register(r'tracking-logs', ParcelTrackingLogViewSet)
router.register(r'whatsapp-logs', WhatsAppLogViewSet)
router.register(r'settings', SettingViewSet)

urlpatterns = [
    path('dashboard-stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('', include(router.urls)),
]
