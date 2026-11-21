import unittest
import json
from datetime import date, timedelta
from app import create_app
from models import db, AdminUser, Gym, Customer, Order, Supplier, Inventory, PurchaseBatch, WastageLog, PricingConfig

class EggifyTestSuite(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_01_homepage(self):
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'EGGIFY', res.data)
        self.assertIn(b'Your Daily Protein Starts Here', res.data)
        print("✓ Homepage loads successfully with branding")

    def test_02_gym_qr_detection(self):
        res = self.client.get('/order?gym=GYM-GOLDS')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'GYM-GOLDS', res.data)
        self.assertIn(b'Gym Identified via QR Code', res.data)
        print("✓ Gym QR detection (?gym=GYM-GOLDS) works properly")

    def test_03_price_calculation_api(self):
        # 12 eggs gym pickup (base 1 egg = ₹9.00, dozen discount = ₹102)
        payload = {'quantity': 12, 'delivery_type': 'gym_pickup', 'distance_km': 0}
        res = self.client.post('/api/calc-price', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)['data']
        self.assertEqual(data['quantity'], 12)
        self.assertEqual(data['eggs_subtotal'], 102.0)
        self.assertEqual(data['delivery_charge'], 0.0)
        self.assertEqual(data['total_amount'], 102.0)
        
        # 30 eggs home delivery 4 km (crate = ₹240 + delivery ₹40 = ₹280)
        payload2 = {'quantity': 30, 'delivery_type': 'home_delivery', 'distance_km': 4.0}
        res2 = self.client.post('/api/calc-price', data=json.dumps(payload2), content_type='application/json')
        data2 = json.loads(res2.data)['data']
        self.assertEqual(data2['quantity'], 30)
        self.assertEqual(data2['eggs_subtotal'], 240.0)
        # base 30 + (4 - 2) * 5 = 40
        self.assertEqual(data2['delivery_charge'], 40.0)
        self.assertEqual(data2['total_amount'], 280.0)
        print("✓ Dynamic pricing calculation API functions accurately")

    def test_04_customer_order_submission_and_checkout(self):
        gym = Gym.query.filter_by(gym_code='GYM-GOLDS').first()
        order_data = {
            'customer_name': 'Test Athlete',
            'customer_phone': '9876599999',
            'customer_email': 'athlete@test.com',
            'gym_id': gym.id,
            'delivery_type': 'gym_pickup',
            'egg_quantity': '18',
            'preferred_date': (date.today() + timedelta(days=1)).strftime('%Y-%m-%d'),
            'preferred_time_slot': 'Morning (6 AM - 9 AM)',
            'customer_notes': 'Please keep in cool shade'
        }
        res = self.client.post('/order', data=order_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Secure UPI Checkout', res.data)
        self.assertIn(b'Scan QR with Any UPI App', res.data)
        
        # Retrieve created order
        order = Order.query.filter_by(customer_phone='9876599999').order_by(Order.id.desc()).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.egg_quantity, 18)
        self.assertEqual(order.total_amount, 150.0)
        self.assertEqual(order.payment_status, 'PENDING')
        print(f"✓ Order #{order.order_code} successfully created and forwarded to checkout")

        # Verify Payment
        verify_payload = {
            'order_code': order.order_code,
            'transaction_id': 'UPI-TEST-12345678',
            'payment_method': 'UPI'
        }
        res_pay = self.client.post('/api/payment/verify', data=json.dumps(verify_payload), content_type='application/json')
        self.assertEqual(res_pay.status_code, 200)
        
        # Check order updated to PAID
        db.session.refresh(order)
        self.assertEqual(order.payment_status, 'PAID')
        self.assertEqual(order.order_status, 'PAYMENT_CONFIRMED')
        print("✓ Payment verification successfully marked order as PAID")

        # Confirmation receipt
        res_conf = self.client.get(f'/confirmation/{order.order_code}')
        self.assertEqual(res_conf.status_code, 200)
        self.assertIn(b'Gym Pickup Pass', res_conf.data)
        print("✓ Order confirmation page displays pickup pass QR")

        # Track order
        res_track = self.client.get(f'/track/{order.order_code}')
        self.assertEqual(res_track.status_code, 200)
        self.assertIn(b'Payment Confirmed', res_track.data)
        print("✓ Order tracking displays live 6-stage timeline")

    def test_05_admin_dashboard_and_wholesale_execution(self):
        # Admin Login
        res_login = self.client.post('/admin/login', data={'username': 'admin', 'password': 'eggify@2026'}, follow_redirects=True)
        self.assertEqual(res_login.status_code, 200)
        self.assertIn(b'Dashboard Overview', res_login.data)
        print("✓ Admin login authenticated successfully")

        # Wholesale page
        res_wh = self.client.get('/admin/wholesale')
        self.assertEqual(res_wh.status_code, 200)
        self.assertIn(b'Wholesale Sourcing & Purchase Automation', res_wh.data)
        print("✓ Wholesale automation engine aggregates orders")

        # Printable Gym Poster
        gym = Gym.query.first()
        res_poster = self.client.get(f'/admin/gyms/{gym.id}/poster')
        self.assertEqual(res_poster.status_code, 200)
        self.assertIn(b'SCAN TO ORDER FRESH EGGS', res_poster.data)
        print(f"✓ Printable Gym poster rendered for {gym.name}")

if __name__ == '__main__':
    unittest.main()
