from django.db import models
from django.contrib.auth.models import BaseUserManager
from core.models import TimestampedModel

class CustomerManager(BaseUserManager):
    def get_queryset(self):
        # Exclude soft-deleted customers by default
        return super().get_queryset().filter(deleted_at__isnull=True)

    def create_customer(self, branch_id, name, phone, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError("Customers must have an email address")
        if not username:
            raise ValueError("Customers must have a username")

        email = self.normalize_email(email)
        customer = self.model(
            branch_id=branch_id,
            name=name,
            phone=phone,
            email=email,
            username=username,
            **extra_fields
        )
        customer.set_password(password)  # Hash the password
        customer.save(using=self._db)
        return customer

    def walk_in_customers(self):
        # Filter customers by type 'walk-in'
        return self.get_queryset().filter(type='walk-in')

    def dining_customers(self):
        # Filter customers by type 'dining'
        return self.get_queryset().filter(type='dining')

    def delivery_customers(self):
        # Filter customers by type 'delivery'
        return self.get_queryset().filter(type='delivery')

    def with_deleted(self):
        # Include soft-deleted customers
        return super().get_queryset()

    def deleted_customers(self):
        # Retrieve only soft-deleted customers
        return super().get_queryset().filter(deleted_at__isnull=False)

class Customer(TimestampedModel):
    CUSTOMER_TYPES = [
        ('walk-in', 'Walk-in'),
        ('dining', 'Dining'),
        ('delivery', 'Delivery'),
    ]

    customer_id = models.AutoField(primary_key=True)
    branch = models.ForeignKey('restaurants.Branch', on_delete=models.CASCADE)
    name = models.CharField(max_length=255, default='Walk-in Customer')
    phone = models.CharField(max_length=15, default='N/A')
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=128)  # Store hashed passwords
    type = models.CharField(max_length=10, choices=CUSTOMER_TYPES, default='walk-in')

    # Custom manager
    objects = CustomerManager()

    class Meta:
        db_table = 'customers'
        indexes = [
            models.Index(fields=['branch_id'], name='idx_customers_branch_id'),
        ]

    def __str__(self):
        return self.name


class LoyaltyProgram(TimestampedModel):
    loyalty_program_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="loyalty_programs",
        db_index=True
    )
    points_earned = models.PositiveIntegerField(default=0)
    points_redeemed = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = "loyalty_programs"
        indexes = [
            models.Index(fields=["customer"], name="idx_loyalty_cust"),
        ]
        verbose_name = "Loyalty Program"
        verbose_name_plural = "Loyalty Programs"

    def __str__(self):
        return f"{self.customer.name} - Points: {self.points_earned}"
