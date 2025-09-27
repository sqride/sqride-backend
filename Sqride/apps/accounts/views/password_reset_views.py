from rest_framework import viewsets,status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from accounts.serializers.password_reset_serializers import (
    PasswordResetRequestSerializer, 
    PasswordResetConfirmSerializer
)
from accounts.renderer import UserRenderer


class PasswordResetRequestView(viewsets.ModelViewSet):
    """
    View to request password reset
    """
    permission_classes = [permissions.AllowAny]
    renderer_classes = [UserRenderer]
    
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            token = serializer.save()
            return Response({
                'message': 'Password reset email sent successfully',
                'token_expires_at': token.expires_at,
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(viewsets.ModelViewSet):
    """
    View to confirm password reset with token
    """
    permission_classes = [permissions.AllowAny]
    renderer_classes = [UserRenderer]
    
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'message': 'Password reset successfully',
                'user_email': user.email,
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetValidateTokenView(viewsets.ModelViewSet):
    """
    View to validate if a password reset token is valid
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        token = request.data.get('token')
        
        if not token:
            return Response({
                'error': 'Token is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from accounts.models import PasswordResetToken
            reset_token = PasswordResetToken.objects.get(token=token, is_used=False)
            
            if reset_token.is_expired():
                return Response({
                    'valid': False,
                    'error': 'Token has expired'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'valid': True,
                'email': reset_token.email,
                'expires_at': reset_token.expires_at,
            }, status=status.HTTP_200_OK)
            
        except PasswordResetToken.DoesNotExist:
            return Response({
                'valid': False,
                'error': 'Invalid token'
            }, status=status.HTTP_400_BAD_REQUEST)