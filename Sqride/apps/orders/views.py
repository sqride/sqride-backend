from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from .models import Order, OrderItem,OrderStatus
from items.models import Item
from .serializers import OrderSerializer, OrderItemSerializer
from accounts.permissions import HasRolePermission
from django.core.exceptions import ValidationError
from customers.models import Customer
from django.utils import timezone
from restaurants.models import RestaurantTable

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """Override get_permissions to use different permissions for different actions"""
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), HasRolePermission("order")]
        return [IsAuthenticated(), HasRolePermission("order")]

    def get_queryset(self):
        """Filter orders based on the user's branch"""
        user = self.request.user
        if hasattr(user, "branch"):
            return Order.objects.filter(branch=user.branch)
        return Order.objects.none()

    def create(self, request, *args, **kwargs):
        """Create a new order with its items"""
        user = request.user
        branch=user.branch
        if not hasattr(user, "branch"):
            return Response(
                {"error": "User must be associated with a branch"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                # Get customer if provided
                customer_id = request.data.get("customer")
                customer = None
                if customer_id:
                    customer = Customer.objects.filter(customer_id=customer_id).first()
                    if not customer:
                        return Response(
                            {"error": f"Customer with ID {customer_id} does not exist"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                order_type = request.data.get("order_type")
                table_id=request.data.get("table")
                
                if branch.is_dine_in_available and order_type == "dining":
                    if not table_id:
                        return Response({
                            "error":"Table is required for dining order"
                            
                        },status=status.HTTP_400_BAD_REQUEST)
                    
                    try:
                        table=RestaurantTable.objects.get(pk=table_id,branch=branch)
                    except RestaurantTable.DoesNotExist:
                        return Response({
                            "error":"There is no such table for this branch"
                        },status=status.HTTP_400_BAD_REQUEST)
                else:
                    table=None
                # Create the order
                order = Order.objects.create(
                    branch=branch,
                    customer=customer,
                    order_type=order_type,
                    currency=branch.currency.currency_code if branch.currency else "PKR",
                    total_amount=0,
                    table=table
                )

                # Get item data from request
                items_data = request.data.get("items", [])
                if not items_data:
                    return Response(
                        {"error": "No items provided in the order."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                item_ids = [item["item"] for item in items_data]
                items = Item.objects.filter(item_id__in=item_ids)
                item_map = {item.item_id: item for item in items}

                order_items = []
                total_amount = 0

                for item_data in items_data:
                    item_id = item_data["item"]
                    quantity = item_data["quantity"]

                    item = item_map.get(item_id)
                    if not item:
                        return Response(
                            {"error": f"Item with ID {item_id} does not exist"},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    price = item.price
                    total_amount += price * quantity

                    order_items.append(OrderItem(
                        order=order,
                        item=item,
                        quantity=quantity,
                        price=price
                    ))

                # Bulk insert order items
                OrderItem.objects.bulk_create(order_items)

                # Update order total
                order.total_amount = total_amount
                order.save()

                # Return response
                serializer = self.get_serializer(order)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        """Update an existing order and its items"""
        instance = self.get_object()

        try:
            with transaction.atomic():
                # Update fields only if provided
                if "order_type" in request.data:
                    instance.order_type = request.data["order_type"]
                if "customer" in request.data:
                    instance.customer_id = request.data["customer"]
                if "table" in request.data:
                    instance.table_id = request.data["table"]

                instance.save()

                # Process order items if provided
                items_data = request.data.get("items", [])
                total_amount = 0

                if items_data:
                    instance.items.all().delete()

                    item_ids = [item["item"] for item in items_data]
                    items = Item.objects.filter(item_id__in=item_ids)
                    item_map = {item.item_id: item for item in items}

                    order_item_objects = []

                    for item_data in items_data:
                        item_id = item_data["item"]
                        quantity = item_data["quantity"]

                        item = item_map.get(item_id)
                        if not item:
                            return Response(
                                {"error": f"Item with ID {item_id} does not exist"},
                                status=status.HTTP_400_BAD_REQUEST
                            )

                        price = item.price
                        total_amount += price * quantity

                        order_item_objects.append(OrderItem(
                            order=instance,
                            item=item,
                            quantity=quantity,
                            price=price
                        ))

                    OrderItem.objects.bulk_create(order_item_objects)

                # Update total and save
                instance.total_amount = total_amount
                instance.save()

                serializer = self.get_serializer(instance)
                return Response(serializer.data)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


    def partial_update(self, request, *args, **kwargs):
        """Partially update an order"""
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Delete an order"""
        instance = self.get_object()
        
        # Check if order can be deleted
        if instance.status == Order.OrderStatus.COMPLETED:
            return Response(
                {"error": "Cannot delete a completed order"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                # Delete all order items first
                instance.items.all().delete()
                # Delete the order
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
    @action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        """Add an item to an existing order"""
        order = self.get_object()
        
        try:
            with transaction.atomic():
                item_id = request.data.get('item')
                quantity = request.data.get('quantity', 1)
                
                try:
                    item = Item.objects.get(item_id=item_id)
                except Item.DoesNotExist:
                    return Response(
                        {"error": f"Item with ID {item_id} does not exist"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                price = item.price
                
                # Create order item
                order_item = OrderItem.objects.create(
                    order=order,
                    item=item,
                    quantity=quantity,
                    price=price
                )
                
                # Update order total
                order.total_amount += (price * quantity)
                order.save()
                
                serializer = OrderItemSerializer(order_item)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )   

    @action(detail=True, methods=['put'])
    def update_item(self, request, pk=None):
        """Update a specific item in an order"""
        order = self.get_object()
        item_id = request.data.get('order_item_id')
        
        try:
            with transaction.atomic():
                order_item = OrderItem.objects.get(
                    order_item_id=item_id,
                    order=order
                )
                
                old_total = order_item.price * order_item.quantity
                
                # Update fields
                if 'quantity' in request.data:
                    order_item.quantity = request.data['quantity']
                if 'item' in request.data:
                    new_item = Item.objects.get(item_id=request.data['item'])
                    order_item.item = new_item
                    order_item.price = new_item.price
                
                order_item.save()
                new_total = order_item.price * order_item.quantity
                
                # Update order total
                order.total_amount = order.total_amount - old_total + new_total
                order.save()
                
                serializer = OrderItemSerializer(order_item)
                return Response(serializer.data)
                
        except OrderItem.DoesNotExist:
            return Response(
                {"error": "Order item not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Item.DoesNotExist:
            return Response(
                {"error": "Item not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['delete'])
    def remove_item(self, request, pk=None):
        """Remove a specific item from an order"""
        order = self.get_object()
        item_id = request.data.get('order_item_id')
        
        try:
            with transaction.atomic():
                order_item = OrderItem.objects.get(
                    order_item_id=item_id,
                    order=order
                )
                
                # Update order total
                order.total_amount -= (order_item.price * order_item.quantity)
                order.save()
                
                # Delete the item
                order_item.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
                
        except OrderItem.DoesNotExist:
            return Response(
                {"error": "Order item not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def items(self, request, pk=None):
        """Get all items for a specific order"""
        order = self.get_object()
        order_items = order.items.all()
        serializer = OrderItemSerializer(order_items, many=True)
        
        return Response({
            'order_id': order.order_id,
            'order_status': order.status,
            'total_amount': float(order.total_amount),
            'items': serializer.data,
            'items_count': len(serializer.data)
        })
        
    @action(detail=True, methods=['post'])
    def mark_as_completed(self, request, pk=None):
        """Mark an order as completed and handle inventory"""
        order = self.get_object()

        if order.status == OrderStatus.COMPLETED:
            return Response(
                {'detail': 'Order is already completed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                # Check inventory for all items
                for order_item in order.items.all():
                    item = order_item.item
                    
                    # Check if item has ingredients that need inventory validation
                    if item.item_ingredients.exists():
                        for item_ingredient in item.item_ingredients.all():
                            required_quantity = item_ingredient.quantity * order_item.quantity
                            ingredient = item_ingredient.ingredients
                            
                            # Check if ingredient exists in inventory
                            try:
                                from inventory.models import Inventory
                                inventory_item = Inventory.objects.get(
                                    branch=order.branch,
                                    ingredient_name__iexact=ingredient.ingredient_name
                                )
                                
                                # Check if enough stock is available
                                if inventory_item.available_quantity < required_quantity:
                                    return Response({
                                        "error": f"Insufficient stock for {ingredient.name}. "
                                                f"Required: {required_quantity} {item_ingredient.unit}, "
                                                f"Available: {inventory_item.available_quantity} {inventory_item.unit}"
                                    }, status=status.HTTP_400_BAD_REQUEST)
                                
                                # Deduct from inventory
                                inventory_item.available_quantity -= required_quantity
                                inventory_item.save()
                                
                                # Log the transaction
                                from inventory.models import InventoryTransaction
                                InventoryTransaction.objects.create(
                                    inventory=inventory_item,
                                    transaction_type='sale',
                                    quantity_change=-required_quantity,
                                    reference_id=order_item.order_item_id
                                )
                                
                            except Inventory.DoesNotExist:
                                # If ingredient not in inventory, skip inventory deduction
                                pass

                # Update order status
                order.status = OrderStatus.COMPLETED
                order.save()

                return Response({'detail': 'Order marked as completed'})

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """Change order status with validation and history tracking"""
        order = self.get_object()
        new_status = request.data.get('status')
        notes = request.data.get('notes')

        if not new_status:
            return Response(
                {"error": "Status is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                order.change_status(new_status, request.user, notes)
                serializer = self.get_serializer(order)
                return Response(serializer.data)
        except ValidationError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def mark_as_paid(self, request, pk=None):
        order = self.get_object()
        if not order.status == OrderStatus.COMPLETED:
            return Response(
                {"error": "Order must be completed before it can be marked as paid."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if order.paid:
            return Response(
                {"error": "Order is already marked as paid."},
                status=status.HTTP_400_BAD_REQUEST
            )
        order.paid = True
        order.paid_at = timezone.now()
        order.save()
        return Response({"message": "Order marked as paid."}, status=status.HTTP_200_OK)
    
class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), HasRolePermission('order')]
        return [IsAuthenticated(), HasRolePermission('order')]

    def get_queryset(self):
        """Filter items based on the user's branch and order"""
        user = self.request.user
        order_pk = self.kwargs.get('order_pk')
        
        if hasattr(user, 'branch'):
            queryset = OrderItem.objects.filter(order__branch=user.branch)
            if order_pk:
                queryset = queryset.filter(order_id=order_pk)
            return queryset
        return OrderItem.objects.none()

    def create(self, request, *args, **kwargs):
        """Create a new order item"""
        try:
            with transaction.atomic():
                # Validate order exists and belongs to user's branch
                order_id = request.data.get('order')
                order = Order.objects.get(id=order_id)
                
                if order.branch != request.user.branch:
                    return Response(
                        {"error": "Order does not belong to your branch"},
                        status=status.HTTP_403_FORBIDDEN
                    )

                # Validate item exists and get its price
                item_id = request.data.get('item')
                item = Item.objects.get(id=item_id)
                
                # Create the order item
                order_item = OrderItem.objects.create(
                    order=order,
                    item=item,
                    quantity=request.data.get('quantity', 1),
                    price=item.price
                )

                # Update order total
                order.total_amount += (order_item.price * order_item.quantity)
                order.save()

                serializer = self.get_serializer(order_item)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Order.DoesNotExist:
            return Response(
                {"error": "Order not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Item.DoesNotExist:
            return Response(
                {"error": "Item not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        """Update an order item"""
        try:
            with transaction.atomic():
                order_item = self.get_object()
                old_total = order_item.price * order_item.quantity

                # Update fields
                if 'quantity' in request.data:
                    order_item.quantity = request.data['quantity']
                if 'item' in request.data:
                    new_item = Item.objects.get(id=request.data['item'])
                    order_item.item = new_item
                    order_item.price = new_item.price

                order_item.save()
                new_total = order_item.price * order_item.quantity

                # Update order total
                order = order_item.order
                order.total_amount = order.total_amount - old_total + new_total
                order.save()

                serializer = self.get_serializer(order_item)
                return Response(serializer.data)

        except Item.DoesNotExist:
            return Response(
                {"error": "Item not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, *args, **kwargs):
        """Delete an order item"""
        try:
            with transaction.atomic():
                order_item = self.get_object()
                order = order_item.order

                # Update order total
                order.total_amount -= (order_item.price * order_item.quantity)
                order.save()

                # Delete the item
                order_item.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )