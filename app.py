from flask import Flask, redirect, url_for
from extensions import bcrypt, login_manager
from auth.routes import auth_bp
from user.routes import user_bp
from admin.init import admin_bp 
from admin.admin_claims import admin_claims_bp
from services.notifications_routes import notifications_bp
from flask_login import current_user
from services.notifications import get_unread_count, get_recent_notifications

app = Flask(__name__, template_folder='project/templates')
app.secret_key = 'secret_key_here'

# --- Initialize extensions ---
bcrypt.init_app(app)
login_manager.init_app(app)

# --- Register blueprints ---
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(user_bp, url_prefix='/user')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(admin_claims_bp)
app.register_blueprint(notifications_bp)

# --- Context Processor for Notifications ---
@app.context_processor
def inject_notifications():
    """Inject notification data into all templates."""
    try:
        if current_user.is_authenticated:
            unread_notifications_count = get_unread_count(current_user.id)
            notifications = get_recent_notifications(current_user.id, limit=5)
        else:
            unread_notifications_count = 0
            notifications = []
    except Exception as e:
        print(f"[CONTEXT PROCESSOR] Error loading notifications: {e}")
        unread_notifications_count = 0
        notifications = []

    return {
        'unread_notifications_count': unread_notifications_count,
        'notifications': notifications
    }



@app.route('/')
def index():
    return redirect(url_for('auth.login'))

if __name__ == '__main__':
    # Bind to all interfaces so other devices can access
    app.run(host='0.0.0.0', port=5000, debug=True)

