from flask import Flask, redirect, url_for
from extensions import bcrypt, login_manager
from auth.routes import auth_bp
from user.routes import user_bp
from admin.init import admin_bp 


app = Flask(__name__, template_folder='project/templates')
app.secret_key = 'secret_key_here'

# --- Initialize extensions ---
bcrypt.init_app(app)
login_manager.init_app(app)

# --- Register blueprints ---
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(user_bp, url_prefix='/user')
app.register_blueprint(admin_bp, url_prefix='/admin')  

@app.route('/')
def index():
    return redirect(url_for('auth.login'))

if __name__ == '__main__':
    # Bind to all interfaces so other devices can access
    app.run(host='0.0.0.0', port=5000, debug=True)

