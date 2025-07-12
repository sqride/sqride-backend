from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from core.models import TimestampedModel
from django.contrib.auth.hashers import make_password, check_password


class SuperAdminManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError("The Username field must be set")
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):  # Renamed method
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_super_admin", True)  # Custom field for Super Admin
        return self.create_user(username, email, password, **extra_fields)

class SuperAdmin(AbstractBaseUser, PermissionsMixin, TimestampedModel):
    username = models.CharField(max_length=255, unique=True)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=True)
    is_super_admin = models.BooleanField(default=True)  # Custom field for Super Admin
    
    objects = SuperAdminManager()
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']
    
    
    def __str__(self):
        return self.username


class OwnerManager(BaseUserManager):
    def create_owner(self, super_admin, username, name, email, password=None):
        if not email:
            raise ValueError("Owners must have an email address")
        email = self.normalize_email(email)
        owner = self.model(super_admin=super_admin,username=username, name=name, email=email)
        owner.set_password(password)
        owner.save(using=self._db)
        return owner

class Owner(TimestampedModel,AbstractBaseUser):
    super_admin = models.ForeignKey('SuperAdmin', on_delete=models.SET_NULL, related_name='owners', null=True)
    username = models.CharField(max_length=150, unique=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    
    objects = OwnerManager()

    class Meta:
        db_table = 'owners'
        indexes = [
            models.Index(fields=['super_admin'], name='idx_owners_super_admin_id'),
            models.Index(fields=['username'], name='idx_owners_username')
        ]

    def __str__(self):
        return self.name
    
    def check_password(self, raw_password):
        return check_password(raw_password, self.password)


class UserRole(TimestampedModel):
    name = models.CharField(max_length=255)
    branch = models.ForeignKey("restaurants.Branch", on_delete=models.CASCADE, related_name="user_roles")

    # General Access Permissions
    dashboard_access = models.BooleanField(default=False)

    # Sales Permissions
    order = models.BooleanField(default=False)
    transactions = models.BooleanField(default=False)
    invoices = models.BooleanField(default=False)

    # POS and Kitchen Portals
    POS_system = models.BooleanField(default=False)
    process_billing_in_pos = models.BooleanField(default=False)
    kitchen_display = models.BooleanField(default=False)

    # Inventory Management
    categories = models.BooleanField(default=False)
    products = models.BooleanField(default=False)
    items = models.BooleanField(default=False)
    modifiers = models.BooleanField(default=False)
    ingredients = models.BooleanField(default=False)

    # Staff Management
    roles = models.BooleanField(default=False)
    manage_users = models.BooleanField(default=False) 
    customers = models.BooleanField(default=False)

    # Expense Management
    expense_types = models.BooleanField(default=False)
    expense_records = models.BooleanField(default=False)

    # Reports Access
    overall_report = models.BooleanField(default=False)
    tax_report = models.BooleanField(default=False)
    expense_report = models.BooleanField(default=False)
    stock_report = models.BooleanField(default=False)

    # Payments Management
    payment_methods = models.BooleanField(default=False)
    payment_transactions = models.BooleanField(default=False)

    # Settings Access
    general_settings = models.BooleanField(default=False)
    security_settings = models.BooleanField(default=False)
    notifications_settings = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "User Role"
        verbose_name_plural = "User Roles"
        unique_together = ('name', 'branch') 
        db_table = "user_role"  # Explicitly setting table name (optional)
        indexes = [
            models.Index(fields=["branch"], name="idx_user_role_name"),
        ]

class UserManager(BaseUserManager):
    def create_user(self, branch, role, username, name, email, password=None):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(branch=branch, role=role, username=username, name=name, email=email)
        user.set_password(password)
        user.save(using=self._db)
        return user
    

class User(TimestampedModel,AbstractBaseUser):
    branch = models.ForeignKey("restaurants.Branch", on_delete=models.CASCADE, related_name="users")
    role = models.ForeignKey(UserRole, on_delete=models.CASCADE, related_name="users")
    username = models.CharField(max_length=150, unique=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)  # Use Django's auth system for better security

    objects = UserManager()  # Assign the custom manager
    
    USERNAME_FIELD = 'username'  # or 'email' if you want to log in with email
    REQUIRED_FIELDS = ['email', 'name']  # Fields to ask for when using createsuperuser

    class Meta:
        db_table = "users"
        indexes = [
            models.Index(fields=["branch"], name="idx_users_branch_id"),
            models.Index(fields=["role"], name="idx_users_role_id"),
        ]

    def __str__(self):
        return f"{self.name} ({self.email})"

class BranchOwnerManager(BaseUserManager):
    def create_user(self, username,name, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(username=username, name=name, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
class BranchOwner(TimestampedModel,AbstractBaseUser):
    branch = models.ForeignKey("restaurants.Branch", on_delete=models.CASCADE, related_name="branch_owners")
    name = models.CharField(max_length=255)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    
    objects = BranchOwnerManager()  # Assign the custom manager
    
    USERNAME_FIELD = "username"  # This is required for authentication
    REQUIRED_FIELDS = ["email"]  # Required for user creation


    class Meta:
        db_table = "branchowners"
        indexes = [
            models.Index(fields=["branch"], name="idx_branchowners_branch_id"),
        ]

    def __str__(self):
        return f"{self.name} "
