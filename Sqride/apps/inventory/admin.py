from django.contrib import admin
from .models import *
from unfold.admin import ModelAdmin
@admin.register(Supplier)
class SupplierAdmin(ModelAdmin): 
    list_display = ('supplier_id', 'supplier_name', 'contact_details', 'email', 'address')
    search_fields = ('supplier_name', 'contact_details', 'email', 'address')
    list_filter = ('supplier_name', 'contact_details', 'email', 'address')
    ordering = ('supplier_name',)
    list_per_page = 20

@admin.register(InventoryCategory)
class InventoryCategoryAdmin(ModelAdmin):
    list_display = ('inventory_category_id', 'category_name')
    search_fields = ('category_name',)
    list_filter = ('category_name',)
    ordering = ('category_name',)
    list_per_page = 20

@admin.register(Inventory)
class InventoryAdmin(ModelAdmin):
    list_display = ('inventory_id', 'branch', 'category', 'supplier', 'ingredient_name', 'unit', 'cost', 'price', 'available_quantity', 'low_stock_alert', 'batch_number', 'expiry_date', 'created_at', 'deleted_at')
    search_fields = ('ingredient_name', 'unit', 'cost', 'price', 'available_quantity', 'low_stock_alert', 'batch_number', 'expiry_date', 'created_at', 'deleted_at')
    list_filter = ('ingredient_name', 'unit', 'cost', 'price', 'available_quantity', 'low_stock_alert', 'batch_number', 'expiry_date', 'created_at', 'deleted_at')
    ordering = ('ingredient_name',)
    list_per_page = 20

@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(ModelAdmin):
    list_display = ('transaction_id', 'inventory', 'transaction_type', 'quantity_change', 'transaction_date')
    search_fields = ('transaction_id', 'inventory', 'transaction_type', 'quantity_change',  'transaction_date')
    list_filter = ('transaction_id', 'inventory', 'transaction_type', 'quantity_change', 'transaction_date')
    ordering = ('transaction_id',)
    list_per_page = 20
    
    # def formfield_for_foreignkey(self, db_field, request, **kwargs):
    #     if db_field.name == "content_type":
    #         allowed_models = [PurchaseOrder]  # Add allowed models
    #         model_map = ContentType.objects.get_for_models(*allowed_models)
    #         kwargs["queryset"] = ContentType.objects.filter(id__in=[ct.id for ct in model_map.values()])
    #     return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(StockAdjustment)
class StockAdjustmentAdmin(ModelAdmin):
    list_display = ('adjustment_id', 'inventory', 'reason', 'quantity_adjusted','adjusted_by', 'adjusted_at')
    search_fields = ('adjustment_id', 'inventory', 'reason', 'quantity_adjusted','adjusted_by', 'adjusted_at')
    list_filter = ('adjustment_id', 'inventory', 'reason', 'quantity_adjusted')
    ordering = ('adjustment_id',)
    list_per_page = 20

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(ModelAdmin):
    list_display = ('purchase_order_id', 'supplier','branch', 'purchased_by','order_date', 'received_date', 'total_cost', 'status')
    search_fields = ('purchase_order_id', 'supplier', 'order_date', 'received_date', 'status')
    list_filter = ('purchase_order_id', 'supplier', 'order_date', 'received_date', 'status')
    ordering = ('purchase_order_id',)
    list_per_page = 20

@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(ModelAdmin):
    list_display = ('purchase_order_item_id', 'purchase_order', 'inventory', 'quantity', 'unit_price', 'total_price')
    search_fields = ('purchase_order_item_id', 'purchase_order', 'inventory', 'quantity', 'unit_price', 'total_price')
    list_filter = ('purchase_order_item_id', 'purchase_order', 'inventory', 'quantity', 'unit_price', 'total_price')
    ordering = ('purchase_order_item_id',)
    list_per_page = 20

