import csv
import io
from functools import wraps
from datetime import datetime, timezone, date, timedelta
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, jsonify, session, Response, send_file
)

def now_utc():
    return datetime.now(timezone.utc)
from models import (
    db, AdminUser, Gym, Customer, Order, Supplier,
    PurchaseBatch, Inventory, WastageLog, PricingConfig, AppNotification
)
from services.pricing import get_pricing_value
from services.qr_generator import generate_gym_qr_data_url, generate_qr_base64
from services.inventory import (
    calculate_wholesale_demand, execute_wholesale_purchase,
    record_wastage, get_or_create_inventory
)
from services.notifications import notify_admin, get_customer_notification_templates
from config import Config

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_id'):
            flash("Please log in to access the admin dashboard.", "warning")
            return redirect(url_for('admin.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin secure login page."""
    if session.get('admin_id'):
        return redirect(url_for('admin.dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        user = AdminUser.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['admin_id'] = user.id
            session['admin_username'] = user.username
            session['admin_name'] = user.full_name
            user.last_login = now_utc()
            db.session.commit()
            flash(f"Welcome back, {user.full_name}!", "success")
            
            next_url = request.args.get('next')
            return redirect(next_url or url_for('admin.dashboard'))
        else:
            flash("Invalid administrator credentials. Please check username and password.", "danger")
            
    return render_template('admin/login.html')


@admin_bp.route('/logout')
def logout():
    session.clear()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for('admin.login'))


@admin_bp.route('/')
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Main Admin Overview Dashboard."""
    today = date.today()
    
    # Overview KPI Metrics
    today_orders = Order.query.filter(db.func.date(Order.created_at) == today).count()
    total_customers = Customer.query.count()
    
    # Eggs ordered & total revenue from paid orders
    paid_orders = Order.query.filter_by(payment_status='PAID').all()
    total_eggs_ordered = sum(o.egg_quantity for o in paid_orders)
    total_revenue = sum(o.total_amount for o in paid_orders)
    
    paid_orders_count = len(paid_orders)
    pending_orders_count = Order.query.filter_by(payment_status='PENDING').count()
    delivered_orders_count = Order.query.filter_by(order_status='DELIVERED').count()
    
    # Wholesale requirement demand
    wholesale_info = calculate_wholesale_demand()
    
    # Financial estimates
    total_wholesale_cost = sum(b.total_cost for b in PurchaseBatch.query.all())
    total_wastage_loss = sum(w.total_loss for w in WastageLog.query.all())
    estimated_net_profit = round(total_revenue - total_wholesale_cost - total_wastage_loss, 2)
    
    # Recent orders
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(8).all()
    
    # Unread notifications
    notifications = AppNotification.query.order_by(AppNotification.created_at.desc()).limit(5).all()
    
    # Inventory
    inv = get_or_create_inventory()
    
    # Chart Data: Last 7 days sales
    days_labels = []
    daily_sales_data = []
    for i in range(6, -1, -1):
        target_day = today - timedelta(days=i)
        days_labels.append(target_day.strftime('%d %b'))
        day_rev = sum(
            o.total_amount for o in Order.query.filter(
                Order.payment_status == 'PAID',
                db.func.date(Order.created_at) == target_day
            ).all()
        )
        daily_sales_data.append(round(day_rev, 2))
        
    # Chart Data: Orders by Gym
    gyms = Gym.query.filter_by(is_active=True).all()
    gym_names = [g.name for g in gyms]
    gym_egg_counts = [g.total_eggs_delivered for g in gyms]
    
    return render_template(
        'admin/dashboard.html',
        today_orders=today_orders,
        total_customers=total_customers,
        total_eggs_ordered=total_eggs_ordered,
        total_revenue=total_revenue,
        paid_orders_count=paid_orders_count,
        pending_orders_count=pending_orders_count,
        delivered_orders_count=delivered_orders_count,
        wholesale_info=wholesale_info,
        estimated_net_profit=estimated_net_profit,
        recent_orders=recent_orders,
        notifications=notifications,
        inv=inv,
        days_labels=days_labels,
        daily_sales_data=daily_sales_data,
        gym_names=gym_names,
        gym_egg_counts=gym_egg_counts
    )


@admin_bp.route('/orders')
@admin_required
def orders():
    """Order Management with search, filtering, and quick actions."""
    status_filter = request.args.get('status', '').strip()
    payment_filter = request.args.get('payment', '').strip()
    gym_filter = request.args.get('gym_id', type=int)
    search_query = request.args.get('search', '').strip()
    
    query = Order.query
    
    if status_filter:
        query = query.filter_by(order_status=status_filter)
    if payment_filter:
        query = query.filter_by(payment_status=payment_filter)
    if gym_filter:
        query = query.filter_by(gym_id=gym_filter)
    if search_query:
        query = query.filter(
            (Order.order_code.ilike(f"%{search_query}%")) |
            (Order.customer_name.ilike(f"%{search_query}%")) |
            (Order.customer_phone.ilike(f"%{search_query}%")) |
            (Order.transaction_id.ilike(f"%{search_query}%"))
        )
        
    orders_list = query.order_by(Order.created_at.desc()).all()
    all_gyms = Gym.query.order_by(Gym.name).all()
    
    return render_template(
        'admin/orders.html',
        orders=orders_list,
        all_gyms=all_gyms,
        current_status=status_filter,
        current_payment=payment_filter,
        current_gym=gym_filter,
        search_query=search_query
    )


@admin_bp.route('/orders/<int:order_id>/status', methods=['POST'])
@admin_required
def update_order_status(order_id):
    """Admin action to update order fulfillment or payment status."""
    order = Order.query.filter_by(id=order_id).first_or_404()
    new_status = request.form.get('order_status')
    new_payment = request.form.get('payment_status')
    admin_notes = request.form.get('admin_notes')
    
    inv = get_or_create_inventory()
    
    if new_status:
        # If moving to delivered, update inventory distribution
        if new_status in ['DELIVERED'] and order.order_status != 'DELIVERED':
            inv.current_stock = max(0, inv.current_stock - order.egg_quantity)
            inv.allocated_stock = max(0, inv.allocated_stock - order.egg_quantity)
            inv.total_distributed += order.egg_quantity
        elif new_status == 'CANCELLED' and order.order_status in ['EGGS_PURCHASED', 'READY_FOR_COLLECTION']:
            # Release allocated stock back to current available stock
            inv.allocated_stock = max(0, inv.allocated_stock - order.egg_quantity)
            
        order.order_status = new_status
        
    if new_payment:
        order.payment_status = new_payment
        if new_payment == 'PAID' and not order.payment_verified_at:
            order.payment_verified_at = now_utc()
            
    if admin_notes is not None:
        order.admin_notes = admin_notes
        
    db.session.commit()
    flash(f"Order #{order.order_code} updated successfully.", "success")
    return redirect(request.referrer or url_for('admin.orders'))


@admin_bp.route('/orders/<int:order_id>/view')
@admin_required
def view_order_modal(order_id):
    """Returns order details and WhatsApp templates."""
    order = Order.query.filter_by(id=order_id).first_or_404()
    templates = get_customer_notification_templates(order)
    return jsonify({
        'status': 'success',
        'order': {
            'id': order.id,
            'code': order.order_code,
            'customer_name': order.customer_name,
            'customer_phone': order.customer_phone,
            'customer_email': order.customer_email,
            'gym_name': order.gym.name if order.gym else 'N/A',
            'delivery_type': order.delivery_type,
            'delivery_address': order.delivery_address,
            'egg_quantity': order.egg_quantity,
            'package_type': order.package_type,
            'price_per_egg': order.price_per_egg,
            'eggs_subtotal': order.eggs_subtotal,
            'delivery_charge': order.delivery_charge,
            'total_amount': order.total_amount,
            'preferred_date': order.preferred_date.strftime('%d %b %Y'),
            'preferred_time_slot': order.preferred_time_slot,
            'payment_status': order.payment_status,
            'payment_method': order.payment_method,
            'transaction_id': order.transaction_id or 'N/A',
            'order_status': order.order_status,
            'created_at': order.created_at.strftime('%d %b %Y, %I:%M %p'),
            'customer_notes': order.customer_notes or '',
            'admin_notes': order.admin_notes or ''
        },
        'whatsapp': templates
    })


@admin_bp.route('/orders/export')
@admin_required
def export_orders():
    """Generates CSV export of orders for accounting/Excel."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        'Order ID', 'Date', 'Customer Name', 'Phone', 'Gym',
        'Delivery Type', 'Quantity', 'Price/Egg', 'Delivery Fee',
        'Total Amount', 'Payment Status', 'Transaction ID', 'Order Status'
    ])
    
    orders_list = Order.query.order_by(Order.created_at.desc()).all()
    for o in orders_list:
        writer.writerow([
            o.order_code,
            o.created_at.strftime('%Y-%m-%d %H:%M'),
            o.customer_name,
            o.customer_phone,
            o.gym.name if o.gym else 'None',
            o.delivery_type,
            o.egg_quantity,
            o.price_per_egg,
            o.delivery_charge,
            o.total_amount,
            o.payment_status,
            o.transaction_id or '',
            o.order_status
        ])
        
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=eggify_orders_export.csv"}
    )


