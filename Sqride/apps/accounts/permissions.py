from rest_framework import permissions
from .models import Owner,SuperAdmin,BranchOwner,User, UserRole
import logging
from rest_framework.exceptions import PermissionDenied

logger = logging.getLogger(__name__)
class IsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user:
            raise PermissionDenied("Authentication credentials were not provided.")
            return False
        
        if request.auth and isinstance(request.auth, dict):  # Ensure auth is a dictionary
            is_admin = request.auth.get("user_type") == "super_admin"
            print("Is SuperAdmin:", is_admin)
            if is_admin:
                return True
            raise PermissionDenied("Only Super Admins can perform this action.")
        
        raise PermissionDenied("Invalid authentication format.")
        return False

class IsOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user:
            return False
        
        if not request.auth or 'user_type' not in request.auth:
            return False
        
        # Verify user is an owner
        is_owner = request.auth.get('user_type') == 'owner'
        
        # If user is owner, attach owner to request for later use
        if is_owner:
            return True
            try:
                # Get the actual Owner instance using the owner_id from the token
                owner = Owner.objects.get(id=request.auth.get('user_id'))
                # print(owner)
                # Attach the owner instance to the request
                request.user = owner
                return True
            except Owner.DoesNotExist:
                return False
        
        return False
class IsOwnerOrSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return IsOwner().has_permission(request, view) or IsSuperAdmin().has_permission(request, view)

class IsBranchOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user:
            return False
        
        if not request.auth or 'user_type' not in request.auth:
            return False
        # Verify user is a branch owner
        is_branch_owner = request.auth.get('user_type') == 'branch_owner'
        
        if is_branch_owner:
            return True
        
        return False
    
    

class CanManageUsers(permissions.BasePermission):
    """
    Custom permission to allow Branch Owners and Branch Users with 'can_manage_users' permission.
    """
    def has_permission(self, request, view):
        # Ensure request has authentication
        if not request.auth:
            return False
        # print(type(request))
        user_type = request.auth.get('user_type')
        user_id = request.auth.get('user_id')
        print("Authenticated User Type:", user_type)
        print("Authenticated User ID:", user_id)
        # Allow full access to Branch Owners
        if user_type == 'branch_owner':
            return True
            try:
                branch_owner = BranchOwner.objects.get(id=request.auth.get('user_id'))
                request.user = branch_owner
                return True
            except BranchOwner.DoesNotExist:
                return False

        # Allow access to Branch Users if they have 'can_manage_users' permission
        elif user_type == 'user':  # Assuming 'user' means BranchUser
            return True
            try:
                branch_user = User.objects.get(id=request.auth.get('user_id'))
                request.user = branch_user

                # Check if the role allows managing users
                return True
                # if branch_user.role and branch_user.role.manage_users:
            except User.DoesNotExist:
                return False

        return False

class HasRolePermission(permissions.BasePermission):
    def __init__(self, required_permission):
        self.required_permission = required_permission

    def has_permission(self, request, view):

        if not request.user or not request.user.is_authenticated:
            return False

        role_id = request.auth.get('role_id') if request.auth else None

        if not role_id:
            return False

        try:
            user_role = UserRole.objects.get(id=role_id)
            return getattr(user_role, self.required_permission, False)
        except UserRole.DoesNotExist:
            return False

