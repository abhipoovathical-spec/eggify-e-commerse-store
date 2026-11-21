import json
from models import PricingConfig, db
from config import Config

def get_pricing_value(key, default):
    config_item = PricingConfig.query.filter_by(key=key).first()
    if config_item:
        try:
            return float(config_item.value)
        except ValueError:
            return config_item.value
    return default

def calculate_order_pricing(quantity, delivery_type='gym_pickup', distance_km=0.0):
    """
    Calculates subtotal, price per egg, delivery charge, and final total amount.
    Enforces server-side validation.
    """
    quantity = int(quantity)
    if quantity < Config.MIN_ORDER_QUANTITY:
        quantity = Config.MIN_ORDER_QUANTITY
        
    base_price = get_pricing_value('base_price_per_egg', Config.DEFAULT_BASE_PRICE_PER_EGG)
    
    # Check tiered package discounts
    package_type = 'custom'
    if quantity == 6:
        subtotal = get_pricing_value('pkg_6_price', Config.DEFAULT_PACKAGES[6])
        package_type = '6'
    elif quantity == 12:
        subtotal = get_pricing_value('pkg_12_price', Config.DEFAULT_PACKAGES[12])
        package_type = '12'
    elif quantity == 18:
        subtotal = get_pricing_value('pkg_18_price', Config.DEFAULT_PACKAGES[18])
        package_type = '18'
    elif quantity == 30:
        subtotal = get_pricing_value('pkg_30_price', Config.DEFAULT_PACKAGES[30])
        package_type = '30'
    elif quantity == 60:
        subtotal = get_pricing_value('pkg_60_price', Config.DEFAULT_PACKAGES[60])
        package_type = '60'
    elif quantity > 60:
        # Bulk discount for 60+
        rate = base_price * 0.90 # 10% wholesale discount
        subtotal = round(quantity * rate, 2)
    elif quantity >= 30:
        rate = base_price * 0.93
        subtotal = round(quantity * rate, 2)
    elif quantity >= 12:
        rate = base_price * 0.96
        subtotal = round(quantity * rate, 2)
    else:
        subtotal = round(quantity * base_price, 2)
        
    price_per_egg = round(subtotal / quantity, 2)
    
    # Delivery charge
    delivery_charge = 0.0
    if delivery_type == 'home_delivery':
        base_delivery = get_pricing_value('home_delivery_base', Config.DEFAULT_HOME_DELIVERY_BASE)
        per_km = get_pricing_value('home_delivery_per_km', Config.DEFAULT_HOME_DELIVERY_PER_KM)
        distance = max(0.0, float(distance_km or 0.0))
        
        # If distance provided, add km rate beyond first 2 km
        if distance > 2:
            extra_km = distance - 2
            delivery_charge = round(base_delivery + (extra_km * per_km), 2)
        else:
            delivery_charge = base_delivery
    else:
        # Gym pickup is always 100% free
        delivery_charge = 0.0
        
    total_amount = round(subtotal + delivery_charge, 2)
    
    return {
        'quantity': quantity,
        'package_type': package_type,
        'price_per_egg': price_per_egg,
        'eggs_subtotal': subtotal,
        'delivery_charge': delivery_charge,
        'total_amount': total_amount
    }
