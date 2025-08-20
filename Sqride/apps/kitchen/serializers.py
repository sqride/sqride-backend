from rest_framework import serializers
from .models import KitchenStation, KitchenOrder, KitchenOrderItem, KitchenDisplay, KitchenStaff, KitchenAnalytics, KitchenNotification
from orders.serializers import OrderSerializer, OrderItemSerializer
from accounts.serializers.user_serializers import UserSerializer

class KitchenStationSerializer(serializers.ModelSerializer):
    class Meta:
        model = KitchenStation
        fields = '__all__'
        read_only_fields = ('branch',)

class KitchenOrderItemSerializer(serializers.ModelSerializer):
    order_item = OrderItemSerializer(read_only=True)
    station = KitchenStationSerializer(read_only=True)
    prepared_by = UserSerializer(read_only=True)
    station_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = KitchenOrderItem
        fields = '__all__'
        read_only_fields = ('kitchen_order', 'started_at', 'completed_at')

class KitchenOrderSerializer(serializers.ModelSerializer):
    items = KitchenOrderItemSerializer(many=True, read_only=True)
    order = OrderSerializer(read_only=True)
    estimated_completion_time = serializers.DateTimeField(required=False)
    priority = serializers.IntegerField(required=False, default=0)
    
    class Meta:
        model = KitchenOrder
        fields = '__all__'
        read_only_fields = ('completed_at', 'preparation_time')

class KitchenDisplaySerializer(serializers.ModelSerializer):
    stations = KitchenStationSerializer(many=True, read_only=True)
    station_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = KitchenDisplay
        fields = '__all__'
        read_only_fields = ('branch',)

    def create(self, validated_data):
        station_ids = validated_data.pop('station_ids', [])
        display = super().create(validated_data)
        
        if station_ids:
            stations = KitchenStation.objects.filter(id__in=station_ids, branch=display.branch)
            display.stations.set(stations)
        
        return display

    def update(self, instance, validated_data):
        station_ids = validated_data.pop('station_ids', None)
        display = super().update(instance, validated_data)
        
        if station_ids is not None:
            stations = KitchenStation.objects.filter(id__in=station_ids, branch=display.branch)
            display.stations.set(stations)
        
        return display

class KitchenStaffSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    station = KitchenStationSerializer(read_only=True)
    station_id = serializers.IntegerField(write_only=True)
    current_order = KitchenOrderSerializer(read_only=True)
    
    class Meta:
        model = KitchenStaff
        fields = '__all__'

class KitchenAnalyticsSerializer(serializers.ModelSerializer):
    station = KitchenStationSerializer(read_only=True)
    station_name = serializers.CharField(source='station.name', read_only=True)
    
    class Meta:
        model = KitchenAnalytics
        fields = '__all__'
        read_only_fields = ('date',)

class KitchenNotificationSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    
    class Meta:
        model = KitchenNotification
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

class KitchenWorkloadSerializer(serializers.Serializer):
    """Serializer for station workload data"""
    station_name = serializers.CharField()
    pending = serializers.IntegerField()
    preparing = serializers.IntegerField()
    total = serializers.IntegerField()
    staff_count = serializers.IntegerField()
    available_staff = serializers.IntegerField()

class KitchenPerformanceSerializer(serializers.Serializer):
    """Serializer for kitchen performance metrics"""
    total_orders = serializers.IntegerField()
    active_orders = serializers.IntegerField()
    completed_orders = serializers.IntegerField()
    sla_breaches = serializers.IntegerField()
    average_preparation_time = serializers.DurationField(allow_null=True)
    peak_hours = serializers.JSONField()