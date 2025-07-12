from django.db import models
from django.db.models import Sum
from django.utils.timezone import now
from core.models import TimestampedModel
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone


class Supplier(TimestampedModel):
    supplier_id = models.AutoField(primary_key=True)
    branch=models.ForeignKey("restaurants.Branch", on_delete=models.CASCADE,related_name="supplier")
    supplier_name = models.CharField(max_length=255, unique=True)
    contact_details = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.supplier_name
    
    class Meta:
        db_table = 'suppliers'

class InventoryCategory(TimestampedModel):
    inventory_category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=255, unique=True)
    branch=models.ForeignKey("restaurants.Branch", on_delete=models.CASCADE,related_name="inventory_categories")
    image =  models.ImageField(upload_to='inventory_categories/',null=True,blank=True)
    class Meta:
        db_table = 'inventory_categories'
        verbose_name = 'Inventory Category'
        verbose_name_plural = 'Inventory Categories'

    def __str__(self):
        return self.category_name

class Inventory(TimestampedModel):
    UNIT_CHOICES = [
        ('g', 'Grams'),
        ('kg', 'Kilograms'),
        ('ml', 'Milliliters'),
        ('l', 'Liters'),
        ('pcs', 'Pieces'),
    ]
    inventory_id = models.AutoField(primary_key=True)
    branch = models.ForeignKey('restaurants.Branch', on_delete=models.CASCADE, related_name='inventory')
    category = models.ForeignKey('InventoryCategory', on_delete=models.CASCADE, related_name='inventory')
    supplier = models.ForeignKey('Supplier', on_delete=models.CASCADE, related_name='inventory')
    ingredient_name = models.CharField(max_length=255)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='g')
    cost = models.DecimalField(max_digits=10, decimal_places=2,default=0.00)
    price = models.DecimalField(max_digits=10, decimal_places=2,default=0.00)
    available_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    low_stock_alert = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    batch_number = models.CharField(max_length=255, blank=True, null=True)
    expiry_date = models.DateTimeField(blank=True, null=True)
    image =  models.ImageField(upload_to='inventory_items/',null=True,blank=True)
    class Meta:
        db_table = 'inventory'
        verbose_name = 'Inventory Item'
        verbose_name_plural = 'Inventory Items'
        indexes = [
            models.Index(fields=['branch_id'], name='idx_inventory_branch')
        ]

    def __str__(self):
        return f"{self.ingredient_name} - {self.available_quantity} {self.unit}"

    def is_expired(self):
        """Check if the inventory item is expired."""
        return self.expiry_date and self.expiry_date < now()

    def is_low_stock(self):
        """Check if the inventory item is below the low stock alert level."""
        return self.available_quantity <= self.low_stock_alert

    def days_to_expiry(self):
        """Returns the number of days left until expiry."""
        if not self.expiry_date:
            return None
        return (self.expiry_date - timezone.now().date()).days
    
    def reduce_stock(self, quantity, user, reason="Manual stock reduction"):
        """
        Reduce stock by a given quantity.
        Prevents negative stock and raises an error if stock is insufficient.
        """
        # Ensure the inventory belongs to the user's branch
        if self.branch != user.branch:
            raise PermissionError("You do not have permission to modify this inventory.")
        
        quantity = Decimal(quantity)
        if quantity > self.available_quantity:
            raise ValueError(f"Not enough stock available for {self.ingredient_name}.")
        

        self.available_quantity -= quantity
        self.save()
        
        # Log the transaction in InventoryTransaction
        InventoryTransaction.objects.create(
            inventory=self,
            transaction_type='adjustment',
            quantity_change=-quantity,
            reference_id=None  # You can link it to a StockAdjustment if necessary
        )

        # Log the adjustment in StockAdjustment
        StockAdjustment.objects.create(
            inventory=self,
            adjustment_type='decrease',
            quantity_adjusted=quantity,
            adjusted_by=user,
            reason=reason
        )

    def restock(self, quantity,user, reason="Manual restock"):
        """Increase stock by a given quantity."""
        if self.branch != user.branch:
            raise PermissionError("You do not have permission to restock this inventory.")

        quantity = Decimal(quantity)
        self.available_quantity += quantity
        self.save()
        # Log the transaction
        InventoryTransaction.objects.create(
            inventory=self,
            transaction_type='adjustment',
            quantity_change=quantity,
            reference_id=None
        )

        # Log the stock adjustment
        StockAdjustment.objects.create(
            inventory=self,
            adjustment_type='increase',
            quantity_adjusted=quantity,
            adjusted_by=user,
            reason=reason
        )

