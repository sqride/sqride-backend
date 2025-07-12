from django.db import models
from core.models import TimestampedModel 
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

class Currency(TimestampedModel):
    currency_id = models.AutoField(primary_key=True)
    currency_code = models.CharField(max_length=10, unique=True)  # e.g., "USD", "EUR"
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=6)  # Stores exchange rate with precision

    class Meta:
        db_table = 'currencies'
    def __str__(self):
        return f"{self.currency_code} - {self.exchange_rate}"


class Restaurant(TimestampedModel):
    owner = models.ForeignKey("accounts.Owner", on_delete=models.CASCADE, related_name="restaurants")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    logo = models.ImageField(upload_to='restaurant_logos/', null=True, blank=True)
    website = models.URLField(validators=[URLValidator()], null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    tax_id = models.CharField(max_length=50, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    subscription_status = models.CharField(
        max_length=20,
        choices=[
            ('trial', 'Trial'),
            ('active', 'Active'),
            ('suspended', 'Suspended'),
            ('expired', 'Expired')
        ],
        default='trial'
    )
    subscription_end_date = models.DateField(null=True, blank=True)
    
    # Business hours
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    
    # Settings
    settings = models.JSONField(default=dict, blank=True)  # For storing restaurant-specific settings
    
    class Meta:
        db_table = "restaurants"
        indexes = [
            models.Index(fields=["owner"], name="idx_restaurants_owner_id"),
            models.Index(fields=["is_active"], name="idx_restaurants_is_active"),
            models.Index(fields=["subscription_status"], name="idx_rest_sub_status"),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        if self.opening_time and self.closing_time and self.opening_time >= self.closing_time:
            raise ValidationError("Closing time must be after opening time")

class Branch(TimestampedModel):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="branches")
    name = models.CharField(max_length=255)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField(null=True, blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name="branches")
    
    # Location
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Branch specific settings
    is_active = models.BooleanField(default=True)
    is_delivery_available = models.BooleanField(default=False)
    is_pickup_available = models.BooleanField(default=True)
    is_dine_in_available = models.BooleanField(default=True)
    
    # Operating hours
    operating_hours = models.JSONField(default=dict,null=True,blank=True)  # Store operating hours for each day
    
    # Branch specific settings
    settings = models.JSONField(default=dict,null=True,blank=True)  # For storing branch-specific settings
    
    # Kitchen system
    kitchen_enabled = models.BooleanField(default=False)
    kitchen_settings = models.JSONField(default=dict, blank=True)  # For storing kitchen-specific settings
    
    class Meta:
        db_table = "branches"
        indexes = [
            models.Index(fields=["restaurant"], name="idx_branches_restaurant_id"),
            models.Index(fields=["is_active"], name="idx_branches_is_active"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["restaurant", "name"], name="unique_branch_name_per_restaurant")
        ]

    def __str__(self):
        return f"{self.name} - {self.restaurant.name}"

# New models for restaurant management
class RestaurantCategory(TimestampedModel):
    restaurant = models.ForeignKey(
        Restaurant, 
        on_delete=models.CASCADE, 
        related_name="restaurant_categories"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='category_images/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    
    class Meta:
        db_table = "restaurant_categories"
        unique_together = ('restaurant', 'name')
        ordering = ['display_order', 'name']

    def __str__(self):
        return f"{self.name} - {self.restaurant.name}"

class RestaurantTable(TimestampedModel):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="tables")
    table_number = models.CharField(max_length=50)
    capacity = models.IntegerField()
    is_active = models.BooleanField(default=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('available', 'Available'),
            ('occupied', 'Occupied'),
            ('reserved', 'Reserved'),
            ('maintenance', 'Maintenance')
        ],
        default='available'
    )
    
    class Meta:
        db_table = "restaurant_tables"
        unique_together = ('branch', 'table_number')
        indexes = [
            models.Index(fields=["status"], name="idx_tables_status"),
        ]

    def __str__(self):
        return f"Table {self.table_number} - {self.branch.name}"

class RestaurantZone(TimestampedModel):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="zones")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = "restaurant_zones"
        unique_together = ('branch', 'name')

    def __str__(self):
        return f"{self.name} - {self.branch.name}"

class RestaurantHoliday(TimestampedModel):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="holidays")
    date = models.DateField()
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    is_recurring = models.BooleanField(default=False)
    
    class Meta:
        db_table = "restaurant_holidays"
        unique_together = ('restaurant', 'date')

    def __str__(self):
        return f"{self.name} - {self.date}"

