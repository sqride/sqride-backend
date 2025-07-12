from rest_framework import serializers
from django.contrib.auth.hashers import make_password, check_password
from accounts.models import  Owner

class OwnerRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    
    class Meta:
        model = Owner
        fields = ('username', 'email', 'password', 'confirm_password', 'name', 'super_admin')
        
    def validate(self, data):
        """
        Validate only business rules, not uniqueness
        """
        errors = {}
        
        # 1. Password validation
        password = data.get('password')
        if password:
            if len(password) < 8:
                errors['password'] = 'Password must be at least 8 characters long'
            elif not any(char.isupper() for char in password):
                errors['password'] = 'Password must contain at least one uppercase letter'
            elif not any(char.isdigit() for char in password):
                errors['password'] = 'Password must contain at least one number'
            
            # Check password confirmation
            if password != data.get('confirm_password'):
                errors['confirm_password'] = 'Passwords do not match'

        # 2. Name format validation
        name = data.get('name', '').strip()
        if len(name) < 2:
            errors['name'] = 'Name must be at least 2 characters long'

        if errors:
            raise serializers.ValidationError(errors)

        # Clean data
        data['name'] = name.title()
        data.pop('confirm_password', None)
        
        return data

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)


class OwnerLoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(help_text='Username or email')
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        identifier = data.get('identifier')
        password = data.get('password')

        if not identifier or not password:
            raise serializers.ValidationError('Both identifier and password are required')

        try:
            user = Owner.objects.get(username=identifier)
        except Owner.DoesNotExist:
            try:
                user = Owner.objects.get(email=identifier)
            except Owner.DoesNotExist:
                raise serializers.ValidationError('Owner not found')

        if check_password(password, user.password):
            data['user'] = user
            return data
        raise serializers.ValidationError('Invalid credentials')

class OwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Owner
        fields = "__all__"