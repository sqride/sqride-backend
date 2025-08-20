from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction
from .models import KitchenStation, KitchenOrder, KitchenOrderItem, KitchenDisplay, KitchenAnalytics, KitchenStaff, KitchenNotification
from .serializers import (
    KitchenStationSerializer, KitchenOrderSerializer,
    KitchenOrderItemSerializer, KitchenDisplaySerializer,
    KitchenStaffSerializer, KitchenAnalyticsSerializer, KitchenNotificationSerializer,
    KitchenWorkloadSerializer, KitchenPerformanceSerializer
)
from accounts.permissions import HasRolePermission, IsOwnerOrSuperAdmin
from .services import KitchenSystemService, KitchenAssignmentService, KitchenNotificationService
from django.db.models import Avg, Count, Sum, Q
from datetime import timedelta
from django.core.exceptions import ValidationError

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

    @action(detail=True, methods=['get'])
    def workload(self, request, pk=None):
        """Get current workload for a specific station"""
        station = self.get_object()
        
        pending_count = KitchenOrderItem.objects.filter(
            station=station,
            status='pending'
        ).count()
        
        preparing_count = KitchenOrderItem.objects.filter(
            station=station,
            status='preparing'
        ).count()
        
        staff_count = KitchenStaff.objects.filter(station=station).count()
        available_staff = KitchenStaff.objects.filter(
            station=station,
            is_available=True
        ).count()
        
        workload_data = {
            'station_name': station.name,
            'pending': pending_count,
            'preparing': preparing_count,
            'total': pending_count + preparing_count,
            'staff_count': staff_count,
            'available_staff': available_staff
        }
        
        serializer = KitchenWorkloadSerializer(workload_data)
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

    def perform_create(self, serializer):
        """Create kitchen order when a regular order is created"""
        order = serializer.save()
        
        # Auto-assign items to stations if enabled
        branch = order.order.branch
        if branch.kitchen_enabled and branch.kitchen_settings.get('auto_assign_stations', False):
            KitchenAssignmentService.auto_assign_orders(branch)

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
            
            # Calculate preparation time
            if order.started_at:
                order.preparation_time = order.completed_at - order.started_at
            
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

    @action(detail=True, methods=['post'])
    def set_priority(self, request, pk=None):
        """Set priority for a kitchen order"""
        order = self.get_object()
        priority = request.data.get('priority', 0)
        
        try:
            priority = int(priority)
            if priority < 0 or priority > 10:
                raise ValueError("Priority must be between 0 and 10")
        except (ValueError, TypeError):
            return Response(
                {"error": "Priority must be a number between 0 and 10"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.priority = priority
        order.save()
        
        return Response({"message": f"Priority set to {priority}"})

    @action(detail=True, methods=['post'])
    def set_estimated_time(self, request, pk=None):
        """Set estimated completion time for a kitchen order"""
        order = self.get_object()
        estimated_minutes = request.data.get('estimated_minutes')
        
        try:
            estimated_minutes = int(estimated_minutes)
            if estimated_minutes <= 0:
                raise ValueError("Estimated time must be positive")
        except (ValueError, TypeError):
            return Response(
                {"error": "Estimated time must be a positive number"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.estimated_completion_time = timezone.now() + timedelta(minutes=estimated_minutes)
        order.save()
        
        return Response({"message": f"Estimated completion time set to {estimated_minutes} minutes"})

    def _update_analytics(self, order):
        """Update analytics for completed order"""
        for item in order.items.all():
            if item.station:
                analytics, _ = KitchenAnalytics.objects.get_or_create(
                    station=item.station,
                    date=timezone.now().date()
                )
                
                if item.started_at and item.completed_at:
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

    @action(detail=True, methods=['post'])
    def reassign(self, request, pk=None):
        """Reassign an item to a different station"""
        item = self.get_object()
        new_station_id = request.data.get('station_id')
        
        if not new_station_id:
            return Response(
                {"error": "Station ID is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success, message = KitchenAssignmentService.reassign_order(item, new_station_id)
        
        if success:
            return Response({"message": message})
        else:
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)

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

    @action(detail=True, methods=['get'])
    def real_time_data(self, request, pk=None):
        """Get real-time data for kitchen display"""
        display = self.get_object()
        stations = display.stations.all()
        
        # Get active orders
        active_orders = KitchenOrder.objects.filter(
            items__station__in=stations,
            status__in=['pending', 'preparing']
        ).distinct()
        
        # Get station workload
        workload = {}
        for station in stations:
            pending_count = KitchenOrderItem.objects.filter(
                station=station,
                status='pending'
            ).count()
            
            preparing_count = KitchenOrderItem.objects.filter(
                station=station,
                status='preparing'
            ).count()
            
            workload[station.name] = {
                'pending': pending_count,
                'preparing': preparing_count,
                'total': pending_count + preparing_count
            }
        
        return Response({
            'active_orders': KitchenOrderSerializer(active_orders, many=True).data,
            'workload': workload,
            'last_updated': timezone.now().isoformat()
        })

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

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get kitchen system status for a branch"""
        try:
            from restaurants.models import Branch
            branch = Branch.objects.get(id=pk)
            
            return Response({
                'kitchen_enabled': branch.kitchen_enabled,
                'kitchen_settings': branch.kitchen_settings or {},
                'stations_count': branch.kitchen_stations.filter(is_active=True).count(),
                'staff_count': KitchenStaff.objects.filter(station__branch=branch).count(),
                'active_orders': KitchenOrder.objects.filter(
                    order__branch=branch,
                    status__in=['pending', 'preparing']
                ).count()
            })
        except Branch.DoesNotExist:
            return Response({"error": "Branch not found"}, status=status.HTTP_404_NOT_FOUND)

class KitchenAnalyticsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission('kitchen_display')]
    
    @action(detail=True, methods=['get'])
    def station_performance(self, request, pk=None):
        station = KitchenStation.objects.get(pk=pk)
        analytics = KitchenAnalytics.objects.filter(station=station)
        serializer = KitchenAnalyticsSerializer(analytics, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def staff_performance(self, request, pk=None):
        staff = KitchenStaff.objects.get(pk=pk)
        completed_orders = KitchenOrderItem.objects.filter(
            prepared_by=staff.user,
            status='completed'
        )
        
        if completed_orders.exists():
            avg_time = completed_orders.aggregate(
                avg_time=Avg('completed_at' - 'started_at')
            )['avg_time']
        else:
            avg_time = None
        
        return Response({
            'total_orders': completed_orders.count(),
            'average_time': avg_time,
            'current_order': staff.current_order.id if staff.current_order else None
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
        
        serializer = KitchenPerformanceSerializer(analytics)
        return Response(serializer.data)

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

    @action(detail=False, methods=['get'])
    def workload(self, request):
        """Get current workload for all stations"""
        branch = request.user.branch
        workload = KitchenAssignmentService.get_station_workload(branch)
        
        # Add staff information to workload
        for station_name, data in workload.items():
            station = KitchenStation.objects.get(name=station_name, branch=branch)
            staff_count = KitchenStaff.objects.filter(station=station).count()
            available_staff = KitchenStaff.objects.filter(
                station=station,
                is_available=True
            ).count()
            
            data['staff_count'] = staff_count
            data['available_staff'] = available_staff
        
        serializer = KitchenWorkloadSerializer(workload.values(), many=True)
        return Response(serializer.data)

class KitchenNotificationViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = KitchenNotificationSerializer

    @action(detail=False, methods=['get'])
    def list(self, request):
        branch = request.user.branch
        notifications = KitchenNotificationService.get_notifications(branch)
        return Response(notifications)

    @action(detail=False, methods=['post'])
    def read(self, request):
        notification_id = request.data.get('notification_id')
        success = KitchenNotificationService.mark_as_read(notification_id)
        
        if success:
            return Response({"message": "Notification marked as read"})
        else:
            return Response({"error": "Failed to mark notification as read"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def clear(self, request):
        branch = request.user.branch
        success = KitchenNotificationService.clear_notifications(branch)
        
        if success:
            return Response({"message": "All notifications cleared"})
        else:
            return Response({"error": "Failed to clear notifications"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications"""
        branch = request.user.branch
        
        try:
            count = KitchenNotification.objects.filter(
                branch=branch,
                is_read=False
            ).count()
            
            return Response({"unread_count": count})
        except Exception:
            return Response({"unread_count": 0})

class KitchenStaffViewSet(viewsets.ModelViewSet):
    queryset = KitchenStaff.objects.all()
    serializer_class = KitchenStaffSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'branch'):
            return KitchenStaff.objects.filter(station__branch=user.branch)
        return KitchenStaff.objects.none()

    def perform_create(self, serializer):
        """Create kitchen staff and validate user belongs to branch"""
        user = self.request.user
        station = serializer.validated_data.get('station')
        
        if station.branch != user.branch:
            raise ValidationError("Staff can only be assigned to stations in their branch")
        
        serializer.save()

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
        
        if completed_items.exists():
            avg_time = completed_items.aggregate(
                avg_time=Avg('completed_at' - 'started_at')
            )['avg_time']
        else:
            avg_time = None
        
        return Response({
            'total_orders': total_orders,
            'average_preparation_time': avg_time,
            'current_order': staff.current_order.id if staff.current_order else None
        })

    @action(detail=True, methods=['post'])
    def toggle_availability(self, request, pk=None):
        """Toggle staff availability status"""
        staff = self.get_object()
        
        with transaction.atomic():
            staff.is_available = not staff.is_available
            if not staff.is_available:
                staff.current_order = None
            staff.save()
        
        status_text = "available" if staff.is_available else "unavailable"
        return Response({"message": f"Staff is now {status_text}"})

    @action(detail=True, methods=['post'])
    def complete_current_order(self, request, pk=None):
        """Mark current order as completed and free up staff"""
        staff = self.get_object()
        
        if not staff.current_order:
            return Response(
                {"error": "No current order to complete"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            staff.current_order = None
            staff.is_available = True
            staff.save()
        
        return Response({"message": "Current order completed, staff is now available"})
