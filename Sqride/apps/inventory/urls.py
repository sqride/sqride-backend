from django.urls import path, include
from rest_framework.routers import DefaultRouter
from inventory.views import *

router = DefaultRouter()
router.register('inventory-categories', CategoryViewSet)
router.register('suppliers', SupplierViewSet)
router.register('items', InventoryViewSet)
router.register('purchase-orders', PurchaseOrderViewSet)
router.register('purchase-order-items', PurchaseOrderItemViewSet)
router.register('transactions', InventoryTransactionViewSet)


urlpatterns = [
    path('', include(router.urls)),
]
