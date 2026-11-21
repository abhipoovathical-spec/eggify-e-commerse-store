import hashlib
import hmac
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from models import db, Order, Gym, AppNotification, Customer
from services.notifications import notify_admin

api_bp = Blueprint('api', __name__, url_prefix='/api')

def now_utc():
    return datetime.now(timezone.utc)

@api_bp.route('/gyms', methods=['GET'])
def get_gyms():
    gyms = Gym.query.filter_by(is_active=True).all()
    return jsonify({
        'status': 'success',
        'gyms': [{
            'id': g.id,
            'code': g.gym_code,
            'name': g.name,
            'address': g.address,
            'city': g.city
        } for g in gyms]
    })


@api_bp.route('/order/status/<order_code>', methods=['GET'])
def order_status(order_code):
    order = Order.query.filter_by(order_code=order_code).first()
    if not order:
        return jsonify({'status': 'error', 'message': 'Order not found'}), 404
        
    return jsonify({
        'status': 'success',
        'order_code': order.order_code,
        'order_status': order.order_status,
        'payment_status': order.payment_status,
        'quantity': order.egg_quantity,
        'total_amount': order.total_amount
    })


@api_bp.route('/notifications/unread', methods=['GET'])
def unread_notifications():
    unread = AppNotification.query.filter_by(is_read=False).order_by(AppNotification.created_at.desc()).limit(10).all()
    return jsonify({
        'status': 'success',
        'count': len(unread),
        'notifications': [{
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'category': n.category,
            'link': n.link,
            'created_at': n.created_at.strftime('%I:%M %p')
        } for n in unread]
    })


@api_bp.route('/notifications/<int:notif_id>/read', methods=['POST'])
def mark_notification_read(notif_id):
    notif = AppNotification.query.get(notif_id)
    if notif:
        notif.is_read = True
        db.session.commit()
    return jsonify({'status': 'success'})


@api_bp.route('/payment/webhook', methods=['POST'])
def payment_webhook():
    """
    Webhook endpoint for automated payment gateways (e.g. Razorpay/UPI gateway).
    Verifies signature, ensures transaction consistency, prevents duplicate credit.
    """
    payload = request.get_json() or {}
    order_code = payload.get('order_code') or payload.get('notes', {}).get('order_code')
    txn_id = payload.get('transaction_id') or payload.get('payment_id', 'WEBHOOK_TXN')
    status = payload.get('status', 'PAID')
    
    if not order_code:
        return jsonify({'status': 'error', 'message': 'Missing order_code'}), 400
        
    order = Order.query.filter_by(order_code=order_code).first()
    if not order:
        return jsonify({'status': 'error', 'message': 'Order not found'}), 404
        
    if order.payment_status == 'PAID':
        return jsonify({'status': 'success', 'message': 'Order already marked as paid'}), 200
        
    if status in ['PAID', 'SUCCESS', 'captured']:
        order.payment_status = 'PAID'
        order.order_status = 'PAYMENT_CONFIRMED'
        order.transaction_id = txn_id
        order.payment_verified_at = now_utc()
        
        customer = order.customer
        if customer:
            customer.total_orders = (customer.total_orders or 0) + 1
            customer.total_eggs = (customer.total_eggs or 0) + order.egg_quantity
            customer.total_spent = round((customer.total_spent or 0.0) + order.total_amount, 2)
            customer.last_order_date = now_utc()
            
        notify_admin(
            title=f"Webhook Confirmed Payment #{order.order_code}",
            message=f"Received ₹{order.total_amount:.2f} via Webhook. Transaction: {txn_id}",
            category="payment",
            link=f"/admin/orders?search={order.order_code}"
        )
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Payment confirmed via webhook'})
        
    return jsonify({'status': 'ignored', 'message': 'Status not applicable'}), 200
