import os
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename

from models.user import User
from db import get_db
from extensions import bcrypt, login_manager

# Configure logging once
logging.basicConfig(level=logging.DEBUG)

auth_bp = Blueprint('auth', __name__)

UPLOAD_FOLDER = os.path.join('static', 'uploads', 'profile_photos')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'avif'}


@login_manager.user_loader
def load_user(user_id: str):
    """Reload user object from the user ID stored in the session."""
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, name, student_id, email, password_hash, profile_photo, created_at, active, role
            FROM users WHERE id=%s
        """, (int(user_id),))
        row = cur.fetchone()
    conn.close()
    return User.from_row(row) if row else None


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------------- REGISTER ----------------
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        student_id = request.form.get('student_id', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')

        logging.debug(f"Register attempt: name={name}, student_id={student_id}, email={email}")

        if not all([name, student_id, email, password, confirm]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('auth.register'))

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.register'))

        pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')

        photo_filename = None
        photo = request.files.get('profile_photo')
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            photo_filename = f"{student_id}_{filename}"
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            photo.save(os.path.join(UPLOAD_FOLDER, photo_filename))

        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE student_id=%s OR email=%s", (student_id, email))
                if cur.fetchone():
                    flash('Student ID or Email is already registered.', 'danger')
                    return redirect(url_for('auth.register'))

                cur.execute("""
                    INSERT INTO users (name, student_id, email, password_hash, profile_photo, role)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (name, student_id, email, pw_hash, photo_filename, 'user'))
                conn.commit()

            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            conn.rollback()
            logging.error(f"Registration failed for email={email}: {e}")
            flash(f'Registration failed: {str(e)}', 'danger')
            return redirect(url_for('auth.register'))

        finally:
            conn.close()

    return render_template('auth/register.html')


# ---------------- LOGIN ----------------
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, name, student_id, email, password_hash, profile_photo, created_at, active, role
                    FROM users WHERE email=%s
                """, (email,))
                row = cur.fetchone()

            if not row:
                flash('Invalid email or password.', 'danger')
                return redirect(url_for('auth.login'))

            user = User.from_row(row)

            if not bcrypt.check_password_hash(user.password_hash, password):
                flash('Invalid email or password.', 'danger')
                return redirect(url_for('auth.login'))

            if not user.is_active():
                flash('Account inactive. Contact support.', 'warning')
                return redirect(url_for('auth.login'))

            login_user(user, remember=True)
            flash('Welcome back!', 'success')

            # ✅ Role-based redirect
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('user.dashboard'))

        finally:
            conn.close()

    return render_template('auth/login.html')


# ---------------- LOGOUT ----------------
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
