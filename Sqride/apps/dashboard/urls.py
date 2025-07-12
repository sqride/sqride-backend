from django.urls import path
from .views import *

urlpatterns = [
    path('branch-insights/', BranchDashboardInsightsViewSet.as_view(), name='branch-insights'),
]