@admin_bp.route('/wholesale')
@admin_required
def wholesale():
    """Wholesale Supplier & Demand Management Engine."""
    demand = calculate_wholesale_demand()
    suppliers = Supplier.query.order_by(Supplier.price_per_egg.asc()).all()
    recent_batches = PurchaseBatch.query.order_by(PurchaseBatch.created_at.desc()).limit(10).all()
    
    return render_template(
        'admin/wholesale.html',
        demand=demand,
        suppliers=suppliers,
        recent_batches=recent_batches
    )


@admin_bp.route('/wholesale/purchase', methods=['POST'])
@admin_required
def execute_purchase():
    """Executes a wholesale purchase batch."""
    supplier_id = request.form.get('supplier_id', type=int)
    quantity = request.form.get('quantity', type=int)
    price_per_egg = request.form.get('price_per_egg', type=float)
    invoice_number = request.form.get('invoice_number', '').strip()
    notes = request.form.get('notes', '').strip()
    
    try:
        batch = execute_wholesale_purchase(supplier_id, quantity, price_per_egg, invoice_number, notes)
        flash(f"Batch #{batch.batch_code} recorded! {quantity} eggs added to inventory.", "success")
    except Exception as e:
        flash(f"Failed to record batch: {str(e)}", "danger")
        
    return redirect(url_for('admin.wholesale'))


