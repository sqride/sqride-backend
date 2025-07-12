from rest_framework import serializers
from restaurants.models import (
    Restaurant, Branch, RestaurantCategory, 
    RestaurantTable, RestaurantZone, RestaurantHoliday
)

class BranchSerializer(serializers.ModelSerializer):
    kitchen_enabled = serializers.BooleanField(read_only=True)
    kitchen_settings = serializers.JSONField(read_only=True)
    
    class Meta:
        model = Branch
        fields = '__all__'
        read_only_fields = ('restaurant',)

class RestaurantSerializer(serializers.ModelSerializer):
    branches = BranchSerializer(many=True, read_only=True)
    
    class Meta:
        model = Restaurant
        fields = '__all__'
        read_only_fields = ('owner',)
        
class RestaurantCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantCategory
        fields = '__all__'
        read_only_fields = ('restaurant',)

class RestaurantTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantTable
        fields = '__all__'
        read_only_fields = ('branch',)

class RestaurantZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantZone
        fields = '__all__'
        read_only_fields = ('branch',)

class RestaurantHolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantHoliday
        fields = '__all__'
        read_only_fields = ('restaurant',)