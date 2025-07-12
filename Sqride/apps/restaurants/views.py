from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import *
from .serializers import *
from accounts.permissions import IsSuperAdmin, IsOwnerOrSuperAdmin
from accounts.models import Owner
from django.db import models

class RestaurantViewSet(viewsets.ModelViewSet):
    queryset = Restaurant.objects.all()
    serializer_class = RestaurantSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    # def get_permissions(self):
    #     if self.action == 'create':
    #         return [IsSuperAdmin()]
    #     elif self.action == 'list':
    #         return [IsOwnerOrSuperAdmin()]
    #     return super().get_permissions()
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return self.queryset.model.objects.none()
        
        user = self.request.user
        user_type = self.request.auth.get("user_type")
        if user_type == "super_admin":
            return Restaurant.objects.all()
        return Restaurant.objects.filter(owner=user)
    
    def list(self, request):
        user = self.request.user
        user_type = request.auth.get("user_type")
        if user_type == "super_admin":
            queryset = Restaurant.objects.all()
        else:
            queryset = Restaurant.objects.filter(owner=user)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def create(self, request):
        user = self.request.user
        user_type = request.auth.get("user_type")
        
        # if user_type != "super_admin":
        #     return Response(
        #         {"detail": "Only super admins can create restaurants."},
        #         status=status.HTTP_403_FORBIDDEN
        #     )
        
        # Validate owner exists
        owner_id = request.data.get('owner')
        try:
            owner = Owner.objects.get(id=owner_id)
        except Owner.DoesNotExist:
            return Response(
                {"detail": "Owner not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create restaurant
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            restaurant = serializer.save()
            
            # Create default branch if branch data is provided
            branch_data = request.data.get('branch')
            if branch_data:
                branch_data['restaurant'] = restaurant.id
                branch_serializer = BranchSerializer(data=branch_data)
                if branch_serializer.is_valid():
                    branch_serializer.save()
                    restaurant_data = serializer.data
                    restaurant_data['branch'] = branch_serializer.data
                    return Response(restaurant_data, status=status.HTTP_201_CREATED)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Check if user has permission to update this restaurant
        user_type = request.auth.get("user_type")
        if user_type != "super_admin" and instance.owner != request.user:
            return Response(
                {"detail": "You don't have permission to update this restaurant."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            self.perform_update(serializer)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Only super admin can delete restaurants
        user_type = request.auth.get("user_type")
        if user_type != "super_admin":
            return Response(
                {"detail": "Only super admins can delete restaurants."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if restaurant has any active branches
        if instance.branches.filter(is_active=True).exists():
            return Response(
                {"detail": "Cannot delete restaurant with active branches."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        restaurant = self.get_object()
        restaurant.is_active = True
        restaurant.save()
        return Response({"detail": "Restaurant activated successfully."})

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        restaurant = self.get_object()
        restaurant.is_active = False
        restaurant.save()
        return Response({"detail": "Restaurant deactivated successfully."})

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        restaurant = self.get_object()
        data = {
            'total_branches': restaurant.branches.count(),
            'active_branches': restaurant.branches.filter(is_active=True).count(),
            'total_tables': restaurant.branches.aggregate(
                total_tables=models.Count('tables')
            )['total_tables'],
            'subscription_status': restaurant.subscription_status,
            'subscription_end_date': restaurant.subscription_end_date
        }
        return Response(data)


class BranchViewSet(viewsets.ModelViewSet):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrSuperAdmin]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return self.queryset.model.objects.none()
        
        user = self.request.user
        user_type = self.request.auth.get("user_type")
        
        if user_type == "super_admin":
            return Branch.objects.all()
        return Branch.objects.filter(restaurant__owner=user)
    
    def create(self, request):
        user = self.request.user
        user_type = request.auth.get("user_type")
        
        # Validate restaurant exists and user has permission
        restaurant_id = request.data.get('restaurant')
        try:
            restaurant = Restaurant.objects.get(id=restaurant_id)
            if user_type != "super_admin" and restaurant.owner != user:
                return Response(
                    {"detail": "You don't have permission to create branches for this restaurant."},
                    status=status.HTTP_403_FORBIDDEN
                )
        except Restaurant.DoesNotExist:
            return Response(
                {"detail": "Restaurant not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            branch = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Check if user has permission to update this branch
        user_type = request.auth.get("user_type")
        if user_type != "super_admin" and instance.restaurant.owner != request.user:
            return Response(
                {"detail": "You don't have permission to update this branch."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            self.perform_update(serializer)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Check if user has permission to delete this branch
        user_type = request.auth.get("user_type")
        if user_type != "super_admin" and instance.restaurant.owner != request.user:
            return Response(
                {"detail": "You don't have permission to delete this branch."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if branch has any active tables or orders
        if instance.tables.filter(is_active=True).exists():
            return Response(
                {"detail": "Cannot delete branch with active tables."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        branch = self.get_object()
        branch.is_active = True
        branch.save()
        return Response({"detail": "Branch activated successfully."})

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        branch = self.get_object()
        branch.is_active = False
        branch.save()
        return Response({"detail": "Branch deactivated successfully."})

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        branch = self.get_object()
        data = {
            'total_tables': branch.tables.count(),
            'active_tables': branch.tables.filter(is_active=True).count(),
            'total_zones': branch.zones.count(),
            'active_zones': branch.zones.filter(is_active=True).count(),
            'currency': branch.currency.currency_code
        }
        return Response(data)

    @action(detail=True, methods=['get'])
    def tables(self, request, pk=None):
        branch = self.get_object()
        tables = branch.tables.all()
        serializer = RestaurantTableSerializer(tables, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def zones(self, request, pk=None):
        branch = self.get_object()
        zones = branch.zones.all()
        serializer = RestaurantZoneSerializer(zones, many=True)
        return Response(serializer.data)


class RestaurantCategoryViewSet(viewsets.ModelViewSet):
    queryset = RestaurantCategory.objects.all()
    serializer_class = RestaurantCategorySerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrSuperAdmin]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return self.queryset.model.objects.none()
        
        user = self.request.user
        user_type = self.request.auth.get("user_type")
        
        if user_type == "super_admin":
            return RestaurantCategory.objects.all()
        return RestaurantCategory.objects.filter(restaurant__owner=user)
    
    def create(self, request):
        user = self.request.user
        user_type = request.auth.get("user_type")
        
        # Validate restaurant exists and user has permission
        restaurant_id = request.data.get('restaurant')
        try:
            restaurant = Restaurant.objects.get(id=restaurant_id)
            if user_type != "super_admin" and restaurant.owner != user:
                return Response(
                    {"detail": "You don't have permission to create categories for this restaurant."},
                    status=status.HTTP_403_FORBIDDEN
                )
        except Restaurant.DoesNotExist:
            return Response(
                {"detail": "Restaurant not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            category = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RestaurantTableViewSet(viewsets.ModelViewSet):
    queryset = RestaurantTable.objects.all()
    serializer_class = RestaurantTableSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrSuperAdmin]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return self.queryset.model.objects.none()
        
        user = self.request.user
        user_type = self.request.auth.get("user_type")
        
        if user_type == "super_admin":
            return RestaurantTable.objects.all()
        return RestaurantTable.objects.filter(branch__restaurant__owner=user)
    
    def create(self, request):
        user = self.request.user
        user_type = request.auth.get("user_type")
        
        # Validate branch exists and user has permission
        branch_id = request.data.get('branch')
        try:
            branch = Branch.objects.get(id=branch_id)
            if user_type != "super_admin" and branch.restaurant.owner != user:
                return Response(
                    {"detail": "You don't have permission to create tables for this branch."},
                    status=status.HTTP_403_FORBIDDEN
                )
        except Branch.DoesNotExist:
            return Response(
                {"detail": "Branch not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            table = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        table = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in dict(RestaurantTable._meta.get_field('status').choices):
            return Response(
                {"detail": "Invalid status."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        table.status = new_status
        table.save()
        return Response({"detail": "Table status updated successfully."})


class RestaurantZoneViewSet(viewsets.ModelViewSet):
    queryset = RestaurantZone.objects.all()
    serializer_class = RestaurantZoneSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrSuperAdmin]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return self.queryset.model.objects.none()
        
        user = self.request.user
        user_type = self.request.auth.get("user_type")
        
        if user_type == "super_admin":
            return RestaurantZone.objects.all()
        return RestaurantZone.objects.filter(branch__restaurant__owner=user)
    
    def create(self, request):
        user = self.request.user
        user_type = request.auth.get("user_type")
        
        # Validate branch exists and user has permission
        branch_id = request.data.get('branch')
        try:
            branch = Branch.objects.get(id=branch_id)
            if user_type != "super_admin" and branch.restaurant.owner != user:
                return Response(
                    {"detail": "You don't have permission to create zones for this branch."},
                    status=status.HTTP_403_FORBIDDEN
                )
        except Branch.DoesNotExist:
            return Response(
                {"detail": "Branch not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            zone = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RestaurantHolidayViewSet(viewsets.ModelViewSet):
    queryset = RestaurantHoliday.objects.all()
    serializer_class = RestaurantHolidaySerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrSuperAdmin]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return self.queryset.model.objects.none()
        
        user = self.request.user
        user_type = self.request.auth.get("user_type")
        
        if user_type == "super_admin":
            return RestaurantHoliday.objects.all()
        return RestaurantHoliday.objects.filter(restaurant__owner=user)
    
    def create(self, request):
        user = self.request.user
        user_type = request.auth.get("user_type")
        
        # Validate restaurant exists and user has permission
        restaurant_id = request.data.get('restaurant')
        try:
            restaurant = Restaurant.objects.get(id=restaurant_id)
            if user_type != "super_admin" and restaurant.owner != user:
                return Response(
                    {"detail": "You don't have permission to create holidays for this restaurant."},
                    status=status.HTTP_403_FORBIDDEN
                )
        except Restaurant.DoesNotExist:
            return Response(
                {"detail": "Restaurant not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            holiday = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