@admin_bp.route('/wholesale/slip/<int:batch_id>')
@admin_required
def wholesale_slip(batch_id):
    """Generates a clean, printable Wholesale Purchase Slip."""
    batch = PurchaseBatch.query.filter_by(id=batch_id).first_or_404()
    return render_template('admin/wholesale_slip.html', batch=batch)


@admin_bp.route('/inventory')
@admin_required
def inventory():
    """Inventory Management & Wastage Logs."""
    inv = get_or_create_inventory()
    wastage_logs = WastageLog.query.order_by(WastageLog.logged_at.desc()).limit(20).all()
    batches = PurchaseBatch.query.order_by(PurchaseBatch.created_at.desc()).limit(10).all()
    
    total_wastage_loss = sum(w.total_loss for w in WastageLog.query.all())
    
    return render_template(
        'admin/inventory.html',
        inv=inv,
        wastage_logs=wastage_logs,
        batches=batches,
        total_wastage_loss=total_wastage_loss
    )


@admin_bp.route('/inventory/wastage', methods=['POST'])
@admin_required
def log_wastage():
    """Logs damaged/cracked eggs."""
    quantity = request.form.get('quantity', type=int)
    reason = request.form.get('reason', 'Transit Damage')
    cost_per_egg = request.form.get('cost_per_egg', 4.80, type=float)
    notes = request.form.get('notes', '').strip()
    
    try:
        log = record_wastage(quantity, reason, cost_per_egg, notes)
        flash(f"Logged {quantity} damaged eggs. Loss: ₹{log.total_loss:.2f}", "warning")
    except Exception as e:
        flash(f"Error logging wastage: {str(e)}", "danger")
        
    return redirect(url_for('admin.inventory'))


