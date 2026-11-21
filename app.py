import os
from flask import Flask, render_template
from config import Config
from models import db, AppNotification, Gym

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize SQLAlchemy
    db.init_app(app)
    
    # Register Blueprints
    from routes.customer import customer_bp
    from routes.admin import admin_bp
    from routes.api import api_bp
    
    app.register_blueprint(customer_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    
    # Custom template filters
    @app.template_filter('inr')
    def inr_filter(value):
        try:
            return f"₹{float(value):,.2f}"
        except (ValueError, TypeError):
            return f"₹{value}"

    @app.template_filter('format_date')
    def format_date_filter(val, fmt='%d %b %Y'):
        if not val:
            return ''
        return val.strftime(fmt)
        
    # Global context processor
    @app.context_processor
    def inject_globals():
        unread_count = 0
        try:
            unread_count = AppNotification.query.filter_by(is_read=False).count()
        except Exception:
            pass
        return {
            'APP_NAME': Config.APP_NAME,
            'APP_TAGLINE': Config.APP_TAGLINE,
            'SUPPORT_PHONE': Config.SUPPORT_PHONE,
            'SUPPORT_EMAIL': Config.SUPPORT_EMAIL,
            'unread_notifications_count': unread_count
        }

    # Serve public folder (for hero section scroll animation images)
    from flask import send_from_directory
    @app.route('/public/<path:filename>')
    def serve_public(filename):
        public_dir = os.path.join(app.root_path, 'public')
        return send_from_directory(public_dir, filename)

    @app.route('/public/image/<path:filename>')
    def serve_public_image_alias(filename):
        images_dir = os.path.join(app.root_path, 'public', 'images')
        return send_from_directory(images_dir, filename)
        
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500

    return app

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # Run locally on port 5000
    app.run(host='0.0.0.0', port=5000, debug=False)
