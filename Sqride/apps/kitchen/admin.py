from django.contrib import admin
from .models import (
    KitchenStation, KitchenOrder, KitchenOrderItem, 
    KitchenDisplay, KitchenStaff, KitchenAnalytics, KitchenNotification
)

@admin.register(KitchenStation)
class KitchenStationAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch', 'is_active', 'created_at')
    list_filter = ('branch', 'is_active', 'created_at')
    search_fields = ('name', 'branch__name')
    list_editable = ('is_active',)
    ordering = ('branch', 'name')

@admin.register(KitchenOrder)
class KitchenOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'status', 'priority', 'branch', 'created_at')
    list_filter = ('status', 'priority', 'order__branch', 'created_at')
    search_fields = ('order__order_id', 'order__branch__name')
    list_editable = ('status', 'priority')
    ordering = ('-created_at',)
    readonly_fields = ('preparation_time',)
    
    def branch(self, obj):
        return obj.order.branch.name if obj.order and obj.order.branch else 'N/A'
    branch.short_description = 'Branch'

@admin.register(KitchenOrderItem)
class KitchenOrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'kitchen_order', 'item_name', 'station', 'status', 'prepared_by', 'started_at')
    list_filter = ('status', 'station', 'kitchen_order__order__branch', 'created_at')
    search_fields = ('kitchen_order__order__order_id', 'order_item__item__name', 'station__name')
    list_editable = ('status', 'station')
    ordering = ('-created_at',)
    readonly_fields = ('kitchen_order', 'order_item')
    
    def item_name(self, obj):
        return obj.order_item.item.name if obj.order_item and obj.order_item.item else 'N/A'
    item_name.short_description = 'Item Name'

@admin.register(KitchenDisplay)
class KitchenDisplayAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch', 'display_type', 'is_active', 'stations_count', 'created_at')
    list_filter = ('branch', 'display_type', 'is_active', 'created_at')
    search_fields = ('name', 'branch__name')
    list_editable = ('is_active', 'display_type')
    ordering = ('branch', 'name')
    filter_horizontal = ('stations',)
    
    def stations_count(self, obj):
        return obj.stations.count()
    stations_count.short_description = 'Stations'

@admin.register(KitchenStaff)
class KitchenStaffAdmin(admin.ModelAdmin):
    list_display = ('user', 'station', 'is_available', 'current_order', 'branch')
    list_filter = ('station__branch', 'is_available', 'station', 'created_at')
    search_fields = ('user__username', 'user__name', 'station__name')
    list_editable = ('is_available',)
    ordering = ('station__branch', 'station', 'user__username')
    
    def branch(self, obj):
        return obj.station.branch.name if obj.station and obj.station.branch else 'N/A'
    branch.short_description = 'Branch'

@admin.register(KitchenAnalytics)
class KitchenAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('station', 'date', 'total_orders', 'sla_breaches', 'avg_prep_time')
    list_filter = ('station__branch', 'date', 'station')
    search_fields = ('station__name', 'station__branch__name')
    ordering = ('-date', 'station__name')
    readonly_fields = ('date',)
    
    def avg_prep_time(self, obj):
        if obj.average_preparation_time:
            total_seconds = obj.average_preparation_time.total_seconds()
            minutes = int(total_seconds // 60)
            seconds = int(total_seconds % 60)
            return f"{minutes}m {seconds}s"
        return 'N/A'
    avg_prep_time.short_description = 'Avg Prep Time'

@admin.register(KitchenNotification)
class KitchenNotificationAdmin(admin.ModelAdmin):
    list_display = ('branch', 'order_id', 'notification_type', 'status', 'is_read', 'created_at')
    list_filter = ('branch', 'notification_type', 'is_read', 'created_at')
    search_fields = ('branch__name', 'message')
    list_editable = ('is_read',)
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')