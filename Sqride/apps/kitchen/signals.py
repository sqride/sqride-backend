from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from orders.models import Order, OrderItem
from .models import KitchenOrder, KitchenOrderItem, KitchenStation
from .services import KitchenAssignmentService
from .utils import calculate_order_priority
from django.db import transaction
from django.utils import timezone

@receiver(post_save, sender=Order)
def create_kitchen_order(sender, instance, created, **kwargs):
    """
    Automatically create kitchen order when a regular order is created
    """
    if created and instance.branch.kitchen_enabled:
        with transaction.atomic():
            # Calculate priority for the kitchen order
            priority = calculate_order_priority(instance)
            
            # Create kitchen order
            kitchen_order = KitchenOrder.objects.create(
                order=instance,
                status='pending',
                priority=priority,
                notes=f"Auto-created from order {instance.order_id}"
            )
            
            # Create kitchen order items for each order item
            for order_item in instance.items.all():
                # Auto-assign to a station based on item category and station workload
                station = _assign_item_to_station(order_item, instance.branch)
                
                KitchenOrderItem.objects.create(
                    kitchen_order=kitchen_order,
                    order_item=order_item,
                    station=station,
                    status='pending'
                )
            
            # Auto-assign orders to stations if enabled
            if instance.branch.kitchen_settings.get('auto_assign_stations', False):
                KitchenAssignmentService.auto_assign_orders(instance.branch)

@receiver(post_save, sender=OrderItem)
def create_kitchen_order_item(sender, instance, created, **kwargs):
    """
    Create kitchen order item when a new order item is added to an existing order
    """
    if created and instance.order.branch.kitchen_enabled:
        try:
            # Check if kitchen order already exists
            kitchen_order, created_ko = KitchenOrder.objects.get_or_create(
                order=instance.order,
                defaults={
                    'status': 'pending',
                    'priority': calculate_order_priority(instance.order),
                    'notes': f"Auto-created from order {instance.order.order_id}"
                }
            )
            
            # Create kitchen order item
            station = _assign_item_to_station(instance, instance.order.branch)
            
            KitchenOrderItem.objects.create(
                kitchen_order=kitchen_order,
                order_item=instance,
                station=station,
                status='pending'
            )
            
            # Auto-assign if enabled
            if instance.order.branch.kitchen_settings.get('auto_assign_stations', False):
                KitchenAssignmentService.auto_assign_orders(instance.order.branch)
                
        except Exception:
            # Ignore errors during creation
            pass

@receiver(post_save, sender=Order)
def update_kitchen_order_status(sender, instance, **kwargs):
    """
    Update kitchen order status when regular order status changes
    """
    if not instance.branch.kitchen_enabled:
        return
    
    try:
        kitchen_order = KitchenOrder.objects.get(order=instance)
        
        # Map order status to kitchen order status
        status_mapping = {
            'pending': 'pending',
            'preparing': 'preparing',
            'completed': 'completed',
            'cancelled': 'cancelled'
        }
        
        new_status = status_mapping.get(instance.status)
        if new_status and new_status != kitchen_order.status:
            old_status = kitchen_order.status
            kitchen_order.status = new_status
            
            # Update timestamps
            if new_status == 'preparing' and old_status == 'pending':
                kitchen_order.started_at = timezone.now()
            elif new_status == 'completed' and old_status in ['pending', 'preparing']:
                kitchen_order.completed_at = timezone.now()
                if kitchen_order.started_at:
                    kitchen_order.preparation_time = kitchen_order.completed_at - kitchen_order.started_at
            
            kitchen_order.save()
            
            # Update kitchen order items status
            if new_status == 'completed':
                kitchen_order.items.update(
                    status='completed',
                    completed_at=timezone.now()
                )
            elif new_status == 'cancelled':
                kitchen_order.items.update(status='cancelled')
            elif new_status == 'preparing':
                # Mark items as preparing if they have stations assigned
                kitchen_order.items.filter(
                    station__isnull=False
                ).update(
                    status='preparing',
                    started_at=timezone.now()
                )
                
    except KitchenOrder.DoesNotExist:
        # Kitchen order doesn't exist, ignore
        pass

