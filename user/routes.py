from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for, jsonify
from flask_login import current_user, login_required
import os
from werkzeug.utils import secure_filename
from auth.routes import UPLOAD_FOLDER
from db import get_db
from models.user import FoundItem, LostItem
from werkzeug.security import check_password_hash, generate_password_hash


# Create a Blueprint named "user" with updated template folder
user_bp = Blueprint('user', __name__, template_folder='../project/user/templates')

UPLOADS_DIR = os.path.join('static', 'uploads')
ALLOWED_EXTS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTS

@user_bp.route('/dashboard')
def dashboard():
    return render_template('user/user_dashboard.html')

@user_bp.route('/lost-items')
@login_required
def lost_items():
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, user_id, name, category, description,
                   last_seen, last_seen_at, status, photo, reported_at
            FROM lost_items
            WHERE user_id=%s
            ORDER BY reported_at DESC
        """, (int(current_user.get_id()),))
        rows = cur.fetchall()
    finally:
        cur.close(); conn.close()
    items = [LostItem.from_row(r) for r in rows]
    return render_template('user/my_lost_items.html', items=items)

@user_bp.route('/lost-items/new', methods=['POST'])
def create_lost_item():
    item_name = request.form.get('item_name')
    category = request.form.get('category')
    date_lost = request.form.get('date_lost')
    location_lost = request.form.get('location_lost')
    description = request.form.get('description')
    reward = request.form.get('reward')
    photo = request.files.get('photo')

    # TODO: Save to DB, handle photo upload
    print("New lost item:", item_name, category, date_lost, location_lost, description, reward, photo)

    return ('', 200)

@user_bp.route('/my-lost-items')
@login_required
def my_lost_items():
        # 🔍 Debug prints
    print("DEBUG current_user:", current_user)
    print("DEBUG current_user.id:", current_user.id)
    print("DEBUG current_user.get_id():", current_user.get_id())
    print("DEBUG current_user.is_authenticated:", current_user.is_authenticated)
    print("DEBUG current_user.is_active:", current_user.is_active())
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, user_id, name, category, description,
                   last_seen, last_seen_at, status, photo, reported_at
            FROM lost_items
            WHERE user_id=%s
            ORDER BY reported_at DESC
        """, (int(current_user.get_id()),))
        rows = cur.fetchall()
    finally:
        cur.close(); conn.close()
    items = [LostItem.from_row(r) for r in rows]
    return render_template('user/my_lost_items.html', items=items)

@user_bp.route('/my-found-items')
@login_required
def my_found_items():
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, user_id, name, category, description,
                   where_found, found_at, status, photo, reported_at
            FROM found_items
            WHERE user_id=%s
            ORDER BY reported_at DESC
        """, (int(current_user.get_id()),))
        rows = cur.fetchall()
    finally:
        cur.close(); conn.close()

    items = [FoundItem.from_row(r) for r in rows]
    return render_template('user/my_found_items.html', items=items)




@user_bp.route('/report-lost', methods=['POST'])
@login_required
def report_lost():
    name = request.form.get('name', '').strip()
    category = request.form.get('category', '').strip()
    description = request.form.get('description', '').strip()
    last_seen = request.form.get('last_seen', '').strip()
    last_seen_at = request.form.get('last_seen_at') or None  # datetime-local value
    photo_file = request.files.get('photo')

    if not name:
        flash('Item name is required.', 'danger')
        return redirect(url_for('user.my_lost_items'))

    photo_filename = None
    if photo_file and allowed_file(photo_file.filename):
        os.makedirs(UPLOADS_DIR, exist_ok=True)
        safe = secure_filename(photo_file.filename)
        photo_filename = f"{current_user.id}_{safe}"
        photo_path = os.path.join(UPLOADS_DIR, photo_filename)
        photo_file.save(photo_path)

    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO lost_items
            (user_id, name, category, description, last_seen, last_seen_at, status, photo, reported_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'pending', %s, NOW())
        """, (int(current_user.get_id()), name, category, description, last_seen, last_seen_at, photo_filename))
        conn.commit()
    finally:
        cur.close(); conn.close()

    flash('Lost item reported successfully.', 'success')
    return redirect(url_for('user.my_lost_items'))


