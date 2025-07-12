from django.db import transaction
from restaurants.models import Branch
from .models import KitchenStation, KitchenDisplay, KitchenStaff
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

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
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"kitchen_{branch_id}",
            {
                "type": "kitchen.update",
                "message": {
                    "order_id": order_id,
                    "status": status
                }
            }
        )

class KitchenAssignmentService:
    @staticmethod
    def assign_order_to_station(kitchen_order_item):
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
