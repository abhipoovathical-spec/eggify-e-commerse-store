import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'eggify-super-secret-fitness-key-2026')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        f"sqlite:///{os.path.join(BASE_DIR, 'eggify.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Business Branding
    APP_NAME = "EGGIFY"
    APP_TAGLINE = "Fresh Eggs. Smart Ordering. Better Fitness."
    SUPPORT_PHONE = "+91 98765 43210"
    SUPPORT_EMAIL = "care@eggify.fitness"
    
    # Default UPI & Payment Settings
    UPI_ID = os.environ.get('UPI_ID', 'eggify@okhdfcbank')
    UPI_PAYEE_NAME = os.environ.get('UPI_PAYEE_NAME', 'EGGIFY Fresh Foods')
    
    # Default Pricing Rules (can be dynamically overridden in DB PricingConfig)
    DEFAULT_BASE_PRICE_PER_EGG = 9.00
    DEFAULT_PACKAGES = {
        6: 54.00,       # 9.00 / egg
        12: 102.00,     # 8.50 / egg
        18: 150.00,     # 8.33 / egg
        30: 240.00,     # 8.00 / egg (1 crate)
        60: 465.00,     # 7.75 / egg (2 crates)
    }
    
    DEFAULT_HOME_DELIVERY_BASE = 30.00
    DEFAULT_HOME_DELIVERY_PER_KM = 5.00
    MIN_ORDER_QUANTITY = 6
    MAX_ORDER_QUANTITY = 300
    
    # Low stock threshold
    LOW_STOCK_THRESHOLD = 150
