from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction
from .models import KitchenStation, KitchenOrder, KitchenOrderItem, KitchenDisplay, KitchenAnalytics, KitchenStaff
from .serializers import (
    KitchenStationSerializer, KitchenOrderSerializer,
    KitchenOrderItemSerializer, KitchenDisplaySerializer,
    KitchenStaffSerializer, KitchenAnalyticsSerializer
)
from accounts.permissions import HasRolePermission, IsOwnerOrSuperAdmin
from .services import KitchenSystemService, KitchenAssignmentService, KitchenNotificationService
from django.db.models import Avg, Count, Sum
from datetime import timedelta

# Create your views here.

class KitchenStationViewSet(viewsets.ModelViewSet):
    queryset = KitchenStation.objects.all()
    serializer_class = KitchenStationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """
        Override get_permissions to use different permissions for session operations
        """
        return [IsAuthenticated(), HasRolePermission('kitchen_display')]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'branch'):
            return KitchenStation.objects.filter(branch=user.branch)
        return KitchenStation.objects.none()

    def perform_create(self, serializer):
        serializer.save(branch=self.request.user.branch)

    @action(detail=True, methods=['get'])
    def orders(self, request, pk=None):
        station = self.get_object()
        orders = KitchenOrderItem.objects.filter(
            station=station,
            status__in=['pending', 'preparing']
        ).select_related('kitchen_order', 'order_item')
        
        serializer = KitchenOrderItemSerializer(orders, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def staff(self, request, pk=None):
        station = self.get_object()
        staff = KitchenStaff.objects.filter(station=station)
        serializer = KitchenStaffSerializer(staff, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        station = self.get_object()
        analytics = KitchenAnalytics.objects.filter(station=station)
        serializer = KitchenAnalyticsSerializer(analytics, many=True)
        return Response(serializer.data)

class KitchenOrderViewSet(viewsets.ModelViewSet):
    queryset = KitchenOrder.objects.all()
    serializer_class = KitchenOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """
        Override get_permissions to use different permissions for session operations
        """
        return [IsAuthenticated(), HasRolePermission('kitchen_display')]
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'branch'):
            return KitchenOrder.objects.filter(order__branch=user.branch)
        return KitchenOrder.objects.none()

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        order = self.get_object()
        
        if order.status != 'pending':
            return Response(
                {"error": "Order is not in pending status"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            order.status = 'preparing'
            order.save()
            
            # Update all items
            order.items.update(status='preparing', started_at=timezone.now())
            
            # Notify kitchen
            KitchenNotificationService.notify_kitchen_update(
                order.order.branch.id,
                order.id,
                'preparing'
            )
        
        return Response({"message": "Order preparation started"})

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        order = self.get_object()
        
        if order.status != 'preparing':
            return Response(
                {"error": "Order is not in preparing status"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            order.status = 'completed'
            order.completed_at = timezone.now()
            order.save()
            
            # Update all items
            order.items.update(
                status='completed',
                completed_at=timezone.now()
            )
            
            # Update analytics
            self._update_analytics(order)
            
            # Notify kitchen
            KitchenNotificationService.notify_kitchen_update(
                order.order.branch.id,
                order.id,
                'completed'
            )
        
        return Response({"message": "Order completed"})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        
        if order.status in ['completed', 'cancelled']:
            return Response(
                {"error": "Order cannot be cancelled"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            order.status = 'cancelled'
            order.save()
            
            # Update all items
            order.items.update(status='cancelled')
            
            # Notify kitchen
            KitchenNotificationService.notify_kitchen_update(
                order.order.branch.id,
                order.id,
                'cancelled'
            )
        
        return Response({"message": "Order cancelled"})

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        order = self.get_object()
        staff_id = request.data.get('staff_id')
        
        try:
            staff = KitchenStaff.objects.get(id=staff_id)
        except KitchenStaff.DoesNotExist:
            return Response(
                {"error": "Staff not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not staff.is_available:
            return Response(
                {"error": "Staff is not available"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            staff.current_order = order
            staff.is_available = False
            staff.save()
        
        return Response({"message": "Order assigned to staff"})

    def _update_analytics(self, order):
        """Update analytics for completed order"""
        for item in order.items.all():
            if item.station:
                analytics, _ = KitchenAnalytics.objects.get_or_create(
                    station=item.station,
                    date=timezone.now().date()
                )
                
                preparation_time = item.completed_at - item.started_at
                
                analytics.total_orders += 1
                analytics.average_preparation_time = (
                    (analytics.average_preparation_time or timedelta(0)) + preparation_time
                ) / 2
                
                if preparation_time > timedelta(minutes=15):  # SLA breach threshold
                    analytics.sla_breaches += 1
                
                analytics.save()

class KitchenOrderItemViewSet(viewsets.ModelViewSet):
    queryset = KitchenOrderItem.objects.all()
    serializer_class = KitchenOrderItemSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """
        Override get_permissions to use different permissions for session operations
        """
        return [IsAuthenticated(), HasRolePermission('kitchen_display')]


    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'branch'):
            return KitchenOrderItem.objects.filter(
                kitchen_order__order__branch=user.branch
            )
        return KitchenOrderItem.objects.none()

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        item = self.get_object()
        
        if item.status != 'pending':
            return Response(
                {"error": "Item is not in pending status"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            item.status = 'preparing'
            item.started_at = timezone.now()
            item.prepared_by = request.user
            item.save()
            
            # Notify kitchen
            KitchenNotificationService.notify_kitchen_update(
                item.kitchen_order.order.branch.id,
                item.kitchen_order.id,
                'item_started'
            )
        
        return Response({"message": "Item preparation started"})

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        item = self.get_object()
        
        if item.status != 'preparing':
            return Response(
                {"error": "Item is not in preparing status"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            item.status = 'completed'
            item.completed_at = timezone.now()
            item.save()
            
            # Check if all items are completed
            kitchen_order = item.kitchen_order
            if all(i.status == 'completed' for i in kitchen_order.items.all()):
                kitchen_order.status = 'ready'
                kitchen_order.save()
            
            # Notify kitchen
            KitchenNotificationService.notify_kitchen_update(
                item.kitchen_order.order.branch.id,
                item.kitchen_order.id,
                'item_completed'
            )
        
        return Response({"message": "Item completed"})

class KitchenDisplayViewSet(viewsets.ModelViewSet):
    queryset = KitchenDisplay.objects.all()
    serializer_class = KitchenDisplaySerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """
        Override get_permissions to use different permissions for session operations
        """
        return [IsAuthenticated(), HasRolePermission('kitchen_display')]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'branch'):
            return KitchenDisplay.objects.filter(branch=user.branch)
        return KitchenDisplay.objects.none()

    def perform_create(self, serializer):
        serializer.save(branch=self.request.user.branch)

    @action(detail=True, methods=['get'])
    def active_orders(self, request, pk=None):
        display = self.get_object()
        stations = display.stations.all()
        
        orders = KitchenOrder.objects.filter(
            items__station__in=stations,
            status__in=['pending', 'preparing']
        ).distinct()
        
        serializer = KitchenOrderSerializer(orders, many=True)
        return Response(serializer.data)

class KitchenSystemViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsOwnerOrSuperAdmin]
    
    @action(detail=True, methods=['post'])
    def enable(self, request, pk=None):
        """
        Enable kitchen system for a branch
        """
        success, message = KitchenSystemService.enable_kitchen_system(pk)
        
        if success:
            return Response({"message": message}, status=status.HTTP_200_OK)
        return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        """
        Disable kitchen system for a branch
        """
        success, message = KitchenSystemService.disable_kitchen_system(pk)
        
        if success:
            return Response({"message": message}, status=status.HTTP_200_OK)
        return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['patch'])
    def update_settings(self, request, pk=None):
        """
        Update kitchen settings for a branch
        """
        success, message = KitchenSystemService.update_kitchen_settings(pk, request.data)
        
        if success:
            return Response({"message": message}, status=status.HTTP_200_OK)
        return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)

class KitchenAnalyticsViewSet(viewsets.ViewSet):
    @action(detail=True, methods=['get'])
    def station_performance(self, request, pk=None):
        station = KitchenStation.objects.get(pk=pk)
        analytics = KitchenAnalytics.objects.filter(station=station)
        return Response(analytics)

    @action(detail=True, methods=['get'])
    def staff_performance(self, request, pk=None):
        staff = KitchenStaff.objects.get(pk=pk)
        completed_orders = KitchenOrderItem.objects.filter(
            prepared_by=staff.user,
            status='completed'
        )
        return Response({
            'total_orders': completed_orders.count(),
            'average_time': completed_orders.aggregate(
                avg_time=Avg('completed_at' - 'started_at')
            )
        })

    @action(detail=False, methods=['get'])
    def overview(self, request):
        branch = request.user.branch
        
        analytics = {
            'total_orders': KitchenOrder.objects.filter(
                order__branch=branch
            ).count(),
            'active_orders': KitchenOrder.objects.filter(
                order__branch=branch,
                status__in=['pending', 'preparing']
            ).count(),
            'completed_orders': KitchenOrder.objects.filter(
                order__branch=branch,
                status='completed'
            ).count(),
            'sla_breaches': KitchenAnalytics.objects.filter(
                station__branch=branch
            ).aggregate(
                total=Sum('sla_breaches')
            )['total'] or 0
        }
        
        return Response(analytics)

    @action(detail=False, methods=['get'])
    def stations(self, request):
        branch = request.user.branch
        
        stations = KitchenStation.objects.filter(branch=branch)
        analytics = []
        
        for station in stations:
            station_analytics = KitchenAnalytics.objects.filter(
                station=station
            ).aggregate(
                total_orders=Sum('total_orders'),
                avg_time=Avg('average_preparation_time'),
                sla_breaches=Sum('sla_breaches')
            )
            
            analytics.append({
                'station': station.name,
                **station_analytics
            })
        
        return Response(analytics)

    @action(detail=False, methods=['get'])
    def daily(self, request):
        branch = request.user.branch
        date = request.query_params.get('date', timezone.now().date())
        
        analytics = KitchenAnalytics.objects.filter(
            station__branch=branch,
            date=date
        ).aggregate(
            total_orders=Sum('total_orders'),
            avg_time=Avg('average_preparation_time'),
            sla_breaches=Sum('sla_breaches')
        )
        
        return Response(analytics)

class KitchenNotificationViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def list(self, request):
        branch = request.user.branch
        notifications = KitchenNotificationService.get_notifications(branch)
        return Response(notifications)

    @action(detail=False, methods=['post'])
    def read(self, request):
        notification_id = request.data.get('notification_id')
        KitchenNotificationService.mark_as_read(notification_id)
        return Response({"message": "Notification marked as read"})

    @action(detail=False, methods=['post'])
    def clear(self, request):
        branch = request.user.branch
        KitchenNotificationService.clear_notifications(branch)
        return Response({"message": "All notifications cleared"})

class KitchenStaffViewSet(viewsets.ModelViewSet):
    queryset = KitchenStaff.objects.all()
    serializer_class = KitchenStaffSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'branch'):
            return KitchenStaff.objects.filter(station__branch=user.branch)
        return KitchenStaff.objects.none()

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        staff = self.get_object()
        station_id = request.data.get('station_id')
        
        try:
            station = KitchenStation.objects.get(id=station_id)
        except KitchenStation.DoesNotExist:
            return Response(
                {"error": "Station not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        with transaction.atomic():
            staff.station = station
            staff.save()
        
        return Response({"message": "Staff assigned to station"})

    @action(detail=True, methods=['post'])
    def unassign(self, request, pk=None):
        staff = self.get_object()
        
        with transaction.atomic():
            staff.station = None
            staff.save()
        
        return Response({"message": "Staff unassigned from station"})

    @action(detail=True, methods=['get'])
    def performance(self, request, pk=None):
        staff = self.get_object()
        
        completed_items = KitchenOrderItem.objects.filter(
            prepared_by=staff.user,
            status='completed'
        )
        
        total_orders = completed_items.count()
        avg_time = completed_items.aggregate(
            avg_time=Avg('completed_at' - 'started_at')
        )['avg_time']
        
        return Response({
            'total_orders': total_orders,
            'average_preparation_time': avg_time,
            'current_order': staff.current_order.id if staff.current_order else None
        })
