from rest_framework import serializers
from .models import KitchenStation, KitchenOrder, KitchenOrderItem, KitchenDisplay, KitchenStaff, KitchenAnalytics
from orders.serializers import OrderSerializer, OrderItemSerializer

class KitchenStationSerializer(serializers.ModelSerializer):
    class Meta:
        model = KitchenStation
        fields = '__all__'

class KitchenOrderItemSerializer(serializers.ModelSerializer):
    order_item = OrderItemSerializer(read_only=True)
    station = KitchenStationSerializer(read_only=True)
    prepared_by = serializers.StringRelatedField()
    
    class Meta:
        model = KitchenOrderItem
        fields = '__all__'

class KitchenOrderSerializer(serializers.ModelSerializer):
    items = KitchenOrderItemSerializer(many=True, read_only=True)
    order = OrderSerializer(read_only=True)
    
    class Meta:
        model = KitchenOrder
        fields = '__all__'

class KitchenDisplaySerializer(serializers.ModelSerializer):
    stations = KitchenStationSerializer(many=True, read_only=True)
    
    class Meta:
        model = KitchenDisplay
        fields = '__all__'

class KitchenStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = KitchenStaff
        fields = '__all__'

class KitchenAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = KitchenAnalytics
        fields = '__all__'