@receiver(post_save, sender=OrderItem)
def update_kitchen_order_item(sender, instance, created, **kwargs):
    """
    Update kitchen order items when order items are modified
    """
    if not created and instance.order.branch.kitchen_enabled:
        try:
            # Find the corresponding kitchen order item
            kitchen_order_item = KitchenOrderItem.objects.get(
                order_item=instance
            )
            
            # Update the kitchen order item if needed
            if kitchen_order_item.status == 'pending':
                # Reassign to appropriate station if item category changed
                new_station = _assign_item_to_station(instance, instance.order.branch)
                if new_station and new_station != kitchen_order_item.station:
                    kitchen_order_item.station = new_station
                    kitchen_order_item.save()
                    
        except KitchenOrderItem.DoesNotExist:
            # Kitchen order item doesn't exist, ignore
            pass

@receiver(post_delete, sender=OrderItem)
def remove_kitchen_order_item(sender, instance, **kwargs):
    """
    Remove kitchen order items when order items are deleted
    """
    if instance.order.branch.kitchen_enabled:
        try:
            # Find and delete the corresponding kitchen order item
            KitchenOrderItem.objects.filter(
                order_item=instance
            ).delete()
            
            # Check if kitchen order has no more items
            kitchen_order = KitchenOrder.objects.filter(
                order=instance.order
            ).first()
            
            if kitchen_order and not kitchen_order.items.exists():
                kitchen_order.delete()
                
        except Exception:
            # Ignore errors during cleanup
            pass

@receiver(post_delete, sender=Order)
def remove_kitchen_order(sender, instance, **kwargs):
    """
    Remove kitchen order when regular order is deleted
    """
    if instance.branch.kitchen_enabled:
        try:
            # Delete the kitchen order and all its items
            KitchenOrder.objects.filter(order=instance).delete()
        except Exception:
            # Ignore errors during cleanup
            pass

def _assign_item_to_station(order_item, branch):
    """
    Intelligently assign an order item to a kitchen station based on:
    1. Item category
    2. Station workload
    3. Station specialization
    """
    try:
        # Get available stations for this branch
        available_stations = KitchenStation.objects.filter(
            branch=branch,
            is_active=True
        )
        
        if not available_stations.exists():
            return None
        
        # Try to find a station based on item category
        if order_item.item.category:
            category_name = order_item.item.category.name.lower()
            
            # Map categories to preferred stations
            category_station_mapping = {
                'dessert': ['dessert', 'bakery', 'pastry'],
                'salad': ['salad', 'cold kitchen', 'prep'],
                'grill': ['grill', 'bbq', 'hot kitchen'],
                'pizza': ['pizza', 'oven', 'hot kitchen'],
                'sushi': ['sushi', 'cold kitchen', 'prep'],
                'drinks': ['bar', 'beverage', 'drinks'],
                'appetizer': ['appetizer', 'prep', 'cold kitchen'],
                'main course': ['main kitchen', 'hot kitchen', 'grill'],
                'side dish': ['prep', 'cold kitchen', 'main kitchen']
            }
            
            # Find preferred stations for this category
            preferred_stations = []
            for category_key, station_names in category_station_mapping.items():
                if category_key in category_name:
                    preferred_stations = station_names
                    break
            
            # Try to assign to preferred stations first
            if preferred_stations:
                for station_name in preferred_stations:
                    station = available_stations.filter(
                        name__icontains=station_name
                    ).first()
                    if station:
                        return station
        
        # If no category-based assignment, use workload-based assignment
        return _assign_by_workload(available_stations)
        
    except Exception:
        # Fallback: return first available station
        return available_stations.first() if available_stations.exists() else None

def _assign_by_workload(stations):
    """
    Assign to station with lowest workload
    """
    try:
        from .services import KitchenAssignmentService
        
        # Get workload for all stations
        workload_data = {}
        for station in stations:
            pending_count = KitchenOrderItem.objects.filter(
                station=station,
                status='pending'
            ).count()
            
            preparing_count = KitchenOrderItem.objects.filter(
                station=station,
                status='preparing'
            ).count()
            
            workload_data[station] = pending_count + preparing_count
        
        # Find station with lowest workload
        if workload_data:
            min_workload_station = min(workload_data.items(), key=lambda x: x[1])[0]
            return min_workload_station
        
        # If no workload data, return first station
        return stations.first()
        
    except Exception:
        # Fallback: return first station
        return stations.first() if stations.exists() else None
