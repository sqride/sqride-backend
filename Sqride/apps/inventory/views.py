from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .models import *
from .serializers import *
from rest_framework.permissions import IsAuthenticated

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = InventoryCategory.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    
    def list(self, request, *args, **kwargs):
        user = request.user

        if hasattr(user, 'branch'):
            branch = user.branch
            categories = InventoryCategory.objects.filter(branch=branch).order_by('inventory_category_id')
            serializer = self.get_serializer(categories, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(
            {"detail": "You are not authorized to view inventory categories."},
            status=status.HTTP_403_FORBIDDEN
        )
        

    def create(self, request, *args, **kwargs):
        user = request.user
        if hasattr(user, 'branch'):
            # Create a mutable copy of request.data
            data = request.data.copy()
            data['branch'] = user.branch.id
            print(data)
            serializer = self.get_serializer(data=data)
            if serializer.is_valid(raise_exception=True):
                serializer.save()
                return Response({"msg":"Cateory created successfully","data":serializer.data}, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "You are not authorized to perform this action."}, status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    

class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]
    
    def list(self,request):
        user=request.user
    
        if hasattr(user, "branch"):
            branch=user.branch
            supplier = Supplier.objects.filter(branch=branch).order_by("supplier_id")
            serializer=self.get_serializer(supplier,many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response({"Details":"No supplier exist"},status=status.HTTP_404_NOT_FOUND)

    def create(self, request, *args, **kwargs):
        user = request.user

        if hasattr(user, 'branch'):
            # Create a mutable copy of request.data
            data = request.data.copy()
            data['branch'] = user.branch.id

            serializer = self.get_serializer(data=data)
            if serializer.is_valid(raise_exception=True):
                serializer.save()
                return Response({"msg": "Supplier Created Successfully","data":serializer.data}, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "You are not authorized to perform this action."}, status=status.HTTP_403_FORBIDDEN)
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid(raise_exception=True):
            self.perform_update(serializer)
            return Response({
                "detail": "Supplier updated successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"detail": "Supplier deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )
        
class InventoryViewSet(viewsets.ModelViewSet):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        user=request.user
        if hasattr(user, "branch"):
            branch=user.branch
            inventory = Inventory.objects.filter(branch=branch).order_by("inventory_id")
            serializer=self.get_serializer(inventory,many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response({"Details":"No inventory exist"},status=status.HTTP_404_NOT_FOUND)

    def create(self, request, *args, **kwargs):
        user = request.user

        if hasattr(user, 'branch'):
            # Create a mutable copy of request.data
            data = request.data.copy()
            data['branch'] = user.branch.id

            serializer = self.get_serializer(data=data)
            if serializer.is_valid(raise_exception=True):
                serializer.save()
                return Response({"msg": "Inventory Created Successfully","data":serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        instance=self.get_object()
        serializer=self.get_serializer(instance)
        return Response(serializer.data,status=status.HTTP_200_OK)
    
    def update(self, request, pk=None):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data,partial=False)
        if serializer.is_valid(raise_exception=True):
            self.perform_update(serializer)
            return Response({
                "detail": "Inventory updated successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            self.perform_update(serializer)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, pk=None):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def reduce_stock(self, request, pk=None):
        """Reduce stock of an inventory item by a given quantity."""
        inventory = self.get_object()
        try:
            quantity = float(request.data.get("quantity", 0))
            user=request.user
            if not hasattr(user,"branch"):
                return Response({"error": "You are not authorized to perform this action."}, status=status.HTTP_403_FORBIDDEN)
            if inventory.branch != user.branch:
                return Response({"error": "You are not authorized to reduce stock for this inventory item."}, status=status.HTTP_403_FORBIDDEN)
            
            inventory.reduce_stock(quantity, user, request.data.get("reason", "Manual stock reduction"))

            # inventory.reduce_stock(quantity)
            return Response({"message": "Stock reduced successfully", "new_quantity": inventory.available_quantity}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def restock(self, request, pk=None):
        """Increase stock of an inventory item by a given quantity."""
        inventory = self.get_object()
        try:
            user=request.user
            if not hasattr(user,"branch"):
                    return Response({"error": "You are not authorized to perform this action."}, status=status.HTTP_403_FORBIDDEN)
                
            if inventory.branch != user.branch:
                return Response({"error": "You are not authorized to restock this inventory item."}, status=status.HTTP_403_FORBIDDEN)
            
            quantity = float(request.data.get("quantity", 0))
            inventory.restock(quantity, user, request.data.get("reason", "Manual restock"))
            return Response({
                "message": "Stock restocked successfully",
                "new_quantity": inventory.available_quantity
            }, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except PermissionError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
        
        
        
class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        user=request.user
        if hasattr(user, "branch"):
            branch=user.branch
            inventory = PurchaseOrder.objects.filter(branch=branch).order_by("purchase_order_id")
            serializer=self.get_serializer(inventory,many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response({"Details":"No Purchae Order exist"},status=status.HTTP_404_NOT_FOUND)

    
    def create(self, request):
        user = request.user

        if hasattr(user, 'branch'):
            # Create a mutable copy of request.data
            data = request.data.copy()
            data['branch'] = user.branch.id
            data['purchased_by'] = user.id  # Set the user who created the order
            
            serializer = self.get_serializer(data=data)
            if serializer.is_valid(raise_exception=True):
                serializer.save()
                return Response({"msg": "Purchae Order Created Successfully","data":serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, pk=None):
        instance = self.get_object()
        serializer=self.get_serializer(instance,data=request.data,partial=False)
        if serializer.is_valid(raise_exception=True):
            self.perform_update(serializer)
            return Response({
                "msg": "Purchase Order updated successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def partial_update(self, request, pk=None):
        instance=self.get_object()
        serializer=self.get_serializer(instance,data=request.data,partial=True)
        if serializer.is_valid(raise_exception=True):
            self.perform_update(serializer)
            return Response({
                "msg": "Purchase Order updated successfully.",
                "data": serializer.data
            },status=status.HTTP_200_OK)
        
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, pk=None):
        purchase_order = self.get_object()
        
        if purchase_order.status == 'completed':
            return Response({"error": "You cannot delete a completed order"}, status=status.HTTP_400_BAD_REQUEST)
        
        self.perform_destroy()
        return Response({'msg':'Order deleted successfully'},status=status.HTTP_204_NO_CONTENT)
        
    
    @action(detail=True, methods=['post'])
    def receive(self, request, pk=None):
        """Endpoint to mark a purchase order as received"""
        purchase_order = self.get_object()

        if purchase_order.status == 'completed':
            return Response({"error": "This purchase order is already completed."}, status=status.HTTP_400_BAD_REQUEST)

        purchase_order.mark_as_received()
        return Response({"message": "Purchase order received, inventory updated."}, status=status.HTTP_200_OK)
    
class PurchaseOrderItemViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrderItem.objects.all()
    serializer_class = PurchaseOrderItemSerializer
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        purchase_order_id = request.query_params.get('purchase_order_id')
        if not purchase_order_id:
            return Response({"detail": "purchase_order_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        items = PurchaseOrderItem.objects.filter(purchase_order_id=purchase_order_id).order_by('purchase_order_item_id')
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)
    
    def create(self, request):
        user = request.user

        # Ensure user is associated with a branch
        if not hasattr(user, 'branch'):
            return Response(
                {"detail": "Only branch users can create purchase order items."},
                status=status.HTTP_403_FORBIDDEN
            )

        data = request.data.copy()

        # Optional: If frontend doesn't send unit_price, we'll handle it in serializer
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(
            {"msg": "Purchase Order Item created successfully.", "data": serializer.data},
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, pk=None):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data,partial=False)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def partial_update(self, request, pk=None):
        instance=self.get_object()
        serializer=self.get_serializer(instance,data=request.data,partial=True)
        if serializer.is_valid(raise_exception=True):
            self.perform_update(serializer)
            return Response({
                "msg": "Order Item updated successfully.",
                "data": serializer.data
            },status=status.HTTP_200_OK)
        
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, pk=None):
        instance = self.get_object()
        
        if instance.purchase_order.status=="completed":
            return Response(
                {'error':'Cannot delete and item from a completed order.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        self.perform_destroy(instance)
        return Response({'message':'Item deleted successfully'},status=status.HTTP_204_NO_CONTENT)
    
class InventoryTransactionViewSet(viewsets.ModelViewSet):
    queryset = InventoryTransaction.objects.all()
    serializer_class = InventoryTransactionSerializer
    permission_classes = [IsAuthenticated]
    
    def list(self, request, *args, **kwargs):
        user=request.user
        
        if hasattr(user, "branch"):
            branch=user.branch
            transactions = InventoryTransaction.objects.filter(inventory__branch=branch).order_by("-transaction_date")
            serializer=self.get_serializer(transactions,many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response({"Details":"No transactions exist"},status=status.HTTP_404_NOT_FOUND)

class StockAdjustmentViewSet(viewsets.ModelViewSet):
    queryset = StockAdjustment.objects.all()
    serializer_class = StockAdjustmentSerializer
    permission_classes = [IsAuthenticated]
    
    def list(self, request, *args, **kwargs):
        user=request.user
        
        if hasattr(user, "branch"):
            branch=user.branch
            adjustments = StockAdjustment.objects.filter(inventory__branch=branch).order_by("-adjusted_at")
            serializer=self.get_serializer(adjustments,many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response({"Details":"No adjustments exist"},status=status.HTTP_404_NOT_FOUND)
    
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data['adjusted_by'] = request.user.id  # Inject the current user

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        # Save adjustment
        adjustment = serializer.save()

        # Call apply_adjustment from the model
        adjustment.apply_adjustment()

        return Response({
            "message": "Stock adjustment applied successfully.",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)
        