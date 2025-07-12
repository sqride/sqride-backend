# apps/items/serializers.py
from rest_framework import serializers
from .models import Category, Modifier, Item, ItemIngredient

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class ModifierSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source='ingredient.name', read_only=True)
    
    class Meta:
        model = Modifier
        fields = '__all__'

class ItemIngredientSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source='ingredient.name', read_only=True)
    
    class Meta:
        model = ItemIngredient
        fields = '__all__'

class ItemSerializer(serializers.ModelSerializer):
    ingredients = ItemIngredientSerializer(source='item_ingredients', many=True, read_only=True)
    modifiers = ModifierSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Item
        fields = '__all__'