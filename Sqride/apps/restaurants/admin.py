from django.contrib import admin
from .models import (
    Restaurant, Branch, RestaurantCategory, 
    RestaurantTable, RestaurantZone, RestaurantHoliday,
    Currency
)
from unfold.admin import ModelAdmin

@admin.register(Currency)
class CurrencyAdmin(ModelAdmin):
    list_display = ('currency_code', 'exchange_rate')
    search_fields = ('currency_code',)
    ordering = ('currency_code',)

@admin.register(Restaurant)
class RestaurantAdmin(ModelAdmin):
    list_display = ('id', 'name', 'owner', 'is_active', 'subscription_status', 'subscription_end_date')
    list_filter = ('is_active', 'subscription_status', 'owner')
    search_fields = ('name', 'owner__name', 'email', 'phone')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'owner', 'description', 'logo')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'website')
        }),
        ('Business Details', {
            'fields': ('tax_id', 'opening_time', 'closing_time')
        }),
        ('Subscription', {
            'fields': ('is_active', 'subscription_status', 'subscription_end_date')
        }),
        ('Settings', {
            'fields': ('settings',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(Branch)
class BranchAdmin(ModelAdmin):
    list_display = ('name', 'restaurant', 'is_active', 'is_delivery_available', 'is_pickup_available', 'is_dine_in_available')
    list_filter = ('is_active', 'is_delivery_available', 'is_pickup_available', 'is_dine_in_available', 'restaurant')
    search_fields = ('name', 'restaurant__name', 'address', 'phone')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'restaurant', 'address','currency')
        }),
        ('Contact Information', {
            'fields': ('phone', 'email')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude')
        }),
        ('Settings', {
            'fields': ('is_active', 'is_delivery_available', 'is_pickup_available', 'is_dine_in_available', 'operating_hours', 'settings')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(RestaurantCategory)
class RestaurantCategoryAdmin(ModelAdmin):
    list_display = ('name', 'restaurant', 'is_active', 'display_order')
    list_filter = ('is_active', 'restaurant')
    search_fields = ('name', 'restaurant__name', 'description')
    ordering = ('display_order', 'name')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(RestaurantTable)
class RestaurantTableAdmin(ModelAdmin):
    list_display = ('table_number', 'branch', 'capacity', 'status', 'is_active')
    list_filter = ('status', 'is_active', 'branch__restaurant')
    search_fields = ('table_number', 'branch__name', 'branch__restaurant__name')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(RestaurantZone)
class RestaurantZoneAdmin(ModelAdmin):
    list_display = ('name', 'branch', 'is_active')
    list_filter = ('is_active', 'branch__restaurant')
    search_fields = ('name', 'branch__name', 'description')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(RestaurantHoliday)
class RestaurantHolidayAdmin(ModelAdmin):
    list_display = ('name', 'restaurant', 'date', 'is_recurring')
    list_filter = ('is_recurring', 'restaurant')
    search_fields = ('name', 'restaurant__name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'date'

