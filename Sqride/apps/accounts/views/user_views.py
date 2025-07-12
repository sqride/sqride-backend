from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.permissions import CanManageUsers
from accounts.serializers.user_serializers import *
from rest_framework.decorators import action
from accounts.models import UserRole, User
from django.shortcuts import get_object_or_404

# Custom token generation functions
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    refresh['user_id'] = str(user.id)
    refresh['user_type'] = 'user'
    refresh['username'] = user.username
    refresh['email'] = user.email
    refresh['branch_id'] = str(user.branch.id) if user.branch else None
    refresh['role_id'] = str(user.role.id) if user.role else None
    
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class UserRoleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user roles within a branch
    """
    serializer_class = UserRoleSerializer
    permission_classes = [CanManageUsers]

    def get_queryset(self):
        """Filter roles based on the branch of the authenticated user."""
        user = self.request.user
              
        if hasattr(user, 'branch') and user.branch:
            return UserRole.objects.filter(branch=user.branch).order_by('id')
        return UserRole.objects.none()

    def list(self, request, *args, **kwargs):
        """List all roles for the branch."""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """Get a specific role by ID."""
        queryset = self.get_queryset()
        role = get_object_or_404(queryset, pk=pk)
        serializer = self.get_serializer(role)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """Create a new role for the branch."""
        print("Creating Role | Request User:", request.user)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(branch=request.user.branch)
        return Response(serializer.data, status=201)

    def update(self, request, pk=None, *args, **kwargs):
        """Update an existing role."""
        queryset = self.get_queryset()
        role = get_object_or_404(queryset, pk=pk)
        serializer = self.get_serializer(role, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def partial_update(self, request, pk=None, *args, **kwargs):
        """Partially update a role (PATCH)."""
        queryset = self.get_queryset()
        role = get_object_or_404(queryset, pk=pk)
        serializer = self.get_serializer(role, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def destroy(self, request, pk=None, *args, **kwargs):
        """Delete a role from the branch."""
        queryset = self.get_queryset()
        role = get_object_or_404(queryset, pk=pk)
        role.delete()
        return Response({"message": "Role deleted successfully"}, status=204)

    @action(detail=True, methods=['get'])
    def users(self, request, pk=None):
        """Get all users assigned to this role."""
        role = self.get_object()
        users = User.objects.filter(role=role)  
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)


class BranchUserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing users within a branch
    """
    serializer_class = UserSerializer
    permission_classes = [CanManageUsers,permissions.IsAuthenticated]
    queryset = User.objects.all()
    
    def list(self, request, *args, **kwargs):
        print(request.user.username)
    # Ensure the user is a branch owner and belongs to a branch
        if not hasattr(request.user, 'branch') or not request.user.branch:
            return Response({
                'error': 'User does not belong to a branch'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get all users of the branch that the branch owner manages
        queryset = User.objects.filter(branch=request.user.branch).order_by('id')
        
        # Serialize the data
        serializer = self.get_serializer(queryset, many=True)
        
        # Return custom response
        return Response({
            'total_users': queryset.count(),
            'users': serializer.data
        }, status=status.HTTP_200_OK)


    def create(self, request, *args, **kwargs):
        """
        Create a new user and automatically assign the branch of the authenticated user.
        """
        if not hasattr(request.user, 'branch') or not request.user.branch:
            return Response({
                'error': 'User does not belong to a branch'
            }, status=status.HTTP_400_BAD_REQUEST)

        data = request.data.copy()
        data['branch'] = request.user.branch.id  # Assign the branch of the authenticated branch owner
        print(data)
        serializer = self.get_serializer(data=data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response({
                'message': 'User created successfully',
                'user': serializer.data
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """
        Update a user, ensuring they belong to the branch of the authenticated user.
        """
        instance = self.get_object()
        if instance.branch != request.user.branch:
            return Response({'error': 'You can only update users in your branch'}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(instance, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        """
        Partially update a user while ensuring they belong to the correct branch.
        """
        instance = self.get_object()
        if instance.branch != request.user.branch:
            return Response({'error': 'You can only update users in your branch'}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a user only if they belong to the authenticated user's branch.
        """
        instance = self.get_object()
        if instance.branch != request.user.branch:
            return Response({'error': 'You can only delete users in your branch'}, status=status.HTTP_403_FORBIDDEN)

        instance.delete()
        return Response({'message': 'User deleted successfully'}, status=status.HTTP_204_NO_CONTENT)

