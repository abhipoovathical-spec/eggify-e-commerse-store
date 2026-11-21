from datetime import datetime, timezone
from models import db, Order, Supplier, Inventory, PurchaseBatch, WastageLog, AppNotification
from config import Config

def now_utc():
    return datetime.now(timezone.utc)

def get_or_create_inventory():
    inv = Inventory.query.first()
    if not inv:
        inv = Inventory(
            total_purchased=0,
            current_stock=0,
            allocated_stock=0,
            damaged_stock=0,
            total_distributed=0
        )
        db.session.add(inv)
        db.session.commit()
    return inv

def calculate_wholesale_demand():
    """
    Aggregates all confirmed/paid customer orders that haven't been purchased yet.
    Avoids counting cancelled, unpaid or already purchased orders.
    """
    # Active orders that need eggs to be sourced:
    # Payment is confirmed, but wholesale purchase hasn't happened yet.
    eligible_orders = Order.query.filter(
        Order.payment_status == 'PAID',
        Order.order_status.in_(['ORDER_RECEIVED', 'PAYMENT_CONFIRMED', 'WHOLESALE_PENDING'])
    ).all()
    
    total_orders_count = len(eligible_orders)
    total_eggs_required = sum(o.egg_quantity for o in eligible_orders)
    expected_sales_revenue = sum(o.eggs_subtotal for o in eligible_orders)
    
    inv = get_or_create_inventory()
    available_stock = max(0, inv.current_stock - inv.allocated_stock)
    
    # Net additional eggs to buy
    additional_to_purchase = max(0, total_eggs_required - available_stock)
    
    # Check suppliers
    suppliers = Supplier.query.filter_by(availability_status='AVAILABLE').order_by(Supplier.price_per_egg.asc()).all()
    preferred_supplier = Supplier.query.filter_by(is_preferred=True).first()
    
    if not preferred_supplier and suppliers:
        preferred_supplier = suppliers[0]
        
    cost_rate = preferred_supplier.price_per_egg if preferred_supplier else 4.80
    estimated_cost = round(additional_to_purchase * cost_rate, 2)
    estimated_gross_profit = round(expected_sales_revenue - estimated_cost, 2)
    
    return {
        'eligible_orders': eligible_orders,
        'total_orders_count': total_orders_count,
        'total_eggs_required': total_eggs_required,
        'available_stock': available_stock,
        'current_stock_total': inv.current_stock,
        'additional_to_purchase': additional_to_purchase,
        'preferred_supplier': preferred_supplier,
        'estimated_cost_rate': cost_rate,
        'estimated_cost': estimated_cost,
        'expected_sales_revenue': expected_sales_revenue,
        'estimated_gross_profit': estimated_gross_profit,
        'is_low_stock': inv.current_stock < Config.LOW_STOCK_THRESHOLD
    }

def execute_wholesale_purchase(supplier_id, quantity, price_per_egg, invoice_ref="", notes=""):
    """
    Records a wholesale egg purchase batch, increments inventory stock,
    and transitions pending orders to 'EGGS_PURCHASED'.
    """
    supplier = Supplier.query.get(supplier_id)
    if not supplier:
        raise ValueError("Supplier not found")
        
    quantity = int(quantity)
    price_per_egg = float(price_per_egg)
    total_cost = round(quantity * price_per_egg, 2)
    
    now_str = now_utc().strftime('%Y%m%d%H%M')
    batch_code = f"PUR-{now_str}"
    
    batch = PurchaseBatch(
        batch_code=batch_code,
        supplier_id=supplier.id,
        total_eggs=quantity,
        price_per_egg=price_per_egg,
        total_cost=total_cost,
        invoice_number=invoice_ref,
        notes=notes,
        status='RECEIVED'
    )
    db.session.add(batch)
    
    # Update inventory
    inv = get_or_create_inventory()
    inv.total_purchased += quantity
    inv.current_stock += quantity
    
    # Assign eligible pending orders to this batch and mark as EGGS_PURCHASED
    pending_orders = Order.query.filter(
        Order.payment_status == 'PAID',
        Order.order_status.in_(['ORDER_RECEIVED', 'PAYMENT_CONFIRMED', 'WHOLESALE_PENDING'])
    ).all()
    
    remaining_batch_capacity = quantity
    for order in pending_orders:
        if remaining_batch_capacity >= order.egg_quantity:
            order.order_status = 'EGGS_PURCHASED'
            order.batch_id = batch.id
            inv.allocated_stock += order.egg_quantity
            remaining_batch_capacity -= order.egg_quantity
            
    # Notify Admin
    notification = AppNotification(
        title="Wholesale Batch Recorded",
        message=f"Purchased {quantity} eggs from {supplier.name} at ₹{price_per_egg}/egg (Total ₹{total_cost}). Stock updated.",
        category="wholesale",
        link="/admin/inventory"
    )
    db.session.add(notification)
    
    db.session.commit()
    return batch

def record_wastage(quantity, reason, cost_per_egg=4.80, notes=""):
    """Logs damaged or broken eggs, deducts from current stock, tracks financial loss."""
    quantity = int(quantity)
    cost_per_egg = float(cost_per_egg)
    total_loss = round(quantity * cost_per_egg, 2)
    
    log = WastageLog(
        quantity=quantity,
        cost_per_egg=cost_per_egg,
        total_loss=total_loss,
        reason=reason,
        notes=notes
    )
    db.session.add(log)
    
    inv = get_or_create_inventory()
    inv.current_stock = max(0, inv.current_stock - quantity)
    inv.damaged_stock += quantity
    
    notification = AppNotification(
        title="Wastage Logged",
        message=f"{quantity} eggs recorded as damaged/wasted ({reason}). Loss: ₹{total_loss}",
        category="inventory",
        link="/admin/inventory"
    )
    db.session.add(notification)
    db.session.commit()
    return log
