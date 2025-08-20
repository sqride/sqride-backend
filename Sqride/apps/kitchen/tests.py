from django.test import TestCase
from django.utils import timezone
from restaurants.models import Restaurant, Branch, Currency
from accounts.models import Owner, SuperAdmin, UserRole, User
from .models import KitchenStation, KitchenOrder, KitchenOrderItem, KitchenDisplay, KitchenStaff
from .services import KitchenSystemService, KitchenAssignmentService
from orders.models import Order, OrderItem
from items.models import Item, Category
from customers.models import Customer

class KitchenSystemTestCase(TestCase):
    def setUp(self):
        # Create test data
        self.super_admin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123'
        )
        
        self.owner = Owner.objects.create(
            super_admin=self.super_admin,
            username='testowner',
            name='Test Owner',
            email='owner@test.com'
        )
        
        self.restaurant = Restaurant.objects.create(
            owner=self.owner,
            name='Test Restaurant',
            description='Test restaurant description'
        )
        
        self.currency = Currency.objects.create(
            currency_code='USD',
            exchange_rate=1.0
        )
        
        self.branch = Branch.objects.create(
            restaurant=self.restaurant,
            name='Test Branch',
            address='123 Test St',
            phone='123-456-7890',
            currency=self.currency
        )
        
        self.category = Category.objects.create(
            restaurant=self.restaurant,
            name='Test Category'
        )
        
        self.item = Item.objects.create(
            branch=self.branch,
            category=self.category,
            name='Test Item',
            cost=5.00,
            price=10.00
        )
        
        self.customer = Customer.objects.create(
            branch=self.branch,
            name='Test Customer',
            phone='123-456-7890',
            email='customer@test.com',
            username='testcustomer'
        )
        
        # Create a user role for testing
        self.user_role = UserRole.objects.create(
            name='Kitchen Staff',
            branch=self.branch,
            kitchen_display=True
        )

    def test_enable_kitchen_system(self):
        """Test enabling kitchen system for a branch"""
        success, message = KitchenSystemService.enable_kitchen_system(self.branch.id)
        
        self.assertTrue(success)
        self.assertEqual(message, "Kitchen system enabled successfully")
        
        # Refresh branch from database
        self.branch.refresh_from_db()
        self.assertTrue(self.branch.kitchen_enabled)
        self.assertIsNotNone(self.branch.kitchen_settings)
        
        # Check if default stations were created
        stations = KitchenStation.objects.filter(branch=self.branch)
        self.assertEqual(stations.count(), 4)  # 4 default stations
        
        # Check if default display was created
        displays = KitchenDisplay.objects.filter(branch=self.branch)
        self.assertEqual(displays.count(), 1)

    def test_disable_kitchen_system(self):
        """Test disabling kitchen system for a branch"""
        # First enable the system
        KitchenSystemService.enable_kitchen_system(self.branch.id)
        
        # Then disable it
        success, message = KitchenSystemService.disable_kitchen_system(self.branch.id)
        
        self.assertTrue(success)
        self.assertEqual(message, "Kitchen system disabled successfully")
        
        # Refresh branch from database
        self.branch.refresh_from_db()
        self.assertFalse(self.branch.kitchen_enabled)
        
        # Check if stations were deactivated
        stations = KitchenStation.objects.filter(branch=self.branch, is_active=True)
        self.assertEqual(stations.count(), 0)

    def test_kitchen_station_creation(self):
        """Test creating kitchen stations"""
        station = KitchenStation.objects.create(
            name='Test Station',
            branch=self.branch,
            description='Test station description'
        )
        
        self.assertEqual(station.name, 'Test Station')
        self.assertEqual(station.branch, self.branch)
        self.assertTrue(station.is_active)

    def test_kitchen_order_creation(self):
        """Test creating kitchen orders"""
        # Create a regular order first
        order = Order.objects.create(
            branch=self.branch,
            customer=self.customer,
            order_type='dining',
            total_amount=10.00
        )
        
        # Create order item
        order_item = OrderItem.objects.create(
            order=order,
            item=self.item,
            quantity=1,
            price=10.00
        )
        
        # Create kitchen order
        kitchen_order = KitchenOrder.objects.create(
            order=order,
            status='pending',
            priority=5
        )
        
        self.assertEqual(kitchen_order.order, order)
        self.assertEqual(kitchen_order.status, 'pending')
        self.assertEqual(kitchen_order.priority, 5)

    def test_kitchen_order_item_creation(self):
        """Test creating kitchen order items"""
        # Create kitchen order first
        order = Order.objects.create(
            branch=self.branch,
            customer=self.customer,
            order_type='dining',
            total_amount=10.00
        )
        
        order_item = OrderItem.objects.create(
            order=order,
            item=self.item,
            quantity=1,
            price=10.00
        )
        
        kitchen_order = KitchenOrder.objects.create(
            order=order,
            status='pending'
        )
        
        station = KitchenStation.objects.create(
            name='Test Station',
            branch=self.branch
        )
        
        kitchen_order_item = KitchenOrderItem.objects.create(
            kitchen_order=kitchen_order,
            order_item=order_item,
            station=station,
            status='pending'
        )
        
        self.assertEqual(kitchen_order_item.kitchen_order, kitchen_order)
        self.assertEqual(kitchen_order_item.order_item, order_item)
        self.assertEqual(kitchen_order_item.station, station)

    def test_kitchen_display_creation(self):
        """Test creating kitchen displays"""
        station = KitchenStation.objects.create(
            name='Test Station',
            branch=self.branch
        )
        
        display = KitchenDisplay.objects.create(
            branch=self.branch,
            name='Test Display',
            display_type='combined'
        )
        
        display.stations.add(station)
        
        self.assertEqual(display.branch, self.branch)
        self.assertEqual(display.stations.count(), 1)
        self.assertIn(station, display.stations.all())

    def test_kitchen_staff_management(self):
        """Test kitchen staff management"""
        # Create a user for staff using the correct method
        staff_user = User.objects.create_user(
            branch=self.branch,
            role=self.user_role,
            username='teststaff',
            name='Test Staff',
            email='staff@test.com',
            password='testpass123'
        )
        
        station = KitchenStation.objects.create(
            name='Test Station',
            branch=self.branch
        )
        
        staff = KitchenStaff.objects.create(
            user=staff_user,
            station=station,
            is_available=True
        )
        
        self.assertEqual(staff.user, staff_user)
        self.assertEqual(staff.station, station)
        self.assertTrue(staff.is_available)

    def test_kitchen_settings_update(self):
        """Test updating kitchen settings"""
        # First enable the system
        KitchenSystemService.enable_kitchen_system(self.branch.id)
        
        # Update settings
        new_settings = {
            'auto_assign_stations': False,
            'default_preparation_time': 20,
            'custom_setting': 'test_value'
        }
        
        success, message = KitchenSystemService.update_kitchen_settings(
            self.branch.id, 
            new_settings
        )
        
        self.assertTrue(success)
        self.assertEqual(message, "Kitchen settings updated successfully")
        
        # Refresh branch and check settings
        self.branch.refresh_from_db()
        self.assertFalse(self.branch.kitchen_settings['auto_assign_stations'])
        self.assertEqual(self.branch.kitchen_settings['default_preparation_time'], 20)
        self.assertEqual(self.branch.kitchen_settings['custom_setting'], 'test_value')

    def test_kitchen_system_status(self):
        """Test getting kitchen system status"""
        # First enable the system
        KitchenSystemService.enable_kitchen_system(self.branch.id)
        
        # Create some test data
        station = KitchenStation.objects.create(
            name='Test Station',
            branch=self.branch
        )
        
        staff_user = User.objects.create_user(
            branch=self.branch,
            role=self.user_role,
            username='teststaff2',
            name='Test Staff 2',
            email='staff2@test.com',
            password='testpass123'
        )
        
        KitchenStaff.objects.create(
            user=staff_user,
            station=station
        )
        
        # Check status
        self.branch.refresh_from_db()
        self.assertTrue(self.branch.kitchen_enabled)
        self.assertIsNotNone(self.branch.kitchen_settings)
        
        # Check if stations and staff exist
        stations_count = KitchenStation.objects.filter(branch=self.branch, is_active=True).count()
        staff_count = KitchenStaff.objects.filter(station__branch=self.branch).count()
        
        self.assertGreater(stations_count, 0)
        self.assertGreater(staff_count, 0)
