import io
import base64
import urllib.parse
import qrcode
from config import Config
from models import PricingConfig

def generate_qr_base64(data_string, box_size=10, border=2):
    """Generates a high-quality QR code image returned as a base64 Data URL."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data_string)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="#0F1115", back_color="#FFFFFF")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"

def generate_gym_qr_data_url(gym_code, base_url=""):
    """
    Creates a QR code directing customer to gym-specific order page:
    e.g. {base_url}/order?gym={gym_code}
    """
    if not base_url:
        target_url = f"/order?gym={gym_code}"
    else:
        target_url = f"{base_url.rstrip('/')}/order?gym={gym_code}"
    return generate_qr_base64(target_url, box_size=12, border=2)

def generate_upi_payload(order_code, amount, customer_name="Customer"):
    """
    Generates standard Indian UPI payment string:
    upi://pay?pa={UPI_ID}&pn={PAYEE}&am={AMOUNT}&tn={NOTE}&tr={TXN_REF}&cu=INR
    """
    upi_id_cfg = PricingConfig.query.filter_by(key='upi_id').first()
    upi_id = upi_id_cfg.value if upi_id_cfg else Config.UPI_ID
    
    payee_cfg = PricingConfig.query.filter_by(key='upi_payee_name').first()
    payee_name = payee_cfg.value if payee_cfg else Config.UPI_PAYEE_NAME
    
    note = f"EGGIFY-{order_code}"
    
    params = {
        'pa': upi_id,
        'pn': payee_name,
        'am': f"{amount:.2f}",
        'tn': note,
        'tr': order_code,
        'cu': 'INR'
    }
    
    query_string = urllib.parse.urlencode(params)
    upi_uri = f"upi://pay?{query_string}"
    
    # Generate QR base64
    qr_data_url = generate_qr_base64(upi_uri, box_size=8, border=2)
    
    return {
        'upi_uri': upi_uri,
        'qr_data_url': qr_data_url,
        'upi_id': upi_id,
        'payee_name': payee_name,
        'amount': amount,
        'order_code': order_code
    }