@user_bp.route('/report-found', methods=['POST'])
@login_required
def report_found():
    name = request.form.get('name')
    category = request.form.get('category')
    description = request.form.get('description')
    where_found = request.form.get('where_found')
    found_at = request.form.get('found_at')
    photo = request.files.get('photo')

    photo_filename = None
    if photo and allowed_file(photo.filename):
        filename = secure_filename(photo.filename)
        photo_filename = f"{current_user.id}_{filename}"
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        photo.save(os.path.join(UPLOAD_FOLDER, photo_filename))

    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO found_items
            (user_id, name, category, description, where_found, found_at, status, photo, reported_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'pending', %s, NOW())
        """, (int(current_user.get_id()), name, category, description, where_found, found_at, photo_filename))
        conn.commit()
    finally:
        cur.close(); conn.close()

    flash('Found item reported successfully!', 'success')
    return redirect(url_for('user.my_found_items'))


@user_bp.route('/lost/<int:item_id>/view')
@login_required
def view_lost_item(item_id):
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM lost_items WHERE id=%s AND user_id=%s", (item_id, int(current_user.get_id())))
        row = cur.fetchone()
    finally:
        cur.close(); conn.close()
    
    if not row:
        return "<div class='alert alert-danger p-3'>Item not found or access denied.</div>", 404
    
    item = LostItem.from_row(row)
    return render_template('user/_view_lost_item.html', item=item)

@user_bp.route('/lost/<int:item_id>/edit')
@login_required
def edit_lost_item(item_id):
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM lost_items WHERE id=%s AND user_id=%s", (item_id, int(current_user.get_id())))
        row = cur.fetchone()
    finally:
        cur.close(); conn.close()
    
    if not row:
        return "<div class='alert alert-danger p-3'>Item not found or access denied.</div>", 404
    
    item = LostItem.from_row(row)
    return render_template('user/_edit_lost_item.html', item=item)

@user_bp.route('/lost/<int:item_id>/close', methods=['POST'])
@login_required
def close_lost_item(item_id):
    conn = get_db(); cur = conn.cursor()
    # Only allow closing your own item
    cur.execute("UPDATE lost_items SET status='closed' WHERE id=%s AND user_id=%s",
                (item_id, current_user.id))
    conn.commit()
    cur.close(); conn.close()
    flash('Item marked as closed.', 'success')
    return redirect(url_for('user.my_lost_items'))

@user_bp.route('/lost/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_lost_item(item_id):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT photo FROM lost_items WHERE id=%s AND user_id=%s", (item_id, current_user.id))
    row = cur.fetchone()

    photo = None
    if row:
        # handle both tuple and dict row types
        if isinstance(row, tuple):
            photo = row[0]
        elif isinstance(row, dict):
            photo = row.get('photo')

    cur.execute("DELETE FROM lost_items WHERE id=%s AND user_id=%s", (item_id, current_user.id))
    conn.commit()
    cur.close(); conn.close()

    if photo:
        try:
            os.remove(os.path.join(UPLOADS_DIR, photo))
        except Exception:
            pass  # ignore file not found

    flash('Item deleted.', 'success')
    return redirect(url_for('user.my_lost_items'))



@user_bp.route('/found/<int:id>/view')
@login_required
def view_found_item(id):
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, user_id, name, category, description,
                   where_found, found_at, status, photo, reported_at
            FROM found_items WHERE id=%s AND user_id=%s
        """, (id, current_user.id))
        row = cur.fetchone()
    finally:
        cur.close(); conn.close()

    if not row:
        return "<p class='text-danger'>Item not found.</p>"

    item = FoundItem.from_row(row)
    return render_template('user/partials/view_found_item.html', item=item)

