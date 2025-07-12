from django.urls import path, include
from rest_framework.routers import DefaultRouter
from pos.views.pos_session import POSSessionViewSet
from pos.views.pos_order import POSOrderViewSet

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'sessions', POSSessionViewSet, basename='pos-session')
router.register(r'orders', POSOrderViewSet, basename='pos-order')

# The API URLs are now determined automatically by the router
urlpatterns = [
    path('', include(router.urls)),
]
