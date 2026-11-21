import urllib.parse
from models import db, AppNotification
from config import Config

def notify_admin(title, message, category="order", link=None):
    """Creates a system notification for the admin dashboard."""
    notif = AppNotification(
        title=title,
        message=message,
        category=category,
        link=link
    )
    db.session.add(notif)
    db.session.commit()
    return notif

def generate_whatsapp_link(phone, message):
    """
    Generates a WhatsApp click-to-chat URL with pre-filled message.
    e.g. https://wa.me/919876543210?text=...
    """
    clean_phone = "".join(filter(str.isdigit, str(phone)))
    if len(clean_phone) == 10:
        clean_phone = "91" + clean_phone
    encoded_msg = urllib.parse.quote(message)
    return f"https://wa.me/{clean_phone}?text={encoded_msg}"

def get_customer_notification_templates(order):
    """
    Provides pre-formatted messaging templates for WhatsApp/SMS
    that the business owner can dispatch with 1 click!
    """
    gym_name = order.gym.name if order.gym else "your selected Gym"
    delivery_info = f"Gym Collection at {gym_name}" if order.delivery_type == 'gym_pickup' else f"Home Delivery to {order.delivery_address}"
    
    # 1. Order Confirmation
    confirmation_msg = (
        f"🍳 *EGGIFY - Fresh Eggs Order Confirmed!*\n\n"
        f"Hi {order.customer_name},\n"
        f"Your order *#{order.order_code}* for *{order.egg_quantity} Fresh Eggs* (₹{order.total_amount:.2f}) has been confirmed!\n\n"
        f"📍 Fulfillment: {delivery_info}\n"
        f"📅 Date: {order.preferred_date.strftime('%d %b %Y')} ({order.preferred_time_slot})\n\n"
        f"Track your order live here: /track/{order.order_code}\n\n"
        f"Stay Fit, Eat Fresh!\nTeam EGGIFY"
    )
    
    # 2. Ready for pickup
    ready_msg = (
        f"🎉 *EGGIFY - Your Protein is Ready for Collection!*\n\n"
        f"Hi {order.customer_name},\n"
        f"Your {order.egg_quantity} Fresh Eggs are packed and waiting at *{gym_name}* front desk!\n\n"
        f"🔖 Show Order ID: *{order.order_code}* at the gym desk.\n"
        f"Enjoy your daily protein!\nTeam EGGIFY"
    )
    
    # 3. Out for Delivery
    delivery_msg = (
        f"🚚 *EGGIFY - Out For Delivery!*\n\n"
        f"Hi {order.customer_name},\n"
        f"Your {order.egg_quantity} Fresh Farm Eggs are out for delivery to your address.\n"
        f"Order ID: *{order.order_code}*\n\n"
        f"Team EGGIFY"
    )
    
    return {
        'confirmation_url': generate_whatsapp_link(order.customer_phone, confirmation_msg),
        'confirmation_msg': confirmation_msg,
        'ready_url': generate_whatsapp_link(order.customer_phone, ready_msg),
        'ready_msg': ready_msg,
        'delivery_url': generate_whatsapp_link(order.customer_phone, delivery_msg),
        'delivery_msg': delivery_msg
    }
