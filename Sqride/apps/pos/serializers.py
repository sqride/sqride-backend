from rest_framework import serializers
from .models import POSSession, POSOrder, POSOrderItem
from orders.serializers import OrderSerializer
from items.serializers import ItemSerializer
from restaurants.serializers import RestaurantTableSerializer

class POSOrderItemSerializer(serializers.ModelSerializer):
    item_details = ItemSerializer(source='item', read_only=True)
    
    class Meta:
        model = POSOrderItem
        fields = [
            'id', 'item', 'item_details', 'quantity', 'unit_price',
            'subtotal', 'notes', 'is_void', 'void_reason',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class POSOrderItemInputSerializer(serializers.Serializer):
    item = serializers.IntegerField(required=True)
    quantity = serializers.IntegerField(default=1, min_value=1)
    notes = serializers.CharField(required=False, allow_null=True)

class POSOrderSerializer(serializers.ModelSerializer):
    order_details = OrderSerializer(source='order', read_only=True)
    table_details = RestaurantTableSerializer(source='table', read_only=True)
    pos_items = POSOrderItemSerializer(many=True, read_only=True)
    items = POSOrderItemInputSerializer(many=True, write_only=True, required=False)
    
    class Meta:
        model = POSOrder
        fields = [
            'id', 'order', 'order_details', 'pos_session',
            'table', 'table_details', 'payment_status',
            'payment_method', 'pos_items', 'items',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class POSSessionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    
    class Meta:
        model = POSSession
        fields = [
            'id', 'user', 'user_name', 'branch', 'branch_name',
            'start_time', 'end_time', 'is_active', 'total_sales',
            'total_orders'
        ]
        read_only_fields = ['start_time', 'end_time', 'total_sales', 'total_orders']
