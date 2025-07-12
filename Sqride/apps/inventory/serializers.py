from rest_framework import serializers
from .models import *

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryCategory
        fields = '__all__'
        ref_name = 'InventoryCategory'  # Unique name for this serializer


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'

class InventorySerializer(serializers.ModelSerializer):
    is_expired = serializers.SerializerMethodField()
    is_low_stock = serializers.SerializerMethodField()
    
    class Meta:
        model = Inventory
        fields = '__all__'
    
    def get_is_expired(self, obj):
        return obj.is_expired()

    def get_is_low_stock(self, obj):
        return obj.is_low_stock()

class PurchaseOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrder
        fields = '__all__'

class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrderItem
        fields = '__all__'
        read_only_fields = ['total_price']

    def validate(self, attrs):
        inventory = attrs.get('inventory')
        unit_price = attrs.get('unit_price')
        print(inventory.price)
        
        if self.instance is None and unit_price is None:
            if inventory and inventory.price:  # Assuming your Inventory model has unit_price
                attrs['unit_price'] = inventory.price
            else:
                raise serializers.ValidationError({
                    "unit_price": "Unit price is missing and cannot be auto-resolved from inventory."
                })
        return attrs
    
class InventoryTransactionSerializer(serializers.ModelSerializer):
    # content_type = serializers.PrimaryKeyRelatedField(
    #     queryset=ContentType.objects.get_for_models(PurchaseOrderItem).values()
    # )
    class Meta:
        model = InventoryTransaction
        fields = '__all__'

class StockAdjustmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockAdjustment
        fields = '__all__'
        

    