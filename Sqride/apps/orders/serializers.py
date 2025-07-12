from rest_framework import serializers
from .models import Order, OrderItem, OrderStatusHistory
from django.core.exceptions import ValidationError

class OrderStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source='changed_by.get_full_name', read_only=True)
    
    class Meta:
        model = OrderStatusHistory
        fields = ['from_status', 'to_status', 'changed_by_name', 'changed_at', 'notes']
        read_only_fields = ['from_status', 'to_status', 'changed_by_name', 'changed_at']

class OrderItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['order_item_id', 'item', 'item_name', 'quantity', 'price']
        read_only_fields = ['order_item_id', 'price']

    def validate(self, data):
        """Validate the order item data"""
        item = data.get('item')
        quantity = data.get('quantity')
        
        if not item:
            raise serializers.ValidationError({"item": "Item is required."})

        # Validate price
        if data.get('price') != item.price:
            raise serializers.ValidationError({
                "price": f"Price mismatch. Current price for {item.name} is {item.price}."
            })

        return data

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    status_changed_by_name = serializers.CharField(source='status_changed_by.get_full_name', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'order_id', 'branch', 'customer', 'order_type',
            'total_amount', 'currency', 'status', 'items',
            'status_changed_at', 'status_changed_by_name',
            'status_history'
        ]
        read_only_fields = ['order_id', 'total_amount', 'currency', 'status_changed_at', 'status_changed_by_name']

    def validate_status(self, value):
        """Validate status changes"""
        instance = getattr(self, 'instance', None)
        if instance and instance.status != value:
            try:
                instance.validate_status_transition(value, self.context.get('request').user)
            except ValidationError as e:
                raise serializers.ValidationError(str(e))
        return value