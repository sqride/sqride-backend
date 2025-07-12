from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import SuperAdmin, Owner, BranchOwner, User

class MultiUserJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        """Override authenticate to set request.auth properly"""
        auth_result = super().authenticate(request)

        if not auth_result:
            return None  # No authentication header found

        user, token = auth_result  
        
        request.auth = token.payload  

        return user, token.payload  

    def get_user(self, validated_token):
        user_id = validated_token.get("user_id")
        user_type = validated_token.get("user_type")        

        if not user_id or not user_type:
            raise AuthenticationFailed("Invalid token: Missing user_id or user_type")

        model_map = {
            "super_admin": SuperAdmin,
            "owner": Owner,
            "branch_owner": BranchOwner,
            "user": User,
        }

        model = model_map.get(user_type)  # Ensure lowercase matching
        
        if not model:
            raise AuthenticationFailed("Invalid user type")

        try:
            user = model.objects.get(id=user_id)
            return user
        except model.DoesNotExist:
            print(f"❌ User with ID {user_id} not found in {model.__name__}")
            raise AuthenticationFailed("User not found")
