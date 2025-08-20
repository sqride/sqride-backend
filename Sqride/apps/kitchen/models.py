from django.db import models
from core.models import TimestampedModel
from orders.models import Order, OrderItem
from restaurants.models import Branch
from accounts.models import User
from datetime import datetime, timedelta

class KitchenStation(TimestampedModel):
    """Represents different cooking stations in the kitchen (e.g., Grill, Fryer, Salad)"""
    name = models.CharField(max_length=100)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='kitchen_stations')
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    
    class Meta:
        unique_together = ('name', 'branch')
    
    def __str__(self):
        return f"{self.name} - {self.branch.name}"

class KitchenOrder(TimestampedModel):
    """Represents an order in the kitchen system"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='kitchen_orders')
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('preparing', 'Preparing'),
            ('ready', 'Ready'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled')
        ],
        default='pending'
    )
    priority = models.IntegerField(default=0)  # Higher number = higher priority
    notes = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    estimated_completion_time = models.DateTimeField(null=True, blank=True)
    sla_breach_time = models.DateTimeField(null=True, blank=True)
    preparation_time = models.DurationField(null=True, blank=True)
    
    def __str__(self):
        return f"Kitchen Order #{self.id} - {self.order.order_id}"

    def calculate_sla_breach(self):
        if self.estimated_completion_time:
            return self.estimated_completion_time + timedelta(minutes=15)  # 15 min buffer
        return None

class KitchenOrderItem(TimestampedModel):
    """Represents individual items in a kitchen order"""
    kitchen_order = models.ForeignKey(KitchenOrder, on_delete=models.CASCADE, related_name='items')
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='kitchen_items')
    station = models.ForeignKey(KitchenStation, on_delete=models.SET_NULL, null=True, related_name='order_items')
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('preparing', 'Preparing'),
            ('ready', 'Ready'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled')
        ],
        default='pending'
    )
    prepared_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='prepared_items')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.order_item.item.name} - {self.status}"

class KitchenDisplay(TimestampedModel):
    """Represents a kitchen display screen configuration"""
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='kitchen_displays')
    name = models.CharField(max_length=100)
    stations = models.ManyToManyField(KitchenStation, related_name='displays')
    is_active = models.BooleanField(default=True)
    display_type = models.CharField(
        max_length=20,
        choices=[
            ('order', 'Order Display'),
            ('preparation', 'Preparation Display'),
            ('combined', 'Combined Display')
        ],
        default='combined'
    )
    
    def __str__(self):
        return f"{self.name} - {self.branch.name}"

class KitchenStaff(TimestampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    station = models.ForeignKey(KitchenStation, on_delete=models.CASCADE)
    is_available = models.BooleanField(default=True)
    current_order = models.ForeignKey(KitchenOrder, null=True, blank=True, on_delete=models.SET_NULL)
    
    class Meta:
        unique_together = ('user', 'station')

class KitchenAnalytics(TimestampedModel):
    station = models.ForeignKey(KitchenStation, on_delete=models.CASCADE)
    date = models.DateField()
    total_orders = models.IntegerField(default=0)
    average_preparation_time = models.DurationField(null=True)
    peak_hours = models.JSONField(default=dict)
    sla_breaches = models.IntegerField(default=0)

class KitchenNotification(TimestampedModel):
    """Model for storing kitchen notifications when WebSocket fails"""
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='kitchen_notifications')
    order_id = models.IntegerField()
    status = models.CharField(max_length=50)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    notification_type = models.CharField(
        max_length=20,
        choices=[
            ('order_update', 'Order Update'),
            ('delay_alert', 'Delay Alert'),
            ('staff_assignment', 'Staff Assignment'),
            ('system_alert', 'System Alert')
        ],
        default='order_update'
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['branch', 'is_read']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Kitchen Notification - {self.branch.name} - {self.message[:50]}"
