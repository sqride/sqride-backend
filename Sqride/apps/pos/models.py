from django.db import models
from restaurants.models import Branch, RestaurantTable
from orders.models import Order
from items.models import Item
from accounts.models import User


class POSSession(models.Model):
    """
    Tracks active POS sessions for staff members
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    total_sales = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_orders = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'pos_sessions'
        indexes = [
            models.Index(fields=['user', 'is_active'], name='idx_pos_sessions_user_active'),
            models.Index(fields=['branch'], name='idx_pos_sessions_branch'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'is_active'],
                condition=models.Q(is_active=True),
                name='unique_active_session_per_user'
            )
        ]

    def __str__(self):
        return f"POS Session - {self.user.username} - {self.branch.name}"
    
    def save(self, *args, **kwargs):
        # Check if user is a SuperAdmin
        if hasattr(self.user, 'user_type') and self.user.user_type == 'SUPER_ADMIN':
            # SuperAdmin can create sessions for any branch
            super().save(*args, **kwargs)
        else:
            # For other users, ensure they belong to the specified branch
            if self.user.branch != self.branch:
                raise ValueError("User must belong to the specified branch")
            super().save(*args, **kwargs)
        
class POSOrder(models.Model):
    """
    POS-specific order model that extends the basic Order
    """
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    pos_session = models.ForeignKey(POSSession, on_delete=models.CASCADE)
    table = models.ForeignKey(RestaurantTable, on_delete=models.SET_NULL, null=True, blank=True)
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('PAID', 'Paid'),
            ('PARTIALLY_PAID', 'Partially Paid'),
            ('CANCELLED', 'Cancelled')
        ],
        default='PENDING'
    )
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('CASH', 'Cash'),
            ('CARD', 'Card'),
            ('SPLIT', 'Split Payment')
        ],
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pos_orders'
        indexes = [
            models.Index(fields=['pos_session'], name='idx_pos_orders_session'),
            models.Index(fields=['payment_status'], name='idx_pos_orders_payment_status'),
        ]

    def __str__(self):
        return f"POS Order {self.order.order_id} - {self.payment_status}"

class POSOrderItem(models.Model):
    """
    POS-specific order item model for tracking item modifications and special instructions
    """
    pos_order = models.ForeignKey(POSOrder, on_delete=models.CASCADE, related_name='pos_items')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True, null=True)
    is_void = models.BooleanField(default=False)
    void_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pos_order_items'
        indexes = [
            models.Index(fields=['pos_order'], name='idx_pos_order_items_order'),
            models.Index(fields=['is_void'], name='idx_pos_order_items_void'),
        ]

    def __str__(self):
        return f"{self.item.name} x {self.quantity} - {self.pos_order.order.order_id}"
