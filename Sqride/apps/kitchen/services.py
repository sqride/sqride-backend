from django.db import transaction
from restaurants.models import Branch
from .models import KitchenStation, KitchenDisplay, KitchenStaff
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from datetime import datetime

class KitchenSystemService:
    @staticmethod
    @transaction.atomic
    def enable_kitchen_system(branch_id):
        """
        Enable kitchen system for a branch and set up initial configuration
        """
        try:
            branch = Branch.objects.get(id=branch_id)
            
            # Enable kitchen system
            branch.kitchen_enabled = True
            
            # Set default kitchen settings
            branch.kitchen_settings = {
                'auto_assign_stations': True,
                'default_preparation_time': 15,  # minutes
                'notify_on_delay': True,
                'delay_threshold': 10,  # minutes
            }
            
            branch.save()
            
            # Create default kitchen stations
            default_stations = [
                {'name': 'Main Kitchen', 'description': 'Main cooking station'},
                {'name': 'Grill', 'description': 'Grill station'},
                {'name': 'Salad', 'description': 'Salad and cold items'},
                {'name': 'Dessert', 'description': 'Dessert station'}
            ]
            
            for station_data in default_stations:
                KitchenStation.objects.create(
                    branch=branch,
                    **station_data
                )
            
            # Create default kitchen display
            KitchenDisplay.objects.create(
                branch=branch,
                name='Main Kitchen Display',
                display_type='combined'
            )
            
            return True, "Kitchen system enabled successfully"
            
        except Branch.DoesNotExist:
            return False, "Branch not found"
        except Exception as e:
            return False, str(e)

    @staticmethod
    @transaction.atomic
    def disable_kitchen_system(branch_id):
        """
        Disable kitchen system for a branch
        """
        try:
            branch = Branch.objects.get(id=branch_id)
            
            # Check if there are any pending kitchen orders
            from .models import KitchenOrder
            pending_orders = KitchenOrder.objects.filter(
                order__branch=branch,
                status__in=['pending', 'preparing']
            ).exists()
            
            if pending_orders:
                return False, "Cannot disable kitchen system while there are pending orders"
            
            # Disable kitchen system
            branch.kitchen_enabled = False
            branch.kitchen_settings = {}
            branch.save()
            
            # Deactivate all kitchen stations
            KitchenStation.objects.filter(branch=branch).update(is_active=False)
            
            # Deactivate all kitchen displays
            KitchenDisplay.objects.filter(branch=branch).update(is_active=False)
            
            return True, "Kitchen system disabled successfully"
            
        except Branch.DoesNotExist:
            return False, "Branch not found"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def update_kitchen_settings(branch_id, settings):
        """
        Update kitchen settings for a branch
        """
        try:
            branch = Branch.objects.get(id=branch_id)
            
            if not branch.kitchen_enabled:
                return False, "Kitchen system is not enabled for this branch"
            
            # Update settings
            current_settings = branch.kitchen_settings or {}
            current_settings.update(settings)
            branch.kitchen_settings = current_settings
            branch.save()
            
            return True, "Kitchen settings updated successfully"
            
        except Branch.DoesNotExist:
            return False, "Branch not found"
        except Exception as e:
            return False, str(e)

