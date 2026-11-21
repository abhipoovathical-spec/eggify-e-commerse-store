from datetime import datetime, timezone, date, timedelta
from app import create_app
from models import (
    db, AdminUser, Gym, Customer, Supplier, Order,
    PurchaseBatch, Inventory, WastageLog, PricingConfig, AppNotification
)
from config import Config
from services.pricing import calculate_order_pricing

def now_utc():
    return datetime.now(timezone.utc)

app = create_app()

def seed_database():
    with app.app_context():
        print("🍳 Resetting and creating database tables...")
        db.drop_all()
        db.create_all()
        
        # 1. Admin User
        admin = AdminUser(
            username='admin',
            full_name='Aarav Sharma (EGGIFY Owner)',
            email='admin@eggify.fitness',
            role='superadmin'
        )
        admin.set_password('eggify@2026')
        db.session.add(admin)
        print("  ✓ Created Admin: 'admin' / 'eggify@2026'")
        
        # 2. Pricing Configuration (Base 1 egg = ₹9.00)
        configs = [
            ('base_price_per_egg', '9.00', 'Standard base price for a single fresh egg'),
            ('pkg_6_price', '54.00', 'Starter Pack (6 eggs) price'),
            ('pkg_12_price', '102.00', 'Fitness Dozen (12 eggs) price'),
            ('pkg_18_price', '150.00', 'Power Athlete (18 eggs) price'),
            ('pkg_30_price', '240.00', 'Gym Pro Crate (30 eggs) price'),
            ('pkg_60_price', '465.00', 'Beast Bulk Crate (60 eggs) price'),
            ('home_delivery_base', '30.00', 'Base home delivery charge for first 2 km'),
            ('home_delivery_per_km', '5.00', 'Additional charge per km after 2 km'),
            ('upi_id', 'eggify@okhdfcbank', 'Official Merchant UPI VPA'),
            ('upi_payee_name', 'EGGIFY Fresh Foods', 'Name displayed in UPI apps'),
            ('support_phone', '+91 98765 43210', 'Customer support WhatsApp/Phone'),
        ]
        for key, val, desc in configs:
            db.session.add(PricingConfig(key=key, value=val, description=desc))
        print("  ✓ Default pricing rules initialized")
        
        # 3. Gyms
        gyms_data = [
            Gym(gym_code='GYM-GOLDS', name="Gold's Gym - Indiranagar", address="100ft Road, 12th Main, Indiranagar", city="Bangalore", contact_person="Coach Vikram", phone="9876500001"),
            Gym(gym_code='GYM-CULT', name="Cult.fit Arena - Koramangala", address="80ft Road, 4th Block, Koramangala", city="Bangalore", contact_person="Trainer Rohit", phone="9876500002"),
            Gym(gym_code='GYM-ANYTIME', name="Anytime Fitness - HSR Layout", address="Sector 2, 27th Main, HSR Layout", city="Bangalore", contact_person="Desk Manager Priya", phone="9876500003"),
            Gym(gym_code='GYM-IRON', name="Iron Sanctuary Bodybuilding", address="ITPL Main Road, Whitefield", city="Bangalore", contact_person="Head Coach Dev", phone="9876500004"),
            Gym(gym_code='GYM-SNAP', name="Snap Fitness - Bellandur", address="Outer Ring Road, Green Glen Layout, Bellandur", city="Bangalore", contact_person="Manager Ananya", phone="9876500005"),
        ]
        for g in gyms_data:
            db.session.add(g)
        db.session.flush()
        print(f"  ✓ Added {len(gyms_data)} partner gyms with unique QR codes")
        
        # 4. Wholesale Suppliers
        sup1 = Supplier(
            name="Sri Lakshmi Poultry Farm & Hatcheries",
            contact_person="Ramesh Gowda",
            phone="9845012345",
            email="ramesh@slpoultry.in",
            location="Doddaballapur Poultry Belt, Bangalore Rural",
            price_per_egg=4.80,
            min_order_qty=150,
            is_preferred=True,
            availability_status='AVAILABLE',
            notes="Direct farm supplier. Delivers daily by 5:30 AM in hygienic crates."
        )
        sup2 = Supplier(
            name="Golden Yolk Agro Farms Pvt Ltd",
            contact_person="Kiran Kumar",
            phone="9845023456",
            email="sales@goldenyolk.com",
            location="Hoskote Industrial Area, Bangalore",
            price_per_egg=4.95,
            min_order_qty=210,
            is_preferred=False,
            availability_status='AVAILABLE',
            notes="Graded white eggs, UV-sanitized shells."
        )
        sup3 = Supplier(
            name="Sunrise Fresh Poultry Suppliers",
            contact_person="Manjunath Reddy",
            phone="9845034567",
            email="sunrise@agrofeed.net",
            location="Kolar Highway Junction",
            price_per_egg=5.10,
            min_order_qty=120,
            is_preferred=False,
            availability_status='AVAILABLE',
            notes="Fast backup supplier, provides 30-egg pulp trays."
        )
        db.session.add_all([sup1, sup2, sup3])
        db.session.flush()
        print("  ✓ Seeded wholesale suppliers with price benchmarking")
        
        # 5. Inventory Initialization
        inv = Inventory(
            total_purchased=600,
            current_stock=240,
            allocated_stock=120,
            damaged_stock=18,
            total_distributed=342
        )
        db.session.add(inv)
        
        # 6. Past Purchase Batch
        batch1 = PurchaseBatch(
            batch_code="PUR-20261118-001",
            supplier_id=sup1.id,
            total_eggs=600,
            price_per_egg=4.80,
            total_cost=2880.00,
            purchase_date=date.today() - timedelta(days=2),
            invoice_number="INV-SLP-4421",
            status="RECEIVED",
            notes="First bulk batch for Indiranagar & Koramangala gyms"
        )
        db.session.add(batch1)
        
        # 7. Wastage record
        wastage1 = WastageLog(
            quantity=18,
            cost_per_egg=4.80,
            total_loss=86.40,
            reason="Transit Damage (pothole on Outer Ring Road)",
            notes="Replaced for customer from reserve buffer."
        )
        db.session.add(wastage1)
        
        # 8. Sample Customers & Active Orders
        cust_data = [
            ("Karan Patel", "9876511111", "karan.p@gmail.com", gyms_data[0].id),
            ("Rahul Verma", "9876522222", "rahul.v@gmail.com", gyms_data[1].id),
            ("Sneha Iyer", "9876533333", "sneha.i@outlook.com", gyms_data[2].id),
            ("Arjun Nair", "9876544444", "arjun.nair@fitness.in", gyms_data[0].id),
            ("Meera Kapoor", "9876555555", "meera.k@gmail.com", gyms_data[3].id),
            ("Vikas Sharma", "9876566666", "vikas.s@techcorp.com", gyms_data[1].id),
            ("Rohan Deshmukh", "9876577777", "rohan.d@gmail.com", gyms_data[4].id),
        ]
        
        customers = []
        for name, phone, email, gym_id in cust_data:
            c = Customer(name=name, phone=phone, email=email, primary_gym_id=gym_id)
            db.session.add(c)
            customers.append(c)
        db.session.flush()
        
        # Orders representing the exact scenario from prompt + historical delivered orders:
        # Prompt example: Customer A: 12, Customer B: 30, Customer C: 18, Customer D: 24, Customer E: 36 -> Total 120 Eggs!
        active_sample_orders = [
            (customers[0], gyms_data[0], 12, 'gym_pickup', 'PAYMENT_CONFIRMED', 'WHOLESALE_PENDING', "Leave at front desk with Coach Vikram"),
            (customers[1], gyms_data[1], 30, 'gym_pickup', 'PAYMENT_CONFIRMED', 'WHOLESALE_PENDING', "In a sturdy crate please"),
            (customers[2], gyms_data[2], 18, 'home_delivery', 'PAYMENT_CONFIRMED', 'WHOLESALE_PENDING', "Flat 302, Green Glen Apt, HSR", 2.5),
            (customers[3], gyms_data[0], 24, 'gym_pickup', 'PAYMENT_CONFIRMED', 'WHOLESALE_PENDING', "Will collect after evening workout at 7 PM"),
            (customers[4], gyms_data[3], 36, 'gym_pickup', 'PAYMENT_CONFIRMED', 'WHOLESALE_PENDING', "High protein bulk phase"),
        ]
        
        for idx, item in enumerate(active_sample_orders):
            cust, gym, qty, del_type, pay_status, ord_status = item[0], item[1], item[2], item[3], item[4], item[5]
            notes = item[6]
            dist = item[7] if len(item) > 7 else 0.0
            
            pricing = calculate_order_pricing(qty, del_type, dist)
            order_code = f"EGG-261120-10{idx+1}"
            
            order = Order(
                order_code=order_code,
                customer_id=cust.id,
                customer_name=cust.name,
                customer_phone=cust.phone,
                customer_email=cust.email,
                gym_id=gym.id,
                delivery_type=del_type,
                delivery_address=notes if del_type == 'home_delivery' else None,
                delivery_distance_km=dist,
                egg_quantity=qty,
                package_type=pricing['package_type'],
                price_per_egg=pricing['price_per_egg'],
                eggs_subtotal=pricing['eggs_subtotal'],
                delivery_charge=pricing['delivery_charge'],
                total_amount=pricing['total_amount'],
                preferred_date=date.today() + timedelta(days=1),
                preferred_time_slot='Morning (6 AM - 9 AM)',
                payment_method='UPI',
                payment_status=pay_status,
                transaction_id=f"UPI{now_utc().strftime('%y%m%d')}00{idx+1}",
                payment_verified_at=now_utc() - timedelta(hours=idx+2),
                order_status=ord_status,
                customer_notes=notes,
                created_at=now_utc() - timedelta(hours=idx+2)
            )
            cust.total_orders = (cust.total_orders or 0) + 1
            cust.total_eggs = (cust.total_eggs or 0) + qty
            cust.total_spent = round((cust.total_spent or 0.0) + pricing['total_amount'], 2)
            cust.last_order_date = now_utc()
            db.session.add(order)
            
        # Add past delivered orders for rich charts & analytics
        past_delivered = [
            (customers[5], gyms_data[1], 60, 2, 'gym_pickup'),
            (customers[6], gyms_data[4], 30, 3, 'gym_pickup'),
            (customers[0], gyms_data[0], 30, 4, 'home_delivery', 3.0),
            (customers[1], gyms_data[1], 18, 5, 'gym_pickup'),
        ]
        
        for idx, p in enumerate(past_delivered):
            cust, gym, qty, days_ago, del_type = p[0], p[1], p[2], p[3], p[4]
            dist = p[5] if len(p) > 5 else 0.0
            pricing = calculate_order_pricing(qty, del_type, dist)
            past_order = Order(
                order_code=f"EGG-2611{15+idx}-09{idx+1}",
                customer_id=cust.id,
                customer_name=cust.name,
                customer_phone=cust.phone,
                customer_email=cust.email,
                gym_id=gym.id,
                delivery_type=del_type,
                delivery_address="Indiranagar 5th Cross" if del_type == 'home_delivery' else None,
                delivery_distance_km=dist,
                egg_quantity=qty,
                package_type=pricing['package_type'],
                price_per_egg=pricing['price_per_egg'],
                eggs_subtotal=pricing['eggs_subtotal'],
                delivery_charge=pricing['delivery_charge'],
                total_amount=pricing['total_amount'],
                preferred_date=date.today() - timedelta(days=days_ago),
                preferred_time_slot='Morning (6 AM - 9 AM)',
                payment_method='UPI',
                payment_status='PAID',
                transaction_id=f"UPIHIST26110{idx}",
                payment_verified_at=now_utc() - timedelta(days=days_ago),
                order_status='DELIVERED',
                created_at=now_utc() - timedelta(days=days_ago),
                batch_id=batch1.id
            )
            cust.total_orders = (cust.total_orders or 0) + 1
            cust.total_eggs = (cust.total_eggs or 0) + qty
            cust.total_spent = round((cust.total_spent or 0.0) + pricing['total_amount'], 2)
            db.session.add(past_order)
            
        # Notification
        notif = AppNotification(
            title="Wholesale Demand Aggregated",
            message="120 eggs required across 5 gym orders for tomorrow's fulfillment. Review supplier rates.",
            category="wholesale",
            link="/admin/wholesale"
        )
        db.session.add(notif)
        
        db.session.commit()
        print("✅ Database successfully seeded with full commercial dataset!")

if __name__ == '__main__':
    seed_database()
