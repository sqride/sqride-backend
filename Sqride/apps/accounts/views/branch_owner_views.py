from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.permissions import IsSuperAdmin, IsOwner, CanManageUsers
from accounts.renderer import UserRenderer
from accounts.serializers.branch_owner_serializers import *
from restaurants import models 
from accounts.models import BranchOwner


def get_tokens_for_branch_owner(user):
    refresh = RefreshToken.for_user(user)
    refresh['user_id'] = str(user.id)
    refresh['user_type'] = 'branch_owner'
    refresh['username'] = user.username
    refresh['branch_id'] = str(user.branch.id) if user.branch else None
    
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class BranchOwnerRegistrationView(viewsets.ModelViewSet):
    """Registration endpoint for Branch Owners"""
    permission_classes = [IsSuperAdmin, permissions.IsAuthenticated]  # Changed from IsOwner to IsSuperAdmin
    renderer_classes = [UserRenderer]
    serializer_class = BranchOwnerRegistrationSerializer
    queryset = BranchOwner.objects.all()
    def post(self, request):
        try:           
            # Validate required fields
            required_fields = ['restaurant','name', 'branch', 'username', 'email', 'password','confirm_password']
            for field in required_fields:
                if field not in request.data:
                    return Response({
                        'error': f'{field} is required'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create mutable copy of request data
            registration_data = request.data
            
            # Verify the owner exists
            try:
                restaurant = models.Restaurant.objects.get(id=registration_data['restaurant'])
            except models.Restaurant.DoesNotExist:
                return Response({
                    'error': 'Owner not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Verify the branch exists and belongs to the specified owner
            try:
                branch = models.Branch.objects.get(id=registration_data['branch'])
                if branch.restaurant.owner.id != restaurant.id:
                    return Response({
                        'error': 'Branch does not belong to the specified owner'
                    }, status=status.HTTP_400_BAD_REQUEST)
            except models.Branch.DoesNotExist:
                return Response({
                    'error': 'Branch not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            
            serializer = self.get_serializer(data=registration_data)
            if serializer.is_valid(raise_exception=True):
                user = serializer.save()
                tokens = get_tokens_for_branch_owner(user)
                return Response({
                    'tokens': tokens,
                    'user': BranchOwnerSerializer(user).data,
                    "msg": "Branch Owner Registration Successful"
                }, status=status.HTTP_201_CREATED)
            else:
                
                return Response({
                    'error': 'Validation failed',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
           
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            

