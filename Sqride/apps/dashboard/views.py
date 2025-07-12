from rest_framework import viewsets,status,views
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from django.utils import timezone
from datetime import timedelta

from restaurants.models import Branch
from orders.models import Order, OrderItem
from .serializers import BranchDashboardInsightsSerializer

class BranchDashboardInsightsViewSet(views.APIView):
    queryset = Branch.objects.all()
    serializer_class = BranchDashboardInsightsSerializer
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        branch = getattr(user, 'branch', None)
        if not branch:
            return Response({'detail': 'No branch associated with this user.'}, status=404)

        # Total revenue
        total_revenue = Order.objects.filter(
            branch=branch, status='completed'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        
        total_cost = OrderItem.objects.filter(order__branch=branch,order__status='completed')
        # net_profit = total_revenue - total_cost
        print(total_cost)
        data = {
            'total_revenue': total_revenue,
            'net_profit': 0,
            'item_sales': {},
            'sales_by_month':{} ,
            'sales_by_week': {},
        }
        serializer = BranchDashboardInsightsSerializer(data)
        return Response(serializer.data)