@admin_bp.route('/gyms')
@admin_required
def gyms():
    """Gym Management & QR Code Generators."""
    gyms_list = Gym.query.order_by(Gym.created_at.desc()).all()
    return render_template('admin/gyms.html', gyms=gyms_list)


@admin_bp.route('/gyms/add', methods=['POST'])
@admin_required
def add_gym():
    """Adds a new Gym with unique code."""
    gym_code = request.form.get('gym_code', '').strip().upper()
    name = request.form.get('name', '').strip()
    address = request.form.get('address', '').strip()
    city = request.form.get('city', 'Bangalore').strip()
    contact_person = request.form.get('contact_person', '').strip()
    phone = request.form.get('phone', '').strip()
    notes = request.form.get('notes', '').strip()
    
    if not gym_code or not name:
        flash("Gym Code and Name are required.", "danger")
        return redirect(url_for('admin.gyms'))
        
    existing = Gym.query.filter_by(gym_code=gym_code).first()
    if existing:
        flash(f"Gym Code '{gym_code}' is already registered.", "danger")
        return redirect(url_for('admin.gyms'))
        
    gym = Gym(
        gym_code=gym_code,
        name=name,
        address=address,
        city=city,
        contact_person=contact_person,
        phone=phone,
        notes=notes,
        is_active=True
    )
    db.session.add(gym)
    db.session.commit()
    
    flash(f"Gym '{name}' ({gym_code}) registered successfully!", "success")
    return redirect(url_for('admin.gyms'))


@admin_bp.route('/gyms/<int:gym_id>/toggle', methods=['POST'])
@admin_required
def toggle_gym(gym_id):
    gym = Gym.query.filter_by(id=gym_id).first_or_404()
    gym.is_active = not gym.is_active
    db.session.commit()
    status_str = "activated" if gym.is_active else "deactivated"
    flash(f"Gym '{gym.name}' has been {status_str}.", "info")
    return redirect(url_for('admin.gyms'))


@admin_bp.route('/gyms/<int:gym_id>/poster')
@admin_required
def gym_poster(gym_id):
    """
    Renders high-resolution printable gym poster
    with EGGIFY branding, gym QR code, and scanning guide.
    """
    gym = Gym.query.filter_by(id=gym_id).first_or_404()
    base_url = request.host_url.rstrip('/')
    qr_data_url = generate_gym_qr_data_url(gym.gym_code, base_url)
    order_url = f"{base_url}/order?gym={gym.gym_code}"
    
    return render_template(
        'admin/gym_poster.html',
        gym=gym,
        qr_data_url=qr_data_url,
        order_url=order_url
    )


@admin_bp.route('/suppliers')
@admin_required
def suppliers():
    """Wholesale Supplier Directory & Price Comparison."""
    suppliers_list = Supplier.query.order_by(Supplier.price_per_egg.asc()).all()
    return render_template('admin/suppliers.html', suppliers=suppliers_list)


@admin_bp.route('/suppliers/add', methods=['POST'])
@admin_required
def add_supplier():
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    email = request.form.get('email', '').strip()
    location = request.form.get('location', '').strip()
    price_per_egg = request.form.get('price_per_egg', 4.80, type=float)
    min_order_qty = request.form.get('min_order_qty', 150, type=int)
    is_preferred = bool(request.form.get('is_preferred'))
    
    if is_preferred:
        # unset others
        Supplier.query.update({Supplier.is_preferred: False})
        
    supplier = Supplier(
        name=name,
        phone=phone,
        email=email,
        location=location,
        price_per_egg=price_per_egg,
        min_order_qty=min_order_qty,
        is_preferred=is_preferred,
        availability_status='AVAILABLE'
    )
    db.session.add(supplier)
    db.session.commit()
    flash(f"Supplier '{name}' added successfully.", "success")
    return redirect(url_for('admin.suppliers'))


