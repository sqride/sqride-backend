from rest_framework import serializers
from django.contrib.auth.hashers import check_password
from accounts.models import BranchOwner, User,Owner

class BranchPortalLoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(help_text='Username or email')
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        identifier = data.get('identifier')
        password = data.get('password')

        if not identifier or not password:
            raise serializers.ValidationError('Both identifier and password are required')
        print(data)
        # Try BranchOwner first
        try:
            user = BranchOwner.objects.get(username=identifier)
            if check_password(password, user.password):
                data['user'] = user
                data['user_type'] = 'branch_owner'
                return data
        except BranchOwner.DoesNotExist:
            try:
                user = BranchOwner.objects.get(email=identifier)
                if check_password(password, user.password):
                    data['user'] = user
                    data['user_type'] = 'branch_owner'
                    return data
            except BranchOwner.DoesNotExist:
                pass

        # Try User
        try:
            user = User.objects.get(username=identifier)
            print(user)
            if check_password(password, user.password):
                data['user'] = user
                data['user_type'] = 'user'
                return data
        except User.DoesNotExist:
            try:
                user = User.objects.get(email=identifier)
                if check_password(password, user.password):
                    data['user'] = user
                    data['user_type'] = 'user'
                    return data
            except User.DoesNotExist:
                pass

        raise serializers.ValidationError('Invalid credentials')



class RestaurantLoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(help_text='Username or email')
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        identifier = data.get('identifier')
        password = data.get('password')

        if not identifier or not password:
            raise serializers.ValidationError('Both identifier and password are required')

        # Try Owner
        try:
            user = Owner.objects.get(username=identifier)
            if check_password(password, user.password):
                data['user'] = user
                data['user_type'] = 'owner'
                return data
        except Owner.DoesNotExist:
            try:
                user = Owner.objects.get(email=identifier)
                if check_password(password, user.password):
                    data['user'] = user
                    data['user_type'] = 'owner'
                    return data
            except Owner.DoesNotExist:
                pass

        # Try BranchOwner
        try:
            user = BranchOwner.objects.get(username=identifier)
            if check_password(password, user.password):
                data['user'] = user
                data['user_type'] = 'branch_owner'
                return data
        except BranchOwner.DoesNotExist:
            try:
                user = BranchOwner.objects.get(email=identifier)
                if check_password(password, user.password):
                    data['user'] = user
                    data['user_type'] = 'branch_owner'
                    return data
            except BranchOwner.DoesNotExist:
                pass

        # Try authenticating as a branch user
        try:
            user = User.objects.get(username=identifier)
        except User.DoesNotExist:
            try:
                user = User.objects.get(email=identifier)
            except User.DoesNotExist:
                pass
        
        if user and check_password(password, user.password):
            data['user'] = user
            data['user_type'] = 'user'
            return data

        raise serializers.ValidationError('Invalid credentials')




