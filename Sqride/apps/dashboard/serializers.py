from rest_framework import serializers

class BranchDashboardInsightsSerializer(serializers.Serializer):
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_profit = serializers.DecimalField(max_digits=12, decimal_places=2)
    item_sales = serializers.DictField(child=serializers.IntegerField())
    sales_by_month = serializers.DictField(child=serializers.DecimalField(max_digits=12, decimal_places=2))
    sales_by_week = serializers.DictField(child=serializers.DecimalField(max_digits=12, decimal_places=2))