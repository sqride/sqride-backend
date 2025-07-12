from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    KitchenStationViewSet,
    KitchenOrderViewSet,
    KitchenOrderItemViewSet,
    KitchenDisplayViewSet,
    KitchenSystemViewSet,
    KitchenStaffViewSet,
    KitchenAnalyticsViewSet,
    
)

router = DefaultRouter()

# Basic Kitchen System URLs
router.register('system', KitchenSystemViewSet, basename='kitchen-system')
router.register('stations', KitchenStationViewSet, basename='kitchen-station')
router.register('orders', KitchenOrderViewSet, basename='kitchen-order')
router.register('items', KitchenOrderItemViewSet, basename='kitchen-item')
router.register('displays', KitchenDisplayViewSet, basename='kitchen-display')

# Staff Management URLs
router.register('staff', KitchenStaffViewSet, basename='kitchen-staff')

# Analytics URLs
router.register('analytics', KitchenAnalyticsViewSet, basename='kitchen-analytics')


urlpatterns = [
    path('', include(router.urls)),
]
