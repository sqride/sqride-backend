from rest_framework_simplejwt.tokens import RefreshToken

class OwnerToken(RefreshToken):
    @classmethod
    def for_user(cls, owner):
        token = super().for_user(owner)
        token['user_id'] = str(owner.owner_id)  # Ensure correct ID field
        return token
