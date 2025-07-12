from django.db import models
from core.models import TimestampedModel
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError
from inventory.models import InventoryTransaction
from restaurants.models import RestaurantTable

class OrderStatus(models.TextChoices):
    PENDING = 'pending', _('Pending')
    PREPARING = 'preparing', _('Preparing')
    COMPLETED = 'completed', _('Completed')
    CANCELLED = 'cancelled', _('Cancelled')

class OrderStatusHistory(models.Model):
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='status_history')
    from_status = models.CharField(max_length=10, choices=OrderStatus.choices)
    to_status = models.CharField(max_length=10, choices=OrderStatus.choices)
    changed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-changed_at']
        verbose_name_plural = 'Order Status Histories'

    def __str__(self):
        return f"Order {self.order.order_id}: {self.from_status} → {self.to_status}"

class OrderManager(models.Manager):
    def pending_orders(self):
        return self.filter(status=OrderStatus.PENDING)

    def completed_orders(self):
        return self.filter(status=OrderStatus.COMPLETED)

class Order(TimestampedModel):
    class OrderType(models.TextChoices):
        DINING = 'dining', _('Dining')
        TAKEAWAY = 'takeaway', _('Takeaway')
        DELIVERY = 'delivery', _('Delivery')

    # Status transition rules
    STATUS_TRANSITIONS = {
        OrderStatus.PENDING: [OrderStatus.PREPARING, OrderStatus.CANCELLED],
        OrderStatus.PREPARING: [OrderStatus.COMPLETED, OrderStatus.CANCELLED],
        OrderStatus.COMPLETED: [],
        OrderStatus.CANCELLED: []
    }

    order_id = models.AutoField(primary_key=True)
    branch = models.ForeignKey('restaurants.Branch', on_delete=models.CASCADE, related_name="orders")
    customer = models.ForeignKey('customers.Customer', on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    order_type = models.CharField(max_length=10, choices=OrderType.choices, default=OrderType.DINING)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=3, default='PKR')
    status = models.CharField(max_length=10, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    status_changed_at = models.DateTimeField(auto_now_add=True)
    status_changed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='changed_orders')
    # In models.py, inside Order class
    paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    table = models.ForeignKey(RestaurantTable, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    objects = OrderManager()

    class Meta:
        indexes = [
            models.Index(fields=['branch'], name='idx_orders_branch_id'),
            models.Index(fields=['customer'], name='idx_orders_customer_id'),
            models.Index(fields=['currency'], name='idx_orders_currency_id'),
            models.Index(fields=['status'], name='idx_orders_status'),
            models.Index(fields=['status_changed_at'], name='idx_orders_status_changed_at'),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.order_id} - {self.get_status_display()}"

    def validate_status_transition(self, new_status, user=None):
        """Validate if the status transition is allowed"""
        if new_status not in self.STATUS_TRANSITIONS[self.status]:
            raise ValidationError(
                f"Cannot change status from {self.status} to {new_status}. "
                f"Allowed transitions: {', '.join(self.STATUS_TRANSITIONS[self.status])}"
            )

    def change_status(self, new_status, user=None, notes=None):
        """Change order status with validation and history tracking"""
        self.validate_status_transition(new_status, user)
        
        old_status = self.status
        self.status = new_status
        self.status_changed_at = timezone.now()
        self.status_changed_by = user
        self.save()

        # Create status history record
        OrderStatusHistory.objects.create(
            order=self,
            from_status=old_status,
            to_status=new_status,
            changed_by=user,
            notes=notes
        )

        return self
    
    def reserve_stock(self):
        """Reserve stock for all items in the order"""
        for order_item in self.items.all():
            # Check if item has ingredients
            if order_item.item.item_ingredients.exists():
                for item_ingredient in order_item.item.item_ingredients.all():
                    required_quantity = item_ingredient.quantity * order_item.quantity
                    ingredient = item_ingredient.ingredients
                    
                    # Check if ingredient exists in inventory
                    try:
                        from inventory.models import Inventory
                        inventory_item = Inventory.objects.get(
                            branch=self.branch,
                            ingredient_name__iexact=ingredient.name
                        )
                        
                        # Deduct from inventory
                        inventory_item.available_quantity -= required_quantity
                        inventory_item.save()
                        
                        # Log the transaction
                        InventoryTransaction.objects.create(
                            inventory=inventory_item,
                            transaction_type='sale',
                            quantity_change=-required_quantity,
                            reference_id=order_item.order_item_id
                        )
                    except:
                        # If ingredient not in inventory, skip
                        pass

    def release_stock(self):
        """Release reserved stock when order is cancelled"""
        for order_item in self.items.all():
            # Check if item has ingredients
            if order_item.item.item_ingredients.exists():
                for item_ingredient in order_item.item.item_ingredients.all():
                    required_quantity = item_ingredient.quantity * order_item.quantity
                    ingredient = item_ingredient.ingredient
                    
                    # Check if ingredient exists in inventory
                    try:
                        from inventory.models import Inventory
                        inventory_item = Inventory.objects.get(
                            branch=self.branch,
                            ingredient_name__iexact=ingredient.name
                        )
                        
                        # Add back to inventory
                        inventory_item.available_quantity += required_quantity
                        inventory_item.save()
                        
                        # Log the transaction
                        InventoryTransaction.objects.create(
                            inventory=inventory_item,
                            transaction_type='adjustment',
                            quantity_change=required_quantity,
                            reference_id=order_item.order_item_id
                        )
                    except:
                        # If ingredient not in inventory, skip
                        pass

class OrderItem(models.Model):
    order_item_id = models.AutoField(primary_key=True)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        db_index=True
    )
    item = models.ForeignKey('items.Item', on_delete=models.CASCADE, related_name="order_items")
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        db_table = "order_items"
        indexes = [
            models.Index(fields=["order"], name="idx_order_items_order_id"),
        ]

    def __str__(self):
        return f"{self.item} ({self.quantity})"

    def validate_stock(self):
        """Validate if there's enough stock for this order item"""
        # Check if item has ingredients
        if not self.item.item_ingredients.exists():
            return True  # Items without ingredients don't need stock validation
            
        for item_ingredient in self.item.item_ingredients.all():
            required_quantity = item_ingredient.quantity * self.quantity
            ingredient = item_ingredient.ingredients
            
            # Check if ingredient exists in inventory
            try:
                from inventory.models import Inventory
                inventory_item = Inventory.objects.get(
                    branch=self.order.branch,
                    ingredient_name__iexact=ingredient.name
                )
                
                if inventory_item.available_quantity < required_quantity:
                    raise ValidationError(
                        f"Not enough stock for {ingredient.name}. "
                        f"Required: {required_quantity} {item_ingredient.unit}, "
                        f"Available: {inventory_item.available_quantity} {inventory_item.unit}"
                    )
            except:
                # If ingredient not in inventory, skip validation
                pass
                
        return True

    def save(self, *args, **kwargs):
        if not self.pk:  # Only validate on creation
            self.validate_stock()
        super().save(*args, **kwargs)
