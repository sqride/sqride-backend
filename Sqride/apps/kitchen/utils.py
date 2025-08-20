from django.utils import timezone
from datetime import timedelta
from .models import KitchenOrder, KitchenOrderItem, KitchenAnalytics
from django.db.models import Sum, Avg
from .models import KitchenStation


def calculate_order_priority(order):
    """
    Calculate priority for a kitchen order based on various factors
    """
    priority = 0
    
    # Base priority
    priority += 5
    
    # Time-based priority (orders waiting longer get higher priority)
    if order.created_at:
        waiting_time = timezone.now() - order.created_at
        if waiting_time > timedelta(minutes=30):
            priority += 3
        elif waiting_time > timedelta(minutes=15):
            priority += 2
        elif waiting_time > timedelta(minutes=5):
            priority += 1
    
    # Order type priority
    if hasattr(order.order, 'order_type'):
        if order.order.order_type == 'dining':
            priority += 2  # Dining orders get higher priority
        elif order.order.order_type == 'delivery':
            priority += 1  # Delivery orders get medium priority
    
    # Customer priority (VIP customers, etc.)
    if hasattr(order.order, 'customer') and order.order.customer:
        # You can implement customer priority logic here
        pass
    
    return min(priority, 10)  # Cap at 10


def check_sla_breaches():
    """
    Check for SLA breaches and send notifications
    """
    from .services import KitchenNotificationService
    
    # Find orders that are taking too long
    threshold_time = timezone.now() - timedelta(minutes=20)  # 20 minutes threshold
    
    overdue_orders = KitchenOrder.objects.filter(
        status='preparing',
        started_at__lt=threshold_time
    )
    
    for order in overdue_orders:
        # Calculate delay
        delay_minutes = int((timezone.now() - order.started_at).total_seconds() / 60)
        
        # Send delay notification
        KitchenNotificationService.notify_delay_alert(
            order.order.branch.id,
            order.id,
            delay_minutes
        )
        
        # Update analytics
        for item in order.items.all():
            if item.station:
                analytics, _ = KitchenAnalytics.objects.get_or_create(
                    station=item.station,
                    date=timezone.now().date()
                )
                analytics.sla_breaches += 1
                analytics.save()


def get_station_efficiency(station, days=7):
    """
    Calculate efficiency metrics for a kitchen station
    """
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    analytics = KitchenAnalytics.objects.filter(
        station=station,
        date__range=[start_date, end_date]
    )
    
    if not analytics.exists():
        return {
            'total_orders': 0,
            'average_preparation_time': None,
            'sla_breaches': 0,
            'efficiency_score': 0
        }
    
    total_orders = analytics.aggregate(total=Sum('total_orders'))['total'] or 0
    sla_breaches = analytics.aggregate(total=Sum('sla_breaches'))['total'] or 0
    
    # Calculate efficiency score (0-100)
    if total_orders > 0:
        breach_rate = (sla_breaches / total_orders) * 100
        efficiency_score = max(0, 100 - breach_rate)
    else:
        efficiency_score = 100
    
    return {
        'total_orders': total_orders,
        'average_preparation_time': analytics.aggregate(
            avg_time=Avg('average_preparation_time')
        )['avg_time'],
        'sla_breaches': sla_breaches,
        'efficiency_score': round(efficiency_score, 2)
    }


def optimize_station_assignments(branch):
    """
    Optimize order assignments across stations
    """
    from .services import KitchenAssignmentService
    
    # Get current workload
    workload = KitchenAssignmentService.get_station_workload(branch)
    
    # Find stations with lowest workload
    sorted_stations = sorted(
        workload.items(),
        key=lambda x: x[1]['total']
    )
    
    # Reassign orders from overloaded stations to underloaded ones
    if len(sorted_stations) >= 2:
        underloaded_station = sorted_stations[0][0]
        overloaded_station = sorted_stations[-1][0]
        
        # Move some orders from overloaded to underloaded station
        items_to_move = KitchenOrderItem.objects.filter(
            station__name=overloaded_station,
            status='pending'
        )[:2]  # Move up to 2 items
        
        for item in items_to_move:
            KitchenAssignmentService.reassign_order(
                item, 
                KitchenStation.objects.get(name=underloaded_station, branch=branch).id
            )


def generate_kitchen_report(branch, start_date=None, end_date=None):
    """
    Generate comprehensive kitchen performance report
    """
    if not start_date:
        start_date = timezone.now().date() - timedelta(days=30)
    if not end_date:
        end_date = timezone.now().date()
    
    # Get all kitchen orders in date range
    orders = KitchenOrder.objects.filter(
        order__branch=branch,
        created_at__date__range=[start_date, end_date]
    )
    
    # Calculate metrics
    total_orders = orders.count()
    completed_orders = orders.filter(status='completed').count()
    cancelled_orders = orders.filter(status='cancelled').count()
    
    # Calculate average preparation time
    completed_items = KitchenOrderItem.objects.filter(
        kitchen_order__in=orders,
        status='completed',
        started_at__isnull=False,
        completed_at__isnull=False
    )
    
    if completed_items.exists():
        avg_prep_time = completed_items.aggregate(
            avg_time=Avg('completed_at' - 'started_at')
        )['avg_time']
    else:
        avg_prep_time = None
    
    # Get station performance
    stations = KitchenStation.objects.filter(branch=branch, is_active=True)
    station_performance = {}
    
    for station in stations:
        station_analytics = KitchenAnalytics.objects.filter(
            station=station,
            date__range=[start_date, end_date]
        ).aggregate(
            total_orders=Sum('total_orders'),
            sla_breaches=Sum('sla_breaches')
        )
        
        station_performance[station.name] = {
            'total_orders': station_analytics['total_orders'] or 0,
            'sla_breaches': station_analytics['sla_breaches'] or 0,
            'efficiency': get_station_efficiency(station, days=(end_date - start_date).days)
        }
    
    return {
        'period': {
            'start_date': start_date,
            'end_date': end_date
        },
        'overview': {
            'total_orders': total_orders,
            'completed_orders': completed_orders,
            'cancelled_orders': cancelled_orders,
            'completion_rate': (completed_orders / total_orders * 100) if total_orders > 0 else 0,
            'average_preparation_time': avg_prep_time
        },
        'station_performance': station_performance,
        'recommendations': _generate_recommendations(station_performance)
    }


def _generate_recommendations(station_performance):
    """
    Generate recommendations based on performance data
    """
    recommendations = []
    
    for station_name, data in station_performance.items():
        if data['efficiency']['efficiency_score'] < 70:
            recommendations.append({
                'station': station_name,
                'type': 'efficiency',
                'message': f'Station {station_name} has low efficiency. Consider staff training or process optimization.',
                'priority': 'high'
            })
        
        if data['sla_breaches'] > data['total_orders'] * 0.1:  # More than 10% SLA breaches
            recommendations.append({
                'station': station_name,
                'type': 'sla',
                'message': f'Station {station_name} has high SLA breach rate. Review workflow and staffing.',
                'priority': 'high'
            })
    
    return recommendations
