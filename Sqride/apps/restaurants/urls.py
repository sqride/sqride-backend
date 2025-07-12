from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RestaurantViewSet, BranchViewSet, RestaurantCategoryViewSet,
    RestaurantTableViewSet, RestaurantZoneViewSet, RestaurantHolidayViewSet
)

router = DefaultRouter()
router.register(r"restaurants", RestaurantViewSet, basename="restaurants")
router.register(r"branches", BranchViewSet, basename="branches")
router.register(r"categories", RestaurantCategoryViewSet, basename="categories")
router.register(r"tables", RestaurantTableViewSet, basename="tables")
router.register(r"zones", RestaurantZoneViewSet, basename="zones")
router.register(r"holidays", RestaurantHolidayViewSet, basename="holidays")

urlpatterns = [
    path("", include(router.urls)),
]