from django.contrib import admin
from .models import POSSession, POSOrder, POSOrderItem
from unfold.admin import ModelAdmin

@admin.register(POSSession)
class POSSessionAdmin(ModelAdmin):
    list_display = ['id', 'user', 'branch', 'start_time', 'end_time', 'is_active', 'total_sales', 'total_orders']
    list_filter = ['is_active', 'branch', 'start_time']
    search_fields = ['user__username', 'branch__name']
    readonly_fields = ['start_time', 'end_time', 'total_sales', 'total_orders']
    ordering = ['-start_time']

@admin.register(POSOrder)
class POSOrderAdmin(ModelAdmin):
    list_display = ['id', 'order', 'pos_session', 'table', 'payment_status', 'payment_method']
    list_filter = ['payment_status', 'payment_method', 'pos_session']
    search_fields = ['order__order_id', 'pos_session__user__username']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

@admin.register(POSOrderItem)
class POSOrderItemAdmin(ModelAdmin):
    list_display = ['id', 'pos_order', 'item', 'quantity', 'unit_price', 'subtotal', 'is_void']
    list_filter = ['is_void', 'pos_order__payment_status']
    search_fields = ['item__name', 'pos_order__order__order_id']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