@admin_bp.route('/suppliers/<int:supplier_id>/preferred', methods=['POST'])
@admin_required
def set_preferred_supplier(supplier_id):
    Supplier.query.update({Supplier.is_preferred: False})
    sup = Supplier.query.filter_by(id=supplier_id).first_or_404()
    sup.is_preferred = True
    db.session.commit()
    flash(f"'{sup.name}' set as preferred wholesale supplier.", "success")
    return redirect(url_for('admin.suppliers'))


@admin_bp.route('/customers')
@admin_required
def customers():
    """Customer CRM & Lifetime Value Tracking."""
    search = request.args.get('search', '').strip()
    query = Customer.query
    if search:
        query = query.filter(
            (Customer.name.ilike(f"%{search}%")) |
            (Customer.phone.ilike(f"%{search}%"))
        )
    customers_list = query.order_by(Customer.total_spent.desc()).all()
    return render_template('admin/customers.html', customers=customers_list, search=search)


@admin_bp.route('/analytics')
@admin_required
def analytics():
    """Financial & Performance Analytics Dashboard."""
    paid_orders = Order.query.filter_by(payment_status='PAID').all()
    
    total_revenue = sum(o.total_amount for o in paid_orders)
    wholesale_expense = sum(b.total_cost for b in PurchaseBatch.query.all())
    delivery_expense = sum(o.delivery_charge for o in paid_orders) * 0.7 # Approx cost
    packaging_expense = len(paid_orders) * 3.50 # ₹3.50 packaging per order
    wastage_loss = sum(w.total_loss for w in WastageLog.query.all())
    
    total_expenses = wholesale_expense + delivery_expense + packaging_expense + wastage_loss
    net_profit = round(total_revenue - total_expenses, 2)
    profit_margin = round((net_profit / total_revenue * 100), 1) if total_revenue > 0 else 0.0
    
    # Gym rankings
    gyms = Gym.query.all()
    gym_stats = []
    for g in gyms:
        g_orders = [o for o in paid_orders if o.gym_id == g.id]
        g_rev = sum(o.total_amount for o in g_orders)
        g_eggs = sum(o.egg_quantity for o in g_orders)
        gym_stats.append({
            'name': g.name,
            'code': g.gym_code,
            'orders_count': len(g_orders),
            'eggs_count': g_eggs,
            'revenue': g_rev
        })
    gym_stats.sort(key=lambda x: x['revenue'], reverse=True)
    
    return render_template(
        'admin/analytics.html',
        total_revenue=total_revenue,
        wholesale_expense=wholesale_expense,
        delivery_expense=delivery_expense,
        packaging_expense=packaging_expense,
        wastage_loss=wastage_loss,
        total_expenses=total_expenses,
        net_profit=net_profit,
        profit_margin=profit_margin,
        gym_stats=gym_stats
    )


@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    """Dynamic Pricing & System Settings."""
    if request.method == 'POST':
        keys = [
            'base_price_per_egg', 'pkg_6_price', 'pkg_12_price',
            'pkg_18_price', 'pkg_30_price', 'pkg_60_price',
            'home_delivery_base', 'home_delivery_per_km',
            'upi_id', 'upi_payee_name', 'support_phone'
        ]
        for key in keys:
            val = request.form.get(key)
            if val is not None:
                item = PricingConfig.query.filter_by(key=key).first()
                if not item:
                    item = PricingConfig(key=key, value=val)
                    db.session.add(item)
                else:
                    item.value = val
        db.session.commit()
        flash("Pricing & system settings updated successfully!", "success")
        return redirect(url_for('admin.settings'))
        
    configs = {c.key: c.value for c in PricingConfig.query.all()}
    return render_template('admin/settings.html', configs=configs, default_config=Config)
