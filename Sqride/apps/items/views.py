# apps/items/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.db.models import Sum, F
from django.core.exceptions import ValidationError
from .models import Category, Modifier, Item, ItemIngredient
from .serializers import (
    CategorySerializer, ModifierSerializer, ItemSerializer, ItemIngredientSerializer
)
from accounts.permissions import HasRolePermission
from decimal import Decimal
from inventory.models import Inventory

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), HasRolePermission('categories')]
        return [IsAuthenticated(), HasRolePermission('categories')]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'branch') and user.branch.restaurant:
            return Category.objects.filter(restaurant=user.branch.restaurant)
        return Category.objects.none()
    
    def create(self, request, *args, **kwargs):
        user=request.user
        # Check if user has a branch and restaurant
        if not hasattr(user, 'branch') or not user.branch.restaurant:
            return Response(
                {"error": "User must be associated with a branch that has a restaurant"},
                status=status.HTTP_400_BAD_REQUEST
            )
        data=request.data
        data['restaurant']= user.branch.restaurant.id
        # Validate and save the category
        serializer = self.get_serializer(data=data)
        
        if serializer.is_valid(raise_exception=True):
        # Save with the restaurant from user's branch
            serializer.save()
            return Response(
                {"message": "Category created successfully", "data": serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response({"error":serializer.error},status=status.HTTP_400_BAD_REQUEST)


    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Check if category has any active items
        if instance.items.filter(is_active=True).exists():
            return Response(
                {"error": "Cannot delete category with active items"},
                status=status.HTTP_400_BAD_REQUEST
            )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        category = self.get_object()
        category.is_active = not category.is_active
        category.save()
        return Response({'status': 'success', 'is_active': category.is_active})




class ModifierViewSet(viewsets.ModelViewSet):
    queryset = Modifier.objects.all()
    serializer_class = ModifierSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), HasRolePermission('modifiers')]
        return [IsAuthenticated(), HasRolePermission('modifiers')]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'branch') and user.branch.restaurant:
            return Modifier.objects.filter(restaurant=user.branch.restaurant)
        return Modifier.objects.none()

    def create(self, request, *args, **kwargs):
        user=request.user
        if not hasattr(user, 'branch') or not user.branch.restaurant:
            return Response(
                {"error": "User must be associated with a branch that has a restaurant"},
                status=status.HTTP_400_BAD_REQUEST
            )
        data=request.data
        data['restaurant']= user.branch.restaurant.id
        # Validate and save the category
        serializer = self.get_serializer(data=data)
        
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(
                {"message": "Modifier created successfully", "data": serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response({"error":serializer.error},status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        # Check if modifier is used in any active items
        if instance.items.filter(is_active=True).exists():
            return Response(
                {"error": "Cannot update modifier used in active items"},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.items.exists():
            return Response(
                {"error": "Cannot delete modifier used in items"},
                status=status.HTTP_400_BAD_REQUEST
            )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        modifier = self.get_object()
        modifier.is_active = not modifier.is_active
        modifier.save()
        return Response({'status': 'success', 'is_active': modifier.is_active})


class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), HasRolePermission('items')]
        return [IsAuthenticated(), HasRolePermission('items')]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'branch'):
            return Item.objects.filter(branch=user.branch)
        return Item.objects.none()

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        user=request.user
        if not hasattr(user, 'branch'):
            raise ValidationError("User must be associated with a branch")
        data=request.data
        data["branch"]=user.branch.id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        
        # Create item
        item = serializer.save(branch=request.user.branch)
        
       # Handle item ingredients
        item_ingredients_data = data.get('item_ingredients', [])
        inventory_ids = [ing["ingredient"] for ing in item_ingredients_data]
        inventory_map = {
            inv.inventory_id: inv for inv in Inventory.objects.filter(inventory_id__in=inventory_ids)
        }

        item_ingredient_objects = []
        for ing in item_ingredients_data:
            inventory_instance = inventory_map.get(ing["ingredient"])
            if not inventory_instance:
                raise ValidationError(f"Invalid ingredient ID: {ing['ingredient']}")

            item_ingredient_objects.append(ItemIngredient(
                item=item,
                ingredients=inventory_instance,
                quantity=ing["quantity"],
                unit=ing["unit"]
            ))

        # Bulk create for performance
        ItemIngredient.objects.bulk_create(item_ingredient_objects)

        # Recalculate cost
        item.calculate_cost_and_price()

        return Response(self.get_serializer(item).data, status=status.HTTP_201_CREATED)
    
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        item = serializer.save()
        
        # Update item ingredients if provided
        if 'item_ingredients' in request.data:
            instance.item_ingredients.all().delete()

            ingredients_data = request.data['item_ingredients']
            inventory_ids = [ing["ingredient"] for ing in ingredients_data]

            # Fetch all inventory items in one query
            inventory_map = {
                inv.inventory_id: inv for inv in Inventory.objects.filter(inventory_id__in=inventory_ids)
            }

            invalid_ids = [ing["ingredient"] for ing in ingredients_data if ing["ingredient"] not in inventory_map]
            if invalid_ids:
                return Response(
                    {
                        "error": f"Invalid Ingredients IDs {invalid_ids}",
                    },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                    
            item_ingredient_objects = []
            for ing in ingredients_data:
                inventory_instance = inventory_map[ing["ingredient"]]
                item_ingredient_objects.append(ItemIngredient(
                    item=instance,
                    ingredients=inventory_instance,
                    quantity=ing["quantity"],
                    unit=ing["unit"]
                ))

            # Bulk create all ingredients
            ItemIngredient.objects.bulk_create(item_ingredient_objects)
            item.calculate_cost_and_price()
        return Response(self.get_serializer(item).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Check if item has any active orders
        if instance.orders.filter(status__in=['pending', 'preparing']).exists():
            return Response(
                {"error": "Cannot delete item with active orders"},
                status=status.HTTP_400_BAD_REQUEST
            )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        item = self.get_object()
        item.is_active = not item.is_active
        item.save()
        return Response({'status': 'success', 'is_active': item.is_active})

    @action(detail=True, methods=['get'])
    def ingredients(self, request, pk=None):
        item = self.get_object()
        ingredients = item.item_ingredients.all()
        serializer = ItemIngredientSerializer(ingredients, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def modifiers(self, request, pk=None):
        item = self.get_object()
        modifiers = item.modifiers.all()
        serializer = ModifierSerializer(modifiers, many=True)
        return Response(serializer.data)

class ItemIngredientViewSet(viewsets.ModelViewSet):
    queryset = ItemIngredient.objects.all()
    serializer_class = ItemIngredientSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'branch'):
            return ItemIngredient.objects.filter(item__branch=user.branch)
        return ItemIngredient.objects.none()