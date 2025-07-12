from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ItemIngredientViewSet, ModifierViewSet, ItemViewSet

router = DefaultRouter()
router.register('categories', CategoryViewSet, basename='category')
router.register('modifiers', ModifierViewSet, basename='modifier')
router.register('', ItemViewSet, basename='item')
router.register(r'item-ingredients', ItemIngredientViewSet, basename='item-ingredient')

urlpatterns = [
    path('', include(router.urls)),
]
