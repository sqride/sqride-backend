from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from accounts.models import BranchOwner
import re

class BranchOwnerRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    
    class Meta:
        model = BranchOwner
        fields = "__all__"
    
    def validate(self, data):
    
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
                
        # 3. Username validation
        username = data.get('username', '').strip()
        if len(username) < 3:
            errors['username'] = 'Username must be at least 3 characters long'
        elif not re.match(r'^[a-zA-Z0-9_.-]+$', username):
            errors['username'] = 'Username can only contain letters, numbers, dots, underscores, and hyphens'

        if errors:
            raise serializers.ValidationError(errors)

        # Clean data
        data['username'] = username
        
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

class BranchOwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = BranchOwner
        fields = ('id', 'username', 'email', 'branch')
        