class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    purchase_order_id = models.AutoField(primary_key=True)
    supplier = models.ForeignKey('Supplier', on_delete=models.CASCADE, related_name='purchase_orders')
    branch = models.ForeignKey('restaurants.Branch', on_delete=models.CASCADE, related_name='purchase_orders')
    total_cost = models.DecimalField(max_digits=12, decimal_places=2,default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    purchased_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)  
    order_date = models.DateTimeField(default=now)
    received_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'purchase_orders'

    def __str__(self):
        return f"PO-{self.purchase_order_id} ({self.get_status_display()})"

    def mark_as_received(self):
        """Mark the purchase order as completed and update inventory."""
        if self.status != 'completed':  # Prevent duplicate updates
            self.status = 'completed'
            self.received_date = now()
            self.save()

            # Loop through each item in the order and update inventory
            for item in self.items.all():
                item.inventory.available_quantity += item.quantity
                item.inventory.save()

                # Log the transaction
                InventoryTransaction.objects.create(
                    inventory=item.inventory,
                    transaction_type='purchase',
                    quantity_change=item.quantity,
                    reference_id=item.purchase_order_item_id
                )


    def cancel_order(self):
        """Cancel the purchase order."""
        self.status = 'cancelled'
        self.save()
        
    def update_total_cost(self):
        """Recalculate the total cost based on all items."""
        self.total_cost = self.items.aggregate(total=Sum('total_price'))['total'] or 0
        self.save()


class PurchaseOrderItem(models.Model):
    purchase_order_item_id = models.AutoField(primary_key=True)
    purchase_order = models.ForeignKey('PurchaseOrder', on_delete=models.CASCADE, related_name='items')
    inventory = models.ForeignKey('Inventory', on_delete=models.CASCADE, related_name='purchase_items')
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2,default=0.00)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, editable=False)  # Auto-calculated field


    class Meta:
        db_table = 'purchase_order_items'

    def __str__(self):
        return f"Item-{self.purchase_order_item_id} for PO-{self.purchase_order.purchase_order_id}"

    def save(self, *args, **kwargs):
        """Automatically calculate total price before saving and update order total cost."""
        self.total_price = self.quantity * self.unit_price 
        super().save(*args, **kwargs)  

        self.purchase_order.update_total_cost()
        

class InventoryTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
        ('adjustment', 'Adjustment'),
        ('wastage', 'Wastage'),
    ]

    transaction_id = models.AutoField(primary_key=True)
    inventory = models.ForeignKey('Inventory', on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity_change = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_date = models.DateTimeField(default=now)
    reference_id = models.IntegerField(blank=True, null=True)  # Links to purchase_order_items, sales, or adjustments
    # Generic relation to reference any model (e.g., PurchaseOrderItem, SaleItem, etc.)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    reference_object = GenericForeignKey('content_type', 'object_id')


    class Meta:
        db_table = 'inventory_transactions'

    def __str__(self):
        return f"{self.transaction_type.capitalize()} - {self.quantity_change} units"

    def apply_transaction(self):
        """Applies the transaction to update inventory quantity."""
        if self.transaction_type in ['sale', 'wastage', 'adjustment']:
            self.inventory.available_quantity -= self.quantity_change
        elif self.transaction_type == 'purchase':
            self.inventory.available_quantity += self.quantity_change
        self.inventory.save()


class StockAdjustment(models.Model):
    ADJUSTMENT_TYPES = [
        ('increase', 'Increase'),
        ('decrease', 'Decrease'),
    ]

    adjustment_id = models.AutoField(primary_key=True)
    inventory = models.ForeignKey('Inventory', on_delete=models.CASCADE, related_name='adjustments')
    adjustment_type = models.CharField(max_length=20, choices=ADJUSTMENT_TYPES)
    quantity_adjusted = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField(blank=True, null=True)
    adjusted_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    adjusted_at = models.DateTimeField(default=now)

    class Meta:
        db_table = 'stock_adjustments'

    def __str__(self):
        return f"{self.adjustment_type.capitalize()} - {self.quantity_adjusted} units"

    def apply_adjustment(self):
        """Adjusts inventory quantity based on the adjustment type."""
        if self.adjustment_type == 'increase':
            self.inventory.available_quantity += self.quantity_adjusted
        elif self.adjustment_type == 'decrease':
            self.inventory.available_quantity -= self.quantity_adjusted
        self.inventory.save()

        # Log the transaction in InventoryTransaction
        InventoryTransaction.objects.create(
            inventory=self.inventory,
            transaction_type='adjustment',
            quantity_change=self.quantity_adjusted if self.adjustment_type == 'increase' else -self.quantity_adjusted,
            reference_id=self.adjustment_id
        )