class KitchenNotificationService:
    @staticmethod
    def notify_kitchen_update(branch_id, order_id, status):
        """
        Send real-time notification to kitchen staff
        """
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"kitchen_{branch_id}",
                {
                    "type": "kitchen.update",
                    "message": {
                        "order_id": order_id,
                        "status": status,
                        "timestamp": timezone.now().isoformat()
                    }
                }
            )
            return True
        except Exception as e:
            # Fallback to database notification if WebSocket fails
            return KitchenNotificationService.create_database_notification(branch_id, order_id, status)

    @staticmethod
    def create_database_notification(branch_id, order_id, status):
        """
        Create a database notification as fallback
        """
        try:
            from .models import KitchenNotification
            KitchenNotification.objects.create(
                branch_id=branch_id,
                order_id=order_id,
                status=status,
                message=f"Order {order_id} status changed to {status}",
                created_at=timezone.now()
            )
            return True
        except Exception:
            return False

    @staticmethod
    def get_notifications(branch, limit=50):
        """
        Get recent notifications for a branch
        """
        try:
            from .models import KitchenNotification
            notifications = KitchenNotification.objects.filter(
                branch=branch,
                is_read=False
            ).order_by('-created_at')[:limit]
            
            return [{
                'id': n.id,
                'order_id': n.order_id,
                'status': n.status,
                'message': n.message,
                'created_at': n.created_at,
                'is_read': n.is_read
            } for n in notifications]
        except Exception:
            return []

    @staticmethod
    def mark_as_read(notification_id):
        """
        Mark a notification as read
        """
        try:
            from .models import KitchenNotification
            notification = KitchenNotification.objects.get(id=notification_id)
            notification.is_read = True
            notification.save()
            return True
        except Exception:
            return False

    @staticmethod
    def clear_notifications(branch):
        """
        Clear all notifications for a branch
        """
        try:
            from .models import KitchenNotification
            KitchenNotification.objects.filter(branch=branch).update(is_read=True)
            return True
        except Exception:
            return False

    @staticmethod
    def notify_delay_alert(branch_id, order_id, delay_minutes):
        """
        Notify kitchen staff about order delays
        """
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"kitchen_{branch_id}",
                {
                    "type": "kitchen.delay_alert",
                    "message": {
                        "order_id": order_id,
                        "delay_minutes": delay_minutes,
                        "timestamp": timezone.now().isoformat(),
                        "alert_type": "delay"
                    }
                }
            )
            return True
        except Exception:
            return False

class KitchenAssignmentService:
    @staticmethod
    def assign_order_to_station(kitchen_order_item):
        """
        Automatically assign an order item to available staff at a station
        """
        available_staff = KitchenStaff.objects.filter(
            station=kitchen_order_item.station,
            is_available=True
        ).first()
        
        if available_staff:
            available_staff.current_order = kitchen_order_item.kitchen_order
            available_staff.is_available = False
            available_staff.save()
            return True
        return False

    @staticmethod
    def auto_assign_orders(branch):
        """
        Automatically assign pending orders to available staff
        """
        try:
            from .models import KitchenOrderItem
            
            # Get all pending items that need assignment
            pending_items = KitchenOrderItem.objects.filter(
                kitchen_order__order__branch=branch,
                status='pending',
                station__isnull=False
            ).select_related('station')
            
            assigned_count = 0
            
            for item in pending_items:
                if KitchenAssignmentService.assign_order_to_station(item):
                    assigned_count += 1
                    item.status = 'preparing'
                    item.started_at = timezone.now()
                    item.save()
            
            return assigned_count
        except Exception:
            return 0

    @staticmethod
    def reassign_order(kitchen_order_item, new_station_id):
        """
        Reassign an order item to a different station
        """
        try:
            new_station = KitchenStation.objects.get(id=new_station_id)
            
            # Check if new station is available
            if not new_station.is_active:
                return False, "Station is not active"
            
            # Update the item's station
            kitchen_order_item.station = new_station
            kitchen_order_item.save()
            
            # Try to auto-assign to available staff
            if KitchenAssignmentService.assign_order_to_station(kitchen_order_item):
                return True, "Order reassigned and staff assigned"
            else:
                return True, "Order reassigned but no staff available"
                
        except KitchenStation.DoesNotExist:
            return False, "Station not found"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_station_workload(branch):
        """
        Get current workload for all stations in a branch
        """
        try:
            from .models import KitchenOrderItem
            
            stations = KitchenStation.objects.filter(branch=branch, is_active=True)
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
            
            return workload
        except Exception:
            return {}

    @staticmethod
    def optimize_station_assignment(branch):
        """
        Optimize order assignment based on station workload
        """
        try:
            workload = KitchenAssignmentService.get_station_workload(branch)
            
            # Find stations with lowest workload
            sorted_stations = sorted(
                workload.items(),
                key=lambda x: x[1]['total']
            )
            
            if sorted_stations:
                return sorted_stations[0][0]  # Return station name with lowest workload
            return None
        except Exception:
            return None
