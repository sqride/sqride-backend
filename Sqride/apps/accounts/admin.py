from django.contrib import admin
from .models import *
from unfold.admin import ModelAdmin

@admin.register(SuperAdmin)
class SuperAdminAdmin(ModelAdmin):
    list_display = ['username','email','is_active','is_staff','is_super_admin']
    list_filter = ['is_active','is_staff','is_super_admin','created_at','updated_at','deleted_at']
    search_fields = ['username','email']

@admin.register(Owner)
class OwnerAdmin(ModelAdmin):
    list_display = ['id','super_admin','username','name','email']
    list_filter = ['super_admin','created_at','updated_at','deleted_at']
    search_fields = ['username','name','email']

@admin.register(UserRole)
class UserRoleAdmin(ModelAdmin):
    list_display = ['id','name','branch']
    list_filter = ['created_at','updated_at','deleted_at']
    search_fields = ['name','branch']

@admin.register(User)
class UserAdmin(ModelAdmin):
    list_display = ['id','branch','role','name','email']
    list_filter = ['created_at','updated_at','deleted_at']
    search_fields = ['name','email']
    
@admin.register(BranchOwner)
class BranchOwnerAdmin(ModelAdmin):
    list_display = ['id','name','username','email','branch']
    list_filter = ['created_at','updated_at','deleted_at','branch']
    search_fields = ['name','username','email']
    
