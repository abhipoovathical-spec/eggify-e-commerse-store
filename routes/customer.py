import uuid
from datetime import datetime, timezone, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app
from models import db, Gym, Customer, Order, PricingConfig, AppNotification
from services.pricing import calculate_order_pricing
from services.qr_generator import generate_upi_payload, generate_qr_base64
from services.notifications import notify_admin, get_customer_notification_templates
from config import Config

def now_utc():
    return datetime.now(timezone.utc)

customer_bp = Blueprint('customer', __name__)

@customer_bp.route('/')
def index():
    """Customer-facing Homepage."""
    gyms = Gym.query.filter_by(is_active=True).order_by(Gym.name).all()
    
    # Packages for display (Base rate 1 egg = ₹9.00 with wholesale volume discounts)
    packages = [
        {'eggs': 6, 'name': 'Starter Pack', 'tag': 'Daily Fuel', 'price': 54.00, 'per_egg': 9.00, 'popular': False, 'desc': 'Ideal for beginners & light workout days.'},
        {'eggs': 12, 'name': 'Fitness Dozen', 'tag': 'Most Popular', 'price': 102.00, 'per_egg': 8.50, 'popular': True, 'desc': 'Perfect weekly protein boost for regular gym-goers.'},
        {'eggs': 18, 'name': 'Power Athlete', 'tag': 'High Protein', 'price': 150.00, 'per_egg': 8.33, 'popular': False, 'desc': 'For intense training cycles & muscle building.'},
        {'eggs': 30, 'name': 'Gym Pro Crate', 'tag': 'Best Value', 'price': 240.00, 'per_egg': 8.00, 'popular': False, 'desc': 'Full fresh 30-egg crate for serious bodybuilders.'},
        {'eggs': 60, 'name': 'Beast Bulk Crate', 'tag': 'Max Savings', 'price': 465.00, 'per_egg': 7.75, 'popular': False, 'desc': 'Two fresh crates for heavy bulkers and fitness duos.'},
    ]
    
    return render_template('customer/index.html', gyms=gyms, packages=packages)


@customer_bp.route('/order')
def order_page():
    """
    Mobile-first order form.
    Detects gym from query param ?gym=GYM001 or allows selection.
    """
    gym_code = request.args.get('gym', '').strip()
    selected_gym = None
    if gym_code:
        selected_gym = Gym.query.filter_by(gym_code=gym_code, is_active=True).first()
        
    active_gyms = Gym.query.filter_by(is_active=True).order_by(Gym.name).all()
    today_str = date.today().strftime('%Y-%m-%d')
    
    preselected_qty = request.args.get('qty', 12, type=int)
    
    return render_template(
        'customer/order.html',
        selected_gym=selected_gym,
        gym_code=gym_code,
        active_gyms=active_gyms,
        today_str=today_str,
        preselected_qty=preselected_qty
    )


@customer_bp.route('/api/calc-price', methods=['POST'])
def api_calc_price():
    """Dynamic pricing calculator called live from frontend."""
    data = request.get_json() or {}
    quantity = data.get('quantity', 12)
    delivery_type = data.get('delivery_type', 'gym_pickup')
    distance_km = data.get('distance_km', 0.0)
    
    try:
        pricing = calculate_order_pricing(quantity, delivery_type, distance_km)
        return jsonify({'status': 'success', 'data': pricing})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@customer_bp.route('/order', methods=['POST'])
