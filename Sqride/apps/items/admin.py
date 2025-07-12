from django.contrib import admin
from .models import Category, Modifier, Item, ItemIngredient
from unfold.admin import ModelAdmin

@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ('name', 'restaurant', 'is_active', 'created_at')
    list_filter = ('restaurant', 'is_active')
    search_fields = ('name', 'restaurant__name')
    ordering = ('name',)

@admin.register(Modifier)
class ModifierAdmin(ModelAdmin):
    list_display = ('title', 'restaurant', 'ingredient', 'cost', 'price', 'is_active')
    list_filter = ('restaurant', 'is_active')
    search_fields = ('title', 'ingredient__name', 'restaurant__name')
    ordering = ('title',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('restaurant', 'ingredient')

class ItemIngredientInline(admin.TabularInline):
    model = ItemIngredient
    extra = 1
    fields = ('ingredients', 'quantity', 'unit')
    autocomplete_fields = ['ingredients']  # Add autocomplete for better UX


@admin.register(Item)
class ItemAdmin(ModelAdmin):
    list_display = ('name', 'branch', 'category', 'cost', 'price', 'is_active')
    list_filter = ('branch', 'category', 'is_active')
    search_fields = ('name', 'branch__name', 'category__name')
    ordering = ('name',)
    inlines = [ItemIngredientInline]
    filter_horizontal = ('modifiers',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('branch', 'category')
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.calculate_cost()  # Recalculate cost after saving

@admin.register(ItemIngredient)
class ItemIngredientAdmin(ModelAdmin):
    list_display = ('item', 'ingredients', 'quantity', 'unit')
    list_filter = ('unit',)
    search_fields = ('item__name', 'inventory__ingredient_name')
    autocomplete_fields = ['item', 'ingredients']