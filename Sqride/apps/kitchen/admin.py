from django.contrib import admin
from .models import KitchenOrder, KitchenOrderItem, KitchenStation, KitchenDisplay, KitchenStaff, KitchenAnalytics
from unfold.admin import ModelAdmin

class KitchenOrderAdmin(ModelAdmin):
    list_display = ('id', 'order', 'status', 'priority', 'notes', 'completed_at')
    

class KitchenOrderItemAdmin(ModelAdmin):
    list_display = ('id', 'kitchen_order', 'order_item', 'station', 'status', 'prepared_by', 'started_at', 'completed_at', 'notes')
    

class KitchenStationAdmin(ModelAdmin):
    list_display = ('id', 'name', 'branch', 'is_active', 'description')

class KitchenDisplayAdmin(ModelAdmin):
    list_display = ('id', 'branch', 'name', 'is_active', 'display_type')

@admin.register(KitchenStaff)
class KitchenStaffAdmin(ModelAdmin):
    list_display = ('user', 'station', 'is_available', 'current_order')
    list_filter = ('station', 'is_available')
    search_fields = ('user__username', 'station__name')

@admin.register(KitchenAnalytics)
class KitchenAnalyticsAdmin(ModelAdmin):
    list_display = ('station', 'date', 'total_orders', 'sla_breaches')
    list_filter = ('station', 'date')

admin.site.register(KitchenOrder, KitchenOrderAdmin)
admin.site.register(KitchenOrderItem, KitchenOrderItemAdmin)
admin.site.register(KitchenStation, KitchenStationAdmin)
admin.site.register(KitchenDisplay, KitchenDisplayAdmin)