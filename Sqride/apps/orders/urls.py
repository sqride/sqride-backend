from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet, OrderItemViewSet

router = DefaultRouter()
router.register(r'', OrderViewSet, basename='order')
# router.register(r'order-items', OrderItemViewSet, basename='order-item')

urlpatterns = [
    path('', include(router.urls)),
]