from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from accounts.models import User, UserRole

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ('username', 'name', 'email', 'password', 'branch', 'role')
        
    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)


class UserSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = User
        fields = "__all__"
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def create(self, validated_data):
        print(validated_data)
        validated_data['password'] = make_password(validated_data['password'])
    
        return super().create(validated_data)

class UserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRole
        fields = "__all__"
        read_only_fields = ['branch']
        
        def validate_name(self, value):
            branch = self.context['request'].user.branch
            if UserRole.objects.filter(name__iexact=value, branch=branch).exists():
                raise serializers.ValidationError(
                    'A role with this name already exists in this branch'
                )
            return value.strip()

class UserLoginSerializer(serializers.ModelSerializer):
    role=UserRoleSerializer()
    
    class Meta:
        model=User
        fields="__all__"

