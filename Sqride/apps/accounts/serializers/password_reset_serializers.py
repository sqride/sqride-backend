from rest_framework import serializers
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.contrib.contenttypes.models import ContentType
from accounts.models import SuperAdmin, Owner, BranchOwner, User, PasswordResetToken
import uuid


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    user_type = serializers.ChoiceField(
        choices=[
            ('super_admin', 'Super Admin'),
            ('owner', 'Owner'),
            ('branch_owner', 'Branch Owner'),
            ('user', 'User'),
        ]
    )

    def validate(self, attrs):
        email = attrs.get('email')
        user_type = attrs.get('user_type')
        
        # Map user types to models
        model_map = {
            'super_admin': SuperAdmin,
            'owner': Owner,
            'branch_owner': BranchOwner,
            'user': User,
        }
        
        model = model_map.get(user_type)
        if not model:
            raise serializers.ValidationError("Invalid user type")
        
        try:
            user = model.objects.get(email=email)
            attrs['user'] = user
            attrs['model'] = model
        except model.DoesNotExist:
            raise serializers.ValidationError("No user found with this email address")
        
        return attrs

    def save(self):
        email = self.validated_data['email']
        user = self.validated_data['user']
        model = self.validated_data['model']
        
        # Invalidate any existing tokens for this user
        content_type = ContentType.objects.get_for_model(model)
        PasswordResetToken.objects.filter(
            content_type=content_type,
            object_id=user.id,
            is_used=False
        ).update(is_used=True)
        
        # Create new token
        expires_at = timezone.now() + timedelta(seconds=getattr(settings, 'PASSWORD_RESET_TIMEOUT', 900))
        token = PasswordResetToken.objects.create(
            email=email,
            content_type=content_type,
            object_id=user.id,
            expires_at=expires_at
        )
        
        # Send email (you can customize this based on your email setup)
        self.send_reset_email(user, token)
        
        return token
    
    def send_reset_email(self, user, token):
        """Send password reset email"""
        subject = 'Password Reset Request - Sqride'
        
        # You can create a proper HTML template for this
        message = f"""
        Hi {getattr(user, 'name', user.username)},
        
        You have requested a password reset for your Sqride account.
        
        Click the link below to reset your password:
        {settings.FRONTEND_URL}/reset-password/{token.token}
        
        This link will expire in 15 minutes.
        
        If you did not request this password reset, please ignore this email.
        
        Best regards,
        Sqride Team
        """
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@sqride.com',
                [user.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Failed to send email: {e}")


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    new_password = serializers.CharField(min_length=8, max_length=128)
    confirm_password = serializers.CharField(min_length=8, max_length=128)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords do not match")
        
        token = attrs.get('token')
        
        try:
            reset_token = PasswordResetToken.objects.get(token=token, is_used=False)
            
            if reset_token.is_expired():
                raise serializers.ValidationError("Token has expired")
            
            attrs['reset_token'] = reset_token
            
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired token")
        
        return attrs

    def save(self):
        reset_token = self.validated_data['reset_token']
        new_password = self.validated_data['new_password']
        
        # Get the user through the generic foreign key
        user = reset_token.user
        
        # Update the password
        user.set_password(new_password)
        user.save()
        
        # Mark token as used
        reset_token.is_used = True
        reset_token.save()
        
        return user