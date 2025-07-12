from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.renderer import UserRenderer
from accounts.models import SuperAdmin
from accounts.serializers.super_admin_serializers import *

def get_tokens_for_superadmin(user):
    refresh = RefreshToken.for_user(user)
    refresh['user_id'] = str(user.id)
    refresh['user_type'] = 'super_admin'
    refresh['username'] = user.username
    
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


# Registration Views
class SuperAdminRegistrationView(viewsets.ModelViewSet):
    """Registration endpoint for SuperAdmin"""
    permission_classes = [permissions.AllowAny]
    renderer_classes = [UserRenderer]
    serializer_class = SuperAdminRegistrationSerializer
    queryset = SuperAdmin.objects.none()
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            user = serializer.save()
            tokens = get_tokens_for_superadmin(user)
            return Response({
                'tokens': tokens,
                'user': SuperAdminSerializer(user).data,
                "msg":"Super Admin Registration Successful"
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SuperAdminLoginView(viewsets.ModelViewSet):
    """Dedicated login endpoint for SuperAdmin"""
    permission_classes = [permissions.AllowAny]
    renderer_classes = [UserRenderer]
    serializer_class = SuperAdminLoginSerializer
    queryset = SuperAdmin.objects.none()
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            user = serializer.validated_data['user']
            tokens = get_tokens_for_superadmin(user)
            return Response({
                'tokens': tokens,
                'user': SuperAdminSerializer(user).data,
                'msg':'Login Successfull'
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    