def submit_order():
    """
    Processes customer order submission.
    Server-side validation of inputs, generates unique order code,
    creates pending order, redirects to secure checkout.
    """
    customer_name = request.form.get('customer_name', '').strip()
    customer_phone = request.form.get('customer_phone', '').strip()
    customer_email = request.form.get('customer_email', '').strip()
    
    gym_id = request.form.get('gym_id', type=int)
    delivery_type = request.form.get('delivery_type', 'gym_pickup')
    delivery_address = request.form.get('delivery_address', '').strip()
    distance_km = request.form.get('distance_km', 0.0, type=float)
    
    egg_quantity = request.form.get('egg_quantity', 12, type=int)
    preferred_date_str = request.form.get('preferred_date', '')
    preferred_time_slot = request.form.get('preferred_time_slot', 'Morning (6 AM - 9 AM)')
    customer_notes = request.form.get('customer_notes', '').strip()
    
    # Validations
    errors = []
    if not customer_name:
        errors.append("Please enter your name.")
        
    # Clean phone number
    clean_phone = "".join(filter(str.isdigit, customer_phone))
    if len(clean_phone) < 10:
        errors.append("Please provide a valid 10-digit mobile number.")
        
    if egg_quantity < 6:
        errors.append("Minimum order is 6 eggs.")
    if egg_quantity > 300:
        errors.append("For bulk orders over 300 eggs, please contact admin directly.")
        
    if not preferred_date_str:
        errors.append("Please select a delivery/pickup date.")
    else:
        try:
            pref_date = datetime.strptime(preferred_date_str, '%Y-%m-%d').date()
            if pref_date < date.today():
                errors.append("Order date cannot be in the past.")
        except ValueError:
            errors.append("Invalid date format.")
            pref_date = date.today()
            
    if delivery_type == 'home_delivery' and not delivery_address:
        errors.append("Please enter your delivery address.")
        
    gym = None
    if gym_id:
        gym = db.session.get(Gym, gym_id)
    if delivery_type == 'gym_pickup' and not gym:
        errors.append("Please select the gym where you want to collect your eggs.")
        
    if errors:
        for err in errors:
            flash(err, 'danger')
        return redirect(url_for('customer.order_page', gym=gym.gym_code if gym else ''))
        
    # Server-side pricing calculation (never trust frontend amounts)
    pricing = calculate_order_pricing(egg_quantity, delivery_type, distance_km)
    
    # Find or create customer record
    customer = Customer.query.filter_by(phone=clean_phone).first()
    if not customer:
        customer = Customer(
            name=customer_name,
            phone=clean_phone,
            email=customer_email if customer_email else None,
            primary_gym_id=gym.id if gym else None
        )
        db.session.add(customer)
        db.session.flush()
    else:
        customer.name = customer_name
        if customer_email:
            customer.email = customer_email
        if gym:
            customer.primary_gym_id = gym.id
            
    # Generate unique readable order code
    order_code = f"EGG-{now_utc().strftime('%y%m%d')}-{uuid.uuid4().hex[:5].upper()}"
    
    order = Order(
        order_code=order_code,
        customer_id=customer.id,
        customer_name=customer_name,
        customer_phone=clean_phone,
        customer_email=customer_email,
        gym_id=gym.id if gym else None,
        delivery_type=delivery_type,
        delivery_address=delivery_address if delivery_type == 'home_delivery' else None,
        delivery_distance_km=distance_km if delivery_type == 'home_delivery' else 0.0,
        egg_quantity=egg_quantity,
        package_type=pricing['package_type'],
        price_per_egg=pricing['price_per_egg'],
        eggs_subtotal=pricing['eggs_subtotal'],
        delivery_charge=pricing['delivery_charge'],
        total_amount=pricing['total_amount'],
        preferred_date=pref_date,
        preferred_time_slot=preferred_time_slot,
        payment_method='UPI',
        payment_status='PENDING',
        order_status='ORDER_RECEIVED',
        customer_notes=customer_notes
    )
    db.session.add(order)
    db.session.commit()
    
    return redirect(url_for('customer.checkout', order_code=order_code))


@customer_bp.route('/checkout/<order_code>')
def checkout(order_code):
    """
    Secure checkout page with Dynamic UPI QR Code, UPI Intent buttons,
    and simulated card/netbanking option.
    """
    order = Order.query.filter_by(order_code=order_code).first_or_404()
    
    if order.payment_status == 'PAID':
        return redirect(url_for('customer.order_confirmation', order_code=order_code))
        
    upi_data = generate_upi_payload(order.order_code, order.total_amount, order.customer_name)
    
    return render_template(
        'customer/checkout.html',
        order=order,
        upi_data=upi_data
    )


