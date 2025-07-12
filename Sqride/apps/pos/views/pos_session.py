from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from pos.models import POSSession, POSOrder
from pos.serializers import POSSessionSerializer
from accounts.permissions import HasRolePermission


class POSSessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing POS sessions
    """
    serializer_class = POSSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """
        Override get_permissions to use different permissions for session operations
        """
        return [IsAuthenticated(), HasRolePermission('POS_system')]
    
    def get_queryset(self):
        """Filter sessions based on the user and branch"""
        user = self.request.user
        if hasattr(user, 'branch'):
            return POSSession.objects.filter(
                user=user,
                branch=user.branch
            )
        return POSSession.objects.none()

    def create(self, request, *args, **kwargs):
        """Start a new POS session"""
        user = request.user
        if not hasattr(user, 'branch'):
            return Response(
                {"error": "User must be associated with a branch"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check for active session
        active_session = POSSession.objects.filter(
            user=user,
            branch=user.branch,
            is_active=True
        ).first()
        
        if active_session:
            return Response(
                {"error": "You already have an active session"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=user, branch=user.branch)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def end_session(self, request, pk=None):
        """End a POS session"""
        session = self.get_object()
        if not session.is_active:
            return Response(
                {"error": "Session is already ended"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session.is_active = False
        session.end_time = timezone.now()
        session.save()
        return Response({"message": "Session ended successfully"})

    @action(detail=False, methods=['get'])
    def active_session(self, request):
        """Get the current active session for the user"""
        user = request.user
        if not hasattr(user, 'branch'):
            return Response(
                {"error": "User must be associated with a branch"},
                status=status.HTTP_400_BAD_REQUEST
            )

        active_session = POSSession.objects.filter(
            user=user,
            branch=user.branch,
            is_active=True
        ).first()

        if not active_session:
            return Response(
                {"error": "No active session found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(active_session)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def session_summary(self, request, pk=None):
        """Get detailed summary of a session"""
        session = self.get_object()
        
        # Get all orders in this session
        orders = POSOrder.objects.filter(pos_session=session)
        
        # Calculate statistics
        total_orders = orders.count()
        total_sales = sum(order.order.total_amount for order in orders)
        payment_methods = {
            'CASH': sum(1 for order in orders if order.payment_method == 'CASH'),
            'CARD': sum(1 for order in orders if order.payment_method == 'CARD'),
            'SPLIT': sum(1 for order in orders if order.payment_method == 'SPLIT')
        }
        
        return Response({
            'session_id': session.id,
            'start_time': session.start_time,
            'end_time': session.end_time,
            'total_orders': total_orders,
            'total_sales': total_sales,
            'payment_methods': payment_methods
        }) 