from django.contrib import admin
from .models import *
from unfold.admin import ModelAdmin

@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ('order_id', 'branch', 'customer', 'order_type', 'total_amount', 'currency', 'status','paid','paid_at', 'created_at')
    list_filter = ('status', 'order_type', 'branch')
    search_fields = ('customer__name', 'branch__name', 'status')
    ordering = ('-created_at',)

@admin.register(OrderItem)
class OrderItemAdmin(ModelAdmin):
    list_display = ('order_item_id', 'order', 'quantity', 'price')
    search_fields = ('order_id',)
    ordering = ('order',)