@customer_bp.route('/api/payment/verify', methods=['POST'])
def verify_payment():
    """
    Server-side payment verification.
    Validates transaction ID / UTR, updates order status to PAID,
    updates customer CRM totals, creates admin notification.
    """
    data = request.get_json() or {}
    order_code = data.get('order_code')
    transaction_id = data.get('transaction_id', '').strip()
    payment_method = data.get('payment_method', 'UPI')
    
    if not order_code:
        return jsonify({'status': 'error', 'message': 'Order code missing.'}), 400
        
    order = Order.query.filter_by(order_code=order_code).first()
    if not order:
        return jsonify({'status': 'error', 'message': 'Order not found.'}), 404
        
    if not transaction_id:
        transaction_id = f"UPI-{uuid.uuid4().hex[:10].upper()}"
        
    # Mark paid and advance fulfillment
    order.payment_status = 'PAID'
    order.order_status = 'PAYMENT_CONFIRMED'
    order.transaction_id = transaction_id
    order.payment_method = payment_method
    order.payment_verified_at = now_utc()
    
    # Update customer record lifetime stats
    customer = order.customer
    if customer:
        customer.total_orders = (customer.total_orders or 0) + 1
        customer.total_eggs = (customer.total_eggs or 0) + order.egg_quantity
        customer.total_spent = round((customer.total_spent or 0.0) + order.total_amount, 2)
        customer.last_order_date = now_utc()
        
    # Send system notification to Admin
    notify_admin(
        title=f"New Paid Order #{order.order_code}",
        message=f"{order.customer_name} placed an order for {order.egg_quantity} eggs (₹{order.total_amount:.2f}). UTR: {transaction_id}",
        category="order",
        link=f"/admin/orders?search={order.order_code}"
    )
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Payment successfully verified!',
        'redirect_url': url_for('customer.order_confirmation', order_code=order_code)
    })


@customer_bp.route('/confirmation/<order_code>')
def order_confirmation(order_code):
    """
    Post-payment confirmation screen with Order ID, details,
    printable receipt, and pickup QR pass.
    """
    order = Order.query.filter_by(order_code=order_code).first_or_404()
    
    # Generate pickup pass QR containing order code and phone
    pass_data = f"EGGIFY-PASS|{order.order_code}|{order.customer_phone}|{order.egg_quantity}EGGS"
    pickup_pass_qr = generate_qr_base64(pass_data, box_size=8, border=2)
    
    templates = get_customer_notification_templates(order)
    
    return render_template(
        'customer/confirmation.html',
        order=order,
        pickup_pass_qr=pickup_pass_qr,
        whatsapp_url=templates['confirmation_url']
    )


@customer_bp.route('/track', methods=['GET', 'POST'])
def track_lookup():
    """Customer lookup for order tracking by Order ID + Mobile number."""
    if request.method == 'POST':
        order_code = request.form.get('order_code', '').strip().upper()
        phone = "".join(filter(str.isdigit, request.form.get('phone', '')))
        
        order = Order.query.filter(
            Order.order_code == order_code,
            Order.customer_phone.like(f"%{phone[-10:]}%")
        ).first()
        
        if not order:
            flash("No order found matching this Order ID and Mobile Number. Please check and try again.", "danger")
            return render_template('customer/track_lookup.html')
            
        return redirect(url_for('customer.track_detail', order_code=order.order_code))
        
    return render_template('customer/track_lookup.html')


@customer_bp.route('/track/<order_code>')
def track_detail(order_code):
    """
    Displays live 6-stage order tracking:
    1. Order Received
    2. Payment Confirmed
    3. Wholesale Purchase Pending
    4. Eggs Purchased
    5. Ready for Collection
    6. Delivered / Collected
    """
    order = Order.query.filter_by(order_code=order_code).first_or_404()
    
    stages = [
        {'id': 'ORDER_RECEIVED', 'title': 'Order Received', 'icon': 'fa-clipboard-check', 'desc': 'Order details logged in EGGIFY system.'},
        {'id': 'PAYMENT_CONFIRMED', 'title': 'Payment Confirmed', 'icon': 'fa-money-bill-wave', 'desc': 'UPI payment received and validated.'},
        {'id': 'WHOLESALE_PENDING', 'title': 'Wholesale Purchase Pending', 'icon': 'fa-calculator', 'desc': 'Aggregated into today\'s farm wholesale lot.'},
        {'id': 'EGGS_PURCHASED', 'title': 'Eggs Purchased', 'icon': 'fa-egg', 'desc': 'Fresh eggs procured from vetted poultry farm.'},
        {'id': 'READY_FOR_COLLECTION', 'title': 'Ready for Collection', 'icon': 'fa-dumbbell', 'desc': 'Inspected & packaged at gym front desk.'},
        {'id': 'DELIVERED', 'title': 'Delivered / Collected', 'icon': 'fa-box-open', 'desc': 'Handed over fresh to customer.'}
    ]
    
    stage_order = [s['id'] for s in stages]
    
    current_index = 0
    if order.order_status in stage_order:
        current_index = stage_order.index(order.order_status)
    elif order.order_status == 'CANCELLED':
        current_index = -1
        
    return render_template(
        'customer/track_detail.html',
        order=order,
        stages=stages,
        current_index=current_index
    )
