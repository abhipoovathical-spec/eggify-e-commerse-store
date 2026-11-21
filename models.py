from datetime import datetime, timezone, date
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

def utcnow():
    return datetime.now(timezone.utc)

class AdminUser(db.Model):
    __tablename__ = 'admin_users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    role = db.Column(db.String(32), default='admin')  # admin, superadmin
    created_at = db.Column(db.DateTime, default=utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Gym(db.Model):
    __tablename__ = 'gyms'
    
    id = db.Column(db.Integer, primary_key=True)
    gym_code = db.Column(db.String(32), unique=True, nullable=False, index=True) # e.g. GYM001, GOLDS-BLR
    name = db.Column(db.String(150), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), default='Bangalore')
    contact_person = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    qr_filename = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    
    orders = db.relationship('Order', backref='gym', lazy='dynamic')

    @property
    def total_orders_count(self):
        return self.orders.filter_by(payment_status='PAID').count()

    @property
    def total_eggs_delivered(self):
        paid_orders = self.orders.filter_by(payment_status='PAID').all()
        return sum(order.egg_quantity for order in paid_orders)


class Customer(db.Model):
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), nullable=True)
    primary_gym_id = db.Column(db.Integer, db.ForeignKey('gyms.id'), nullable=True)
    total_orders = db.Column(db.Integer, default=0)
    total_eggs = db.Column(db.Integer, default=0)
    total_spent = db.Column(db.Float, default=0.0)
    last_order_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    
    primary_gym = db.relationship('Gym', backref='customers')
    orders = db.relationship('Order', backref='customer', lazy='dynamic')


class Supplier(db.Model):
    __tablename__ = 'suppliers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    contact_person = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    location = db.Column(db.String(255), nullable=False)
    price_per_egg = db.Column(db.Float, nullable=False, default=4.80)
    min_order_qty = db.Column(db.Integer, default=150) # MOQ
    availability_status = db.Column(db.String(32), default='AVAILABLE') # AVAILABLE, LOW_STOCK, UNAVAILABLE
    is_preferred = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    purchase_batches = db.relationship('PurchaseBatch', backref='supplier', lazy='dynamic')


class PurchaseBatch(db.Model):
    __tablename__ = 'purchase_batches'
    
    id = db.Column(db.Integer, primary_key=True)
    batch_code = db.Column(db.String(64), unique=True, nullable=False) # e.g. PUR-20261120-001
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    total_eggs = db.Column(db.Integer, nullable=False)
    price_per_egg = db.Column(db.Float, nullable=False)
    total_cost = db.Column(db.Float, nullable=False)
    purchase_date = db.Column(db.Date, default=date.today)
    invoice_number = db.Column(db.String(64), nullable=True)
    status = db.Column(db.String(32), default='RECEIVED') # ORDERED, RECEIVED, CANCELLED
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    
    orders = db.relationship('Order', backref='purchase_batch', lazy='dynamic')


class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_code = db.Column(db.String(40), unique=True, nullable=False, index=True) # e.g. EGG-202611-1001
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    customer_name = db.Column(db.String(120), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False, index=True)
    customer_email = db.Column(db.String(120), nullable=True)
    
    gym_id = db.Column(db.Integer, db.ForeignKey('gyms.id'), nullable=True)
    delivery_type = db.Column(db.String(32), default='gym_pickup') # 'gym_pickup' or 'home_delivery'
    delivery_address = db.Column(db.Text, nullable=True)
    delivery_distance_km = db.Column(db.Float, default=0.0)
    
    egg_quantity = db.Column(db.Integer, nullable=False)
    package_type = db.Column(db.String(32), default='custom') # 6, 12, 18, 30, 60, custom
    price_per_egg = db.Column(db.Float, nullable=False)
    eggs_subtotal = db.Column(db.Float, nullable=False)
    delivery_charge = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)
    
    preferred_date = db.Column(db.Date, nullable=False)
    preferred_time_slot = db.Column(db.String(50), default='Morning (6 AM - 9 AM)')
    
    # Payment fields
    payment_method = db.Column(db.String(32), default='UPI') # UPI, GPAY, PHONEPE, CARD
    payment_status = db.Column(db.String(32), default='PENDING', index=True) # PENDING, PAID, FAILED, REFUNDED
    transaction_id = db.Column(db.String(100), nullable=True) # UPI UTR / Gateway Ref
    payment_verified_at = db.Column(db.DateTime, nullable=True)
    
    # Fulfillment tracking stages
    # 1. ORDER_RECEIVED
    # 2. PAYMENT_CONFIRMED
    # 3. WHOLESALE_PENDING
    # 4. EGGS_PURCHASED
    # 5. READY_FOR_COLLECTION
    # 6. DELIVERED
    # CANCELLED
    order_status = db.Column(db.String(40), default='ORDER_RECEIVED', index=True)
    
    batch_id = db.Column(db.Integer, db.ForeignKey('purchase_batches.id'), nullable=True)
    
    customer_notes = db.Column(db.Text, nullable=True)
    admin_notes = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    @property
    def status_badge_class(self):
        mapping = {
            'ORDER_RECEIVED': 'bg-amber-100 text-amber-800 border-amber-300',
            'PAYMENT_CONFIRMED': 'bg-blue-100 text-blue-800 border-blue-300',
            'WHOLESALE_PENDING': 'bg-purple-100 text-purple-800 border-purple-300',
            'EGGS_PURCHASED': 'bg-indigo-100 text-indigo-800 border-indigo-300',
            'READY_FOR_COLLECTION': 'bg-teal-100 text-teal-800 border-teal-300',
            'DELIVERED': 'bg-emerald-100 text-emerald-800 border-emerald-300',
            'CANCELLED': 'bg-rose-100 text-rose-800 border-rose-300'
        }
        return mapping.get(self.order_status, 'bg-gray-100 text-gray-800')

    @property
    def status_human_label(self):
        mapping = {
            'ORDER_RECEIVED': 'Order Received',
            'PAYMENT_CONFIRMED': 'Payment Confirmed',
            'WHOLESALE_PENDING': 'Wholesale Pending',
            'EGGS_PURCHASED': 'Eggs Purchased',
            'READY_FOR_COLLECTION': 'Ready for Collection',
            'DELIVERED': 'Delivered / Collected',
            'CANCELLED': 'Cancelled / Refunded'
        }
        return mapping.get(self.order_status, self.order_status)


class Inventory(db.Model):
    __tablename__ = 'inventory'
    
    id = db.Column(db.Integer, primary_key=True)
    total_purchased = db.Column(db.Integer, default=0)
    current_stock = db.Column(db.Integer, default=0) # Available in warehouse/holding
    allocated_stock = db.Column(db.Integer, default=0) # Reserved for confirmed orders
    damaged_stock = db.Column(db.Integer, default=0) # Wastage/broken
    total_distributed = db.Column(db.Integer, default=0) # Successfully handed to customers
    last_updated = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)


class WastageLog(db.Model):
    __tablename__ = 'wastage_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    cost_per_egg = db.Column(db.Float, nullable=False, default=4.80)
    total_loss = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(100), nullable=False) # 'Transit Damage', 'Spoiled/Cracked', 'Handling'
    notes = db.Column(db.Text, nullable=True)
    logged_at = db.Column(db.DateTime, default=utcnow)


class PricingConfig(db.Model):
    __tablename__ = 'pricing_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    value = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)


class AppNotification(db.Model):
    __tablename__ = 'app_notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='order') # order, wholesale, inventory, alert
    is_read = db.Column(db.Boolean, default=False)
    link = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)
