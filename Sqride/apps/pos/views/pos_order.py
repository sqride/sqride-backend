from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction
from pos.models import POSSession, POSOrder, POSOrderItem
from pos.serializers import POSOrderSerializer, POSOrderItemSerializer
from orders.serializers import OrderSerializer
from items.models import Item
from restaurants.models import RestaurantTable
from accounts.permissions import HasRolePermission
from customers.models import Customer
from django.core.exceptions import ValidationError


class POSOrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing POS orders
    """
    serializer_class = POSOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """
        Override get_permissions to use different permissions for different actions
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'process_payment', 'split_payment']:
            return [IsAuthenticated(), HasRolePermission('process_billing_in_pos')]
        return [IsAuthenticated(), HasRolePermission('POS_system')]

    def get_queryset(self):
        """Filter orders based on the user's branch"""
        user = self.request.user
        if hasattr(user, 'branch'):
            return POSOrder.objects.filter(
                pos_session__branch=user.branch
            )
        return POSOrder.objects.none()

    def validate_order_items(self, items_data):
        """Validate stock availability for all items in the order"""
        for item_data in items_data:
            item = Item.objects.get(id=item_data['item'])
            quantity = item_data['quantity']
            
            if item.recipe:
                for ingredient in item.recipe.ingredients.all():
                    required_quantity = ingredient.quantity * quantity
                    if ingredient.ingredient.available_quantity < required_quantity:
                        raise ValidationError(
                            f"Not enough stock for {ingredient.ingredient.ingredient_name}. "
                            f"Required: {required_quantity} {ingredient.unit}, "
                            f"Available: {ingredient.ingredient.available_quantity} {ingredient.unit}"
                        )
        return True

    def create(self, request, *args, **kwargs):
        """Create a new POS order"""
        user = request.user
        if not hasattr(user, 'branch'):
            return Response(
                {"error": "User must be associated with a branch"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                # Validate stock availability
                self.validate_order_items(request.data.get('items', []))
                
                # Get active session
                active_session = POSSession.objects.filter(
                    user=user,
                    branch=user.branch,
                    is_active=True
                ).first()
                
                if not active_session:
                    return Response(
                        {"error": "No active POS session found"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Create base order
                order_data = {
                    'branch': user.branch.id,
                    'customer': request.data.get('customer'),
                    'order_type': request.data.get('order_type', 'dining'),
                    'currency': user.branch.currency.currency_code if user.branch.currency else 'PKR',
                    'total_amount': 0
                }
                
                order_serializer = OrderSerializer(data=order_data)
                if not order_serializer.is_valid():
                    return Response(order_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                order = order_serializer.save()

                # Create POS order
                pos_order_data = {
                    'order': order.order_id,
                    'pos_session': active_session.id,
                    'table': request.data.get('table'),
                    'payment_status': 'PENDING'
                }
                
                serializer = self.get_serializer(data=pos_order_data)
                if not serializer.is_valid():
                    order.delete()  # Clean up if POS order creation fails
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                pos_order = serializer.save()

                # Process order items
                items_data = request.data.get('items', [])
                if not items_data:
                    return Response(
                        {"error": "No items provided in the order"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                total_amount = 0
                created_items = []
                
                for item_data in items_data:
                    try:
                        item = Item.objects.get(id=item_data['item'])
                        quantity = item_data.get('quantity', 1)
                        unit_price = item.price
                        subtotal = unit_price * quantity
                        total_amount += subtotal

                        pos_item = POSOrderItem.objects.create(
                            pos_order=pos_order,
                            item=item,
                            quantity=quantity,
                            unit_price=unit_price,
                            subtotal=subtotal,
                            notes=item_data.get('notes')
                        )
                        created_items.append(pos_item)
                    except Item.DoesNotExist:
                        # If any item is not found, roll back the transaction
                        raise Exception(f"Item with ID {item_data['item']} not found")
                    except Exception as e:
                        raise Exception(f"Error creating item: {str(e)}")

                # Update order total
                order.total_amount = total_amount
                order.save()

                # Update session totals
                active_session.total_orders += 1
                active_session.total_sales += total_amount
                active_session.save()

                # Reserve stock
                order.reserve_stock()

                # Get the complete order with items
                response_serializer = self.get_serializer(pos_order)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """Update an existing POS order"""
        instance = self.get_object()
        
        try:
            with transaction.atomic():
                # Update POS order fields
                instance.table = request.data.get('table', instance.table)
                instance.save()

                # Update base order
                order = instance.order
                order.order_type = request.data.get('order_type', order.order_type)
                order.customer = request.data.get('customer', order.customer)
                order.save()

                # Handle items update
                items_data = request.data.get('items', [])
                total_amount = 0

                # Clear existing items
                instance.pos_items.all().delete()

                # Create new items
                for item_data in items_data:
                    item = Item.objects.get(id=item_data['item'])
                    quantity = item_data.get('quantity', 1)
                    unit_price = item.price
                    subtotal = unit_price * quantity
                    total_amount += subtotal

                    POSOrderItem.objects.create(
                        pos_order=instance,
                        item=item,
                        quantity=quantity,
                        unit_price=unit_price,
                        subtotal=subtotal,
                        notes=item_data.get('notes')
                    )

                # Update order total
                order.total_amount = total_amount
                order.save()

                # Update session total
                instance.pos_session.total_sales = (
                    instance.pos_session.total_sales - instance.order.total_amount + total_amount
                )
                instance.pos_session.save()

                serializer = self.get_serializer(instance)
                return Response(serializer.data)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, *args, **kwargs):
        """Delete a POS order"""
        instance = self.get_object()
        
        # Check if order can be deleted
        if instance.payment_status != 'PENDING':
            return Response(
                {"error": "Cannot delete a paid order"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                # Update session totals
                session = instance.pos_session
                session.total_orders -= 1
                session.total_sales -= instance.order.total_amount
                session.save()

                # Delete the order (this will cascade delete the POS order)
                instance.order.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def process_payment(self, request, pk=None):
        """Process payment for an order"""
        instance = self.get_object()
        
        try:
            with transaction.atomic():
                if instance.payment_status != 'PENDING':
                    return Response(
                        {"error": "Order is already paid"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                payment_method = request.data.get('payment_method')
                if not payment_method:
                    return Response(
                        {"error": "Payment method is required"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                instance.payment_method = payment_method
                instance.payment_status = 'PAID'
                instance.save()

                # Update order status
                order = instance.order
                order.status = 'completed'
                order.save()

                return Response({"message": "Payment processed successfully"})

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def split_payment(self, request, pk=None):
        """Split payment for an order"""
        instance = self.get_object()
        
        try:
            with transaction.atomic():
                if instance.payment_status != 'PENDING':
                    return Response(
                        {"error": "Order is already paid"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                payment_methods = request.data.get('payment_methods', [])
                if not payment_methods:
                    return Response(
                        {"error": "Payment methods are required"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Process split payment logic here
                instance.payment_status = 'PARTIALLY_PAID'
                instance.save()

                return Response({"message": "Split payment processed successfully"})

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        """Add an item to an existing order"""
        pos_order = self.get_object()
        if pos_order.payment_status != 'PENDING':
            return Response(
                {"error": "Cannot modify paid order"},
                status=status.HTTP_400_BAD_REQUEST
            )

        item_id = request.data.get('item')
        quantity = request.data.get('quantity', 1)
        notes = request.data.get('notes')

        try:
            item = Item.objects.get(id=item_id)
        except Item.DoesNotExist:
            return Response(
                {"error": "Item not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        unit_price = item.price
        subtotal = unit_price * quantity

        pos_item = POSOrderItem.objects.create(
            pos_order=pos_order,
            item=item,
            quantity=quantity,
            unit_price=unit_price,
            subtotal=subtotal,
            notes=notes
        )

        # Update order total
        order = pos_order.order
        order.total_amount += subtotal
        order.save()

        # Update session total
        pos_order.pos_session.total_sales += subtotal
        pos_order.pos_session.save()

        return Response(POSOrderItemSerializer(pos_item).data)

    @action(detail=True, methods=['post'])
    def void_item(self, request, pk=None):
        """Void an item from an order"""
        pos_order = self.get_object()
        if pos_order.payment_status != 'PENDING':
            return Response(
                {"error": "Cannot modify paid order"},
                status=status.HTTP_400_BAD_REQUEST
            )

        item_id = request.data.get('item')
        reason = request.data.get('reason')

        try:
            pos_item = POSOrderItem.objects.get(
                pos_order=pos_order,
                item_id=item_id,
                is_void=False
            )
        except POSOrderItem.DoesNotExist:
            return Response(
                {"error": "Item not found in order"},
                status=status.HTTP_404_NOT_FOUND
            )

        pos_item.is_void = True
        pos_item.void_reason = reason
        pos_item.save()

        # Update order total
        order = pos_order.order
        order.total_amount -= pos_item.subtotal
        order.save()

        # Update session total
        pos_order.pos_session.total_sales -= pos_item.subtotal
        pos_order.pos_session.save()

        return Response({"message": "Item voided successfully"})

    @action(detail=False, methods=['get'])
    def active_orders(self, request):
        """Get all active orders for the current session"""
        user = request.user
        if not hasattr(user, 'branch'):
            return Response(
                {"error": "User must be associated with a branch"},
                status=status.HTTP_400_BAD_REQUEST
            )

        active_session = POSSession.objects.filter(
            user=user,
            branch=user.branch,
            is_active=True
        ).first()

        if not active_session:
            return Response(
                {"error": "No active session found"},
                status=status.HTTP_404_NOT_FOUND
            )

        orders = POSOrder.objects.filter(
            pos_session=active_session,
            payment_status='PENDING'
        )
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def print_receipt(self, request, pk=None):
        """Generate receipt for an order"""
        pos_order = self.get_object()
        
        # Get order details
        order = pos_order.order
        items = pos_order.pos_items.all()
        
        # Format receipt data
        receipt_data = {
            'order_id': order.order_id,
            'date': order.created_at,
            'table': pos_order.table.table_number if pos_order.table else 'N/A',
            'items': [
                {
                    'name': item.item.name,
                    'quantity': item.quantity,
                    'unit_price': item.unit_price,
                    'subtotal': item.subtotal
                } for item in items
            ],
            'total_amount': order.total_amount,
            'payment_method': pos_order.payment_method,
            'payment_status': pos_order.payment_status
        }
        
        return Response(receipt_data)

    @action(detail=True, methods=['post'])
    def transfer_table(self, request, pk=None):
        """Transfer order to a different table"""
        pos_order = self.get_object()
        new_table_id = request.data.get('new_table_id')
        
        if not new_table_id:
            return Response(
                {"error": "New table ID is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            new_table = RestaurantTable.objects.get(id=new_table_id)
        except RestaurantTable.DoesNotExist:
            return Response(
                {"error": "Table not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if new table is available
        if new_table.status != 'available':
            return Response(
                {"error": "Table is not available"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update table status
        old_table = pos_order.table
        if old_table:
            old_table.status = 'available'
            old_table.save()
        
        new_table.status = 'occupied'
        new_table.save()
        
        # Update order
        pos_order.table = new_table
        pos_order.save()
        
        return Response({"message": "Table transferred successfully"}) 