@user_bp.route('/found/<int:id>/edit')
@login_required
def edit_found_item(id):
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, user_id, name, category, description,
                   where_found, found_at, status, photo, reported_at
            FROM found_items WHERE id=%s AND user_id=%s
        """, (id, current_user.id))
        row = cur.fetchone()
    finally:
        cur.close(); conn.close()

    if not row:
        return "<p class='text-danger'>Item not found.</p>"

    item = FoundItem.from_row(row)
    return render_template('user/partials/edit_found_item.html', item=item)

@user_bp.route('/found/<int:id>/update', methods=['POST'])
@login_required
def update_found_item(id):
    name = request.form.get('name')
    category = request.form.get('category')
    description = request.form.get('description')
    where_found = request.form.get('where_found')
    found_at = request.form.get('found_at')

    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE found_items
            SET name=%s, category=%s, description=%s,
                where_found=%s, found_at=%s
            WHERE id=%s AND user_id=%s
        """, (name, category, description, where_found, found_at, id, current_user.id))
        conn.commit()
    finally:
        cur.close(); conn.close()

    flash('Found item updated successfully!', 'success')
    return redirect(url_for('user.my_found_items'))

@user_bp.route('/lost/<int:item_id>/update', methods=['POST'])
@login_required
def update_lost_item(item_id):
    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        last_seen = request.form.get('last_seen')
        last_seen_at = request.form.get('last_seen_at')
        description = request.form.get('description')

        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            UPDATE lost_items
            SET name=%s, category=%s, last_seen=%s, last_seen_at=%s, description=%s
            WHERE id=%s AND user_id=%s
        """, (name, category, last_seen, last_seen_at, description, item_id, current_user.id))
        conn.commit()
        cur.close()
        conn.close()

        flash('Lost item updated successfully!', 'success')
        return redirect(url_for('user.lost_items'))


@user_bp.route('/found/<int:id>/delete', methods=['POST'])
@login_required
def delete_found_item(id):
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM found_items WHERE id=%s AND user_id=%s", (id, current_user.id))
        conn.commit()
    finally:
        cur.close(); conn.close()

    flash('Found item deleted successfully!', 'info')
    return redirect(url_for('user.my_found_items'))

@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Handle profile photo upload
        profile_photo = request.files.get('profile_photo')
        photo_filename = current_user.profile_photo  # keep existing photo by default
        
        if profile_photo and profile_photo.filename:
            if allowed_file(profile_photo.filename):
                os.makedirs(os.path.join('static', 'uploads', 'profile_photos'), exist_ok=True)
                filename = secure_filename(profile_photo.filename)
                photo_filename = f"{current_user.id}_{filename}"
                photo_path = os.path.join('static', 'uploads', 'profile_photos', photo_filename)
                profile_photo.save(photo_path)
        
        # Update user preferences in database
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("""
                UPDATE users
                SET profile_photo=%s
                WHERE id=%s
            """, (photo_filename, current_user.id))
            conn.commit()
            
            # Update current_user object
            current_user.profile_photo = photo_filename
            
            flash('Profile updated successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Profile update failed: {str(e)}', 'danger')
        finally:
            cur.close()
            conn.close()
        
        return redirect(url_for('user.profile'))

    # Fetch user activity
    conn = get_db()
    cur = conn.cursor()
    try:
        # Get recent lost items
        cur.execute("""
            SELECT 'Lost Item' as type, name, reported_at
            FROM lost_items
            WHERE user_id=%s
            ORDER BY reported_at DESC
            LIMIT 3
        """, (current_user.id,))
        lost_activities = list(cur.fetchall())
        
        # Get recent found items
        cur.execute("""
            SELECT 'Found Item' as type, name, reported_at
            FROM found_items
            WHERE user_id=%s
            ORDER BY reported_at DESC
            LIMIT 3
        """, (current_user.id,))
        found_activities = list(cur.fetchall())
        
        # Combine and sort by date
        activities = lost_activities + found_activities
        activities = sorted(activities, key=lambda x: x.get('reported_at') or '', reverse=True)[:5]
        
    finally:
        cur.close()
        conn.close()

    return render_template('user/profile.html', user=current_user, activities=activities)

@user_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    current_pw = request.form.get('current_password')
    new_pw = request.form.get('new_password')
    confirm_pw = request.form.get('confirm_password')

    if not current_user.check_password(current_pw):
        flash('Incorrect current password.', 'danger')
        return redirect(url_for('user.profile'))

    if new_pw != confirm_pw:
        flash('New passwords do not match.', 'warning')
        return redirect(url_for('user.profile'))

    # Hash new password
    current_user.set_password(new_pw)

    # Update DB using raw connection
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE users SET password_hash=%s WHERE id=%s",
                    (current_user.password_hash, current_user.id))
        conn.commit()
        flash('Password updated successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Password update failed: {str(e)}', 'danger')
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('user.profile'))




@user_bp.route('/notifications')
def notifications():
    return render_template('user/notifications.html')

@user_bp.route('/debug-user')
@login_required
def debug_user():
    return f"""
    <h3>Debug Current User</h3>
    <ul>
      <li><strong>repr:</strong> {current_user!r}</li>
      <li><strong>id:</strong> {current_user.id}</li>
      <li><strong>get_id():</strong> {current_user.get_id()}</li>
      <li><strong>is_authenticated:</strong> {current_user.is_authenticated}</li>
      <li><strong>is_active:</strong> {current_user.is_active()}</li>
      <li><strong>email:</strong> {getattr(current_user, 'email', None)}</li>
      <li><strong>student_id:</strong> {getattr(current_user, 'student_id', None)}</li>
    </ul>
    """

@user_bp.route('/api/lost_items/<int:item_id>')
@login_required
def api_lost_item(item_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, user_id, name, category, description,
                   last_seen, last_seen_at, status, photo, reported_at
            FROM lost_items
            WHERE id=%s AND user_id=%s
        """, (item_id, int(current_user.get_id())))
        row = cur.fetchone()
    finally:
        cur.close(); conn.close()

    if not row:
        return jsonify({'error': 'Item not found'}), 404

    # Format reported_at date
    reported_at_str = None
    if row.get('reported_at'):
        try:
            reported_at_str = row['reported_at'].strftime('%Y-%m-%d')
        except:
            reported_at_str = str(row['reported_at'])

    return jsonify({
        'id': row.get('id'),
        'name': row.get('name'),
        'category': row.get('category'),
        'description': row.get('description'),
        'last_seen': row.get('last_seen'),
        'last_seen_at': row.get('last_seen_at'),
        'status': row.get('status'),
        'photo': row.get('photo'),
        'reported_at': reported_at_str
    })

@user_bp.route('/api/found_items/<int:id>')
@login_required
def api_found_item(id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, user_id, name, category, description,
                   where_found, found_at, status, photo, reported_at
            FROM found_items
            WHERE id=%s AND user_id=%s
        """, (id, int(current_user.get_id())))
        row = cur.fetchone()
    finally:
        cur.close(); conn.close()

    if not row:
        return jsonify({'error': 'Item not found'}), 404

    # Format found_at date
    found_at_str = None
    if row.get('found_at'):
        try:
            found_at_str = row['found_at'].strftime('%Y-%m-%d')
        except:
            found_at_str = str(row['found_at'])

    return jsonify({
        'id': row.get('id'),
        'name': row.get('name'),
        'category': row.get('category'),
        'description': row.get('description'),
        'where_found': row.get('where_found'),
        'found_at': found_at_str,
        'status': row.get('status'),
        'photo': row.get('photo'),
        'reported_at': row.get('reported_at')
    })


#ML Routes
@user_bp.route('/matches')
@login_required
def matches():
    # Placeholder: Replace with real matching logic later
    matches = []  # or a list of dicts with matched items
    return render_template('user/matches.html', matches=matches)
