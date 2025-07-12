from django.db import models
from core.models import TimestampedModel
from restaurants.models import Restaurant, Branch
from inventory.models import Inventory

class Category(TimestampedModel):
    """Category model for menu items"""
    category_id = models.AutoField(primary_key=True)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to="category_images/", null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'categories'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        unique_together = ("restaurant", "name")  # Prevent duplicate category names per restaurant

    def __str__(self):
        return f"{self.name} ({self.restaurant.name})"

class Modifier(TimestampedModel):
    """Modifier model for items (e.g., extra cheese, no onions)"""
    modifier_id = models.AutoField(primary_key=True)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="modifiers")
    title = models.CharField(max_length=255)
    ingredient = models.ForeignKey(Inventory, on_delete=models.CASCADE, related_name="modifiers")
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'modifiers'
        unique_together = ("restaurant", "title")

    def __str__(self):
        return f"{self.title} - {self.ingredient.ingredient_name}"

class Item(TimestampedModel):
    """Item model for menu items"""
    item_id = models.AutoField(primary_key=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="items")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="item_images/", null=True, blank=True)
    ingredients = models.ManyToManyField(Inventory, through='ItemIngredient', related_name="items")
    modifiers = models.ManyToManyField(Modifier, related_name="items", blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'items'
        unique_together = ('branch', 'name')

    def __str__(self):
        return f"{self.name} - {self.branch.name}"

    def calculate_cost(self):
        """Calculate total cost based on ingredients"""
        total_cost = sum(
            item_ingredient.quantity * item_ingredient.ingredients.cost
            for item_ingredient in self.item_ingredients.all()
        )
        self.cost = total_cost
        self.save()
    
    def calculate_price(self):
        """Calculate total price based on ingredients"""
        total_price = sum(
            item_ingredient.quantity * item_ingredient.ingredients.price
            for item_ingredient in self.item_ingredients.all()
        )
        self.price = total_price
        self.save()
        
    def calculate_cost_and_price(self):
        """Calculate both cost and price"""
        self.calculate_cost()
        self.calculate_price()
        
class ItemIngredient(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="item_ingredients")
    ingredients = models.ForeignKey(Inventory, on_delete=models.CASCADE, related_name="used_in_recipes")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit = models.CharField(max_length=10, choices=Inventory.UNIT_CHOICES, default='g')

    class Meta:
        db_table = 'item_ingredients'
        unique_together = ('item', 'ingredients')

    def __str__(self):
        return f"{self.quantity} {self.unit} of {self.ingredients.ingredient_name} in {self.item.name}"