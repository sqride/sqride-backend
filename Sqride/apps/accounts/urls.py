from django.urls import path, include
from accounts.views.super_admin_views import (SuperAdminRegistrationView,
                                              SuperAdminLoginView)
from accounts.views.owner_views import OwnerRegistrationView,OwnerLoginView,OwnerRestaurantsView
from accounts.views.branch_owner_views import BranchOwnerRegistrationView
from accounts.views.user_views import UserRoleViewSet,BranchUserViewSet
from accounts.views.branch_views import BranchPortalLoginView
from accounts.views.password_reset_views import PasswordResetRequestView, PasswordResetConfirmView,PasswordResetValidateTokenView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('superadmin/register', SuperAdminRegistrationView, basename='superadmin-register')
router.register('owner/register', OwnerRegistrationView, basename='owner-register')
router.register('branch-owner/register', BranchOwnerRegistrationView, basename='branch-owner-register')
router.register('superadmin/login', SuperAdminLoginView, basename='superadmin-login')
router.register('owner/login', OwnerLoginView, basename='owner-login')
router.register('branch-portal/login', BranchPortalLoginView, basename='branch-portal-login')
router.register('roles', UserRoleViewSet, basename='user-role')
router.register('branch-users', BranchUserViewSet, basename='branch-user')
router.register('owner/restaurants', OwnerRestaurantsView, basename='owner-restaurants')
router.register('password-reset/request/', PasswordResetRequestView, basename='password-reset')
router.register("password-reset/confirm/", PasswordResetConfirmView, basename='password-reset-confirm')
router.register("password-reset/validate-token/", PasswordResetValidateTokenView, basename='password-reset-validate-token')
urlpatterns = [

    path('', include(router.urls)),
]