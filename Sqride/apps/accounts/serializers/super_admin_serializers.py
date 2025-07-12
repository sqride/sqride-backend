from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from ..models import SuperAdmin



class SuperAdminRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = SuperAdmin
        fields = "__all__"
        
    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)
    
    
class SuperAdminLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(style={'input_type': 'password'}, write_only=True)

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        if username and password:
            try:
                user = SuperAdmin.objects.get(username=username)
                if user.check_password(password):
                    if not user.is_active:
                        raise serializers.ValidationError("Account is disabled.")
                    data['user'] = user
                    return data
                else:
                    raise serializers.ValidationError("Incorrect password.")
            except SuperAdmin.DoesNotExist:
                raise serializers.ValidationError("Username not found.")
        else:
            raise serializers.ValidationError("Must include 'username' and 'password'.")

class SuperAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuperAdmin
        fields = "__all__"