from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.permissions import IsSuperAdmin, IsOwner
from accounts.renderer import UserRenderer
from accounts.models import Owner, SuperAdmin
# from restaurants import models
from restaurants.models import Restaurant
from accounts.serializers.owner_serializers import *
from restaurants.serializers import RestaurantSerializer

def get_tokens_for_owner(user):
    refresh = RefreshToken.for_user(user)
    refresh['user_id'] = str(user.id)
    refresh['user_type'] = 'owner'
    refresh['username'] = user.username
    
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

class OwnerRegistrationView(viewsets.ModelViewSet):
    """Registration endpoint for Restaurant Owners"""
    permission_classes = [IsSuperAdmin,permissions.IsAuthenticated]
    renderer_classes = [UserRenderer]
    serializer_class = OwnerRegistrationSerializer
    queryset = Owner.objects.all()
    
    def create(self, request):
        
        print("user",request.user)
        if not isinstance(request.user, SuperAdmin):
            return Response({"detail": "Invalid user type"}, status=status.HTTP_403_FORBIDDEN)

        registration_data = request.data.copy()
            
        registration_data['super_admin'] = request.user.id
        print(registration_data)
        serializer = self.get_serializer(data=registration_data)
        if serializer.is_valid(raise_exception=True):
            user = serializer.save()
            tokens = get_tokens_for_owner(user)
            return Response({
                'tokens': tokens,
                'user': OwnerSerializer(user).data,
                "msg":"Owner Registration Successful"
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OwnerLoginView(viewsets.ModelViewSet):
    """Dedicated login endpoint for Restaurant Owners"""
    permission_classes = [permissions.AllowAny]
    serializer_class = OwnerLoginSerializer
    queryset = Owner.objects.none()
    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            print("user is ",user)
            tokens = get_tokens_for_owner(user)
    
            return Response({
                'tokens': tokens,
                'user': OwnerSerializer(user).data
            }, status=status.HTTP_200_OK)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

   
class OwnerRestaurantsView(viewsets.ModelViewSet):
    queryset = Owner.objects.all()
    permission_classes = [IsOwner]
    serializer_class = RestaurantSerializer
    def list(self, request):
        try:
            # Get owner from the request (set by IsOwner permission)
            owner = request.user
            
            # Get all restaurants for this owner
            restaurants = Restaurant.objects.filter(owner=owner)
            
            # Add some useful metadata
            data = {
                'owner_name': owner.name,
                'owner_email': owner.email,
                'total_restaurants': restaurants.count(),
                'restaurants': RestaurantSerializer(restaurants, many=True).data
            }
            
            return Response(data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
            