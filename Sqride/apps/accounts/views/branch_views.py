from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.serializers.branch_owner_serializers import *
from accounts.serializers.user_serializers import *
from accounts.serializers.branch_serializers import *

# Custom token generation functions
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


class BranchPortalLoginView(viewsets.ModelViewSet):  
    permission_classes = [permissions.AllowAny]
    serializer_class = BranchPortalLoginSerializer
    queryset = User.objects.all()

    def create(self, request): 
        serializer = self.serializer_class(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            user_type = serializer.validated_data['user_type']
            
            if user_type == 'branch_owner':
                tokens = get_tokens_for_branch_owner(user)
                user_data = BranchOwnerSerializer(user).data
            else:
                tokens = get_tokens_for_user(user)
                user_data = UserLoginSerializer(user).data
            
            return Response({
                'user_type': user_type,
                'tokens': tokens,
                'user': user_data
            })
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
 
