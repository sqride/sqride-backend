#!/usr/bin/env python
"""
Simple test script to demonstrate kitchen system functionality
Run this with: python manage.py shell < test_kitchen_system.py
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Sqride.settings')
django.setup()

from django.utils import timezone
from restaurants.models import Restaurant, Branch, Currency
from accounts.models import Owner, SuperAdmin, UserRole, User
from kitchen.models import KitchenStation, KitchenOrder, KitchenOrderItem, KitchenDisplay, KitchenStaff
from kitchen.services import KitchenSystemService, KitchenAssignmentService
from orders.models import Order, OrderItem
from items.models import Item, Category
from customers.models import Customer

def test_kitchen_system():
    """Test the complete kitchen system workflow"""
    print("🧪 Testing Kitchen System...")
    
    try:
        # 1. Create test data
        print("1. Creating test data...")
        
        # Create super admin
        super_admin, created = SuperAdmin.objects.get_or_create(
            username='testadmin',
            defaults={'email': 'admin@test.com'}
        )
        if created:
            super_admin.set_password('testpass123')
            super_admin.save()
            print("   ✅ Created SuperAdmin")
        
        # Create owner
        owner, created = Owner.objects.get_or_create(
            username='testowner',
            defaults={
                'super_admin': super_admin,
                'name': 'Test Owner',
                'email': 'owner@test.com'
            }
        )
        if created:
            owner.set_password('testpass123')
            owner.save()
            print("   ✅ Created Owner")
        
        # Create restaurant
        restaurant, created = Restaurant.objects.get_or_create(
            name='Test Restaurant',
            defaults={
                'owner': owner,
                'description': 'Test restaurant for kitchen system'
            }
        )
        if created:
            print("   ✅ Created Restaurant")
        
        # Create currency
        currency, created = Currency.objects.get_or_create(
            currency_code='USD',
            defaults={'exchange_rate': 1.0}
        )
        if created:
            print("   ✅ Created Currency")
        
        # Create branch
        branch, created = Branch.objects.get_or_create(
            name='Test Branch',
            defaults={
                'restaurant': restaurant,
                'address': '123 Test St',
                'phone': '123-456-7890',
                'currency': currency
            }
        )
        if created:
            print("   ✅ Created Branch")
        
        # Create category
        category, created = Category.objects.get_or_create(
            name='Test Category',
            defaults={'restaurant': restaurant}
        )
        if created:
            print("   ✅ Created Category")
        
        # Create item
        item, created = Item.objects.get_or_create(
            name='Test Item',
            defaults={
                'branch': branch,
                'category': category,
                'cost': 5.00,
                'price': 10.00
            }
        )
        if created:
            print("   ✅ Created Item")
        
        # Create customer
        customer, created = Customer.objects.get_or_create(
            username='testcustomer',
            defaults={
                'branch': branch,
                'name': 'Test Customer',
                'phone': '123-456-7890',
                'email': 'customer@test.com'
            }
        )
        if created:
            customer.set_password('testpass123')
            customer.save()
            print("   ✅ Created Customer")
        
        # Create user role
        user_role, created = UserRole.objects.get_or_create(
            name='Kitchen Staff',
            defaults={
                'branch': branch,
                'kitchen_display': True
            }
        )
        if created:
            print("   ✅ Created UserRole")
        
        # 2. Enable kitchen system
        print("\n2. Enabling kitchen system...")
        success, message = KitchenSystemService.enable_kitchen_system(branch.id)
        if success:
            print(f"   ✅ {message}")
        else:
            print(f"   ❌ {message}")
            return
        
        # 3. Create kitchen staff
        print("\n3. Creating kitchen staff...")
        staff_user, created = User.objects.get_or_create(
            username='teststaff',
            defaults={
                'branch': branch,
                'role': user_role,
                'name': 'Test Staff',
                'email': 'staff@test.com'
            }
        )
        if created:
            staff_user.set_password('testpass123')
            staff_user.save()
            print("   ✅ Created Staff User")
        
        # Get a kitchen station
        station = KitchenStation.objects.filter(branch=branch).first()
        if station:
            print(f"   ✅ Using station: {station.name}")
        
        # Create kitchen staff
        kitchen_staff, created = KitchenStaff.objects.get_or_create(
            user=staff_user,
            defaults={'station': station}
        )
        if created:
            print("   ✅ Created Kitchen Staff")
        
        # 4. Create an order
        print("\n4. Creating test order...")
        order = Order.objects.create(
            branch=branch,
            customer=customer,
            order_type='dining',
            total_amount=10.00
        )
        print(f"   ✅ Created Order #{order.order_id}")
        
        # Create order item
        order_item = OrderItem.objects.create(
            order=order,
            item=item,
            quantity=1,
            price=10.00
        )
        print(f"   ✅ Created Order Item")
        
        # 5. Check if kitchen order was created automatically
        print("\n5. Checking kitchen order creation...")
        try:
            kitchen_order = KitchenOrder.objects.get(order=order)
            print(f"   ✅ Kitchen Order created automatically: #{kitchen_order.id}")
            print(f"      Status: {kitchen_order.status}")
            print(f"      Priority: {kitchen_order.priority}")
            
            # Check kitchen order items
            kitchen_items = KitchenOrderItem.objects.filter(kitchen_order=kitchen_order)
            print(f"      Items: {kitchen_items.count()}")
            
            for item in kitchen_items:
                print(f"        - {item.order_item.item.name} -> Station: {item.station.name if item.station else 'None'}")
                
        except KitchenOrder.DoesNotExist:
            print("   ❌ Kitchen Order was not created automatically")
        
        # 6. Test kitchen system status
        print("\n6. Testing kitchen system status...")
        try:
            from kitchen.views import KitchenSystemViewSet
            # This would normally be done through the API, but we can check the data directly
            stations_count = KitchenStation.objects.filter(branch=branch, is_active=True).count()
            staff_count = KitchenStaff.objects.filter(station__branch=branch).count()
            active_orders = KitchenOrder.objects.filter(
                order__branch=branch,
                status__in=['pending', 'preparing']
            ).count()
            
            print(f"   ✅ Active Stations: {stations_count}")
            print(f"   ✅ Kitchen Staff: {staff_count}")
            print(f"   ✅ Active Orders: {active_orders}")
            
        except Exception as e:
            print(f"   ❌ Error checking status: {e}")
        
        # 7. Test workload
        print("\n7. Testing station workload...")
        try:
            workload = KitchenAssignmentService.get_station_workload(branch)
            print("   ✅ Station Workload:")
            for station_name, data in workload.items():
                print(f"      {station_name}: {data['total']} orders (pending: {data['pending']}, preparing: {data['preparing']})")
        except Exception as e:
            print(f"   ❌ Error checking workload: {e}")
        
        print("\n🎉 Kitchen System Test Completed Successfully!")
        print(f"📊 Summary:")
        print(f"   - Branch: {branch.name}")
        print(f"   - Kitchen Enabled: {branch.kitchen_enabled}")
        print(f"   - Stations: {KitchenStation.objects.filter(branch=branch).count()}")
        print(f"   - Staff: {KitchenStaff.objects.filter(station__branch=branch).count()}")
        print(f"   - Orders: {Order.objects.filter(branch=branch).count()}")
        print(f"   - Kitchen Orders: {KitchenOrder.objects.filter(order__branch=branch).count()}")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_kitchen_system()
