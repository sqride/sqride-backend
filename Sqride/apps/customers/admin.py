from django.contrib import admin
from .models import *
from unfold.admin import ModelAdmin

@admin.register(Customer)
class CustomerAdmin(ModelAdmin):
    list_display = ('customer_id', 'branch', 'name', 'phone', 'email', 'username', 'type', 'created_at')
    list_filter = ('type', 'branch')
    search_fields = ('name', 'phone', 'email', 'username')
    readonly_fields = ('created_at',)

    fieldsets = (
        (None, {'fields': ('branch', 'name', 'phone', 'email', 'username', 'password', 'type')}),
        ('Important Dates', {'fields': ('created_at', 'deleted_at')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('branch', 'name', 'phone', 'email', 'username', 'password', 'type'),
        }),
    )

    ordering = ('email',)

@admin.register(LoyaltyProgram)
class LoyalityProgramAdmin(ModelAdmin):
    list_display = ['customer', 'points_earned','points_redeemed','created_at']
    list_filter = ['customer']
    search_fields = ['customer']