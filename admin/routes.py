from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required
import pymysql

from db import get_db
from models.user import User
from .init import admin_bp  


@admin_bp.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        # Fetch users with report count
        cur.execute("""
            SELECT u.id, u.name, u.student_id, u.email, u.role, u.active,
                   u.profile_photo AS photo_url,
                   (SELECT COUNT(*) FROM lost_items WHERE user_id = u.id) +
                   (SELECT COUNT(*) FROM found_items WHERE user_id = u.id) AS reports_count
            FROM users u
            ORDER BY u.id ASC
        """)
        users = cur.fetchall()

        # KPIs
        cur.execute("SELECT COUNT(*) AS total FROM users")
        total_users = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) AS active_count FROM users WHERE active=1")
        active_users = cur.fetchone()["active_count"]

        cur.execute("SELECT COUNT(*) AS admins FROM users WHERE role='admin'")
        admin_count = cur.fetchone()["admins"]

        cur.execute("SELECT COUNT(*) AS lost_count FROM lost_items")
        lost_items = cur.fetchone()["lost_count"]

        cur.execute("SELECT COUNT(*) AS found_count FROM found_items")
        found_items = cur.fetchone()["found_count"]

        # Pending verifications from both tables
        cur.execute("""
            SELECT
              (SELECT COUNT(*) FROM lost_items WHERE status='pending') +
              (SELECT COUNT(*) FROM found_items WHERE status='pending') AS pending
        """)
        pending = cur.fetchone()["pending"]

        kpis = {
            "total_users": {"label": "Total Users", "value": total_users},
            "active_users": {"label": "Active Users", "value": active_users},
            "admins": {"label": "Admins", "value": admin_count},
            "lost_items": {"label": "Lost Items Reported", "value": lost_items},
            "found_items": {"label": "Found Items Reported", "value": found_items},
            "pending": {"label": "Pending Verifications", "value": pending},
        }

        # Reports Overview Table — fallback to lost + found items
        cur.execute("""
            SELECT li.id, li.name, 'lost' AS type, li.reported_at, li.last_seen AS location, 
                   li.status, u.name AS reporter_name
            FROM lost_items li
            JOIN users u ON li.user_id = u.id
            UNION ALL
            SELECT fi.id, fi.name, 'found' AS type, fi.reported_at, fi.where_found AS location,
                   fi.status, u.name AS reporter_name
            FROM found_items fi
            JOIN users u ON fi.user_id = u.id
            ORDER BY reported_at DESC
            LIMIT 10
        """)
        reports = cur.fetchall()


        chart_data = {
            "labels": ["Lost Items", "Found Items"],
            "counts": [lost_items, found_items]
        }

        return render_template(
            'admin/dashboard.html',
            users=users,
            kpis=kpis,
            chart_data=chart_data,
            reports=reports
        )

    finally:
        cur.close()
        conn.close()


@admin_bp.route('/users')
@login_required
def users_page():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, role, active, profile_photo FROM users ORDER BY id ASC")
    users = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin/user.html', users=users)

# --- Edit User ---
@admin_bp.route('/users/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    if request.method == 'POST':
        role = request.form.get('role')
        active = 1 if request.form.get('active') else 0

        conn = get_db()
        cur = conn.cursor()
        try:
            # Only update role and active status - preserve name and email
            cur.execute("""
                UPDATE users
                SET role=%s, active=%s
                WHERE id=%s
            """, (role, active, id))
            conn.commit()
            flash('User updated successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Update failed: {str(e)}', 'danger')
        finally:
            cur.close()
            conn.close()
        
        return redirect(url_for('admin.users_page'))

    # Fetch user for display
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, email, role, active FROM users WHERE id=%s", (id,))
        user = cur.fetchone()
    finally:
        cur.close()
        conn.close()
    
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin.users_page'))
    
    return render_template('admin/edit_user.html', user=user)


# --- Add User ---
# @admin_bp.route('/users/add', methods=['GET', 'POST'])
# @login_required
# def add_user():
#     if request.method == 'POST':
#         name = request.form.get('name')
#         email = request.form.get('email')
#         role = request.form.get('role')
#         active = 1 if request.form.get('active') else 0

#         conn = get_db()
#         cur = conn.cursor()
#         try:
#             cur.execute("""
#                 INSERT INTO users (name, email, role, active, password_hash, created_at)
#                 VALUES (%s, %s, %s, %s, %s, NOW())
#             """, (name, email, role, active, ''))
#             conn.commit()
#             flash('User added successfully!', 'success')
#         except Exception as e:
#             conn.rollback()
#             flash(f'Add user failed: {str(e)}', 'danger')
#         finally:
#             cur.close()
#             conn.close()
        
#         return redirect(url_for('admin.users_page'))

#     return render_template('admin/add_user.html')


# --- Deactivate User ---
@admin_bp.route('/users/deactivate/<int:id>', methods=['POST'])
@login_required
def deactivate_user(id):
    conn = get_db()
    cur = conn.cursor()
    try:
        # Get user name first for flash message
        cur.execute("SELECT name FROM users WHERE id=%s", (id,))
        user = cur.fetchone()
        user_name = user.get('name') if user else 'User'
        
        # Deactivate the user
        cur.execute("""
            UPDATE users
            SET active=0
            WHERE id=%s
        """, (id,))
        conn.commit()
        flash(f'User {user_name} has been deactivated.', 'warning')
    except Exception as e:
        conn.rollback()
        flash(f'Deactivate failed: {str(e)}', 'danger')
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('admin.users_page'))

@admin_bp.route('/items')
@login_required
def items_page():
    conn = get_db()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        # Get filter parameters
        search_q = request.args.get('q', '').strip()
        category = request.args.get('category', '').strip()
        item_type = request.args.get('type', '').strip()  # 'lost' or 'found'
        
        # Build dynamic query for lost items
        lost_query = """
            SELECT li.id, li.name, li.category, 'lost' AS type, li.reported_at,
                   li.last_seen AS location, li.status, li.photo, u.name AS reporter_name
            FROM lost_items li
            JOIN users u ON li.user_id = u.id
            WHERE 1=1
        """
        lost_params = []
        
        if search_q:
            lost_query += " AND (li.id LIKE %s OR li.name LIKE %s)"
            lost_params.extend([f'%{search_q}%', f'%{search_q}%'])
        
        if category:
            lost_query += " AND li.category = %s"
            lost_params.append(category)
        
        if item_type and item_type != 'found':
            # If searching for lost specifically, only use lost_query
            pass
        
        # Build dynamic query for found items
        found_query = """
            SELECT fi.id, fi.name, fi.category, 'found' AS type, fi.reported_at,
                   fi.where_found AS location, fi.status, fi.photo, u.name AS reporter_name
            FROM found_items fi
            JOIN users u ON fi.user_id = u.id
            WHERE 1=1
        """
        found_params = []
        
        if search_q:
            found_query += " AND (fi.id LIKE %s OR fi.name LIKE %s)"
            found_params.extend([f'%{search_q}%', f'%{search_q}%'])
        
        if category:
            found_query += " AND fi.category = %s"
            found_params.append(category)
        
        if item_type and item_type != 'lost':
            # If searching for found specifically, only use found_query
            pass
        
        # Execute queries based on type filter
        items = []
        
        if not item_type or item_type == 'lost':
            cur.execute(lost_query, lost_params)
            items.extend(cur.fetchall())
        
        if not item_type or item_type == 'found':
            cur.execute(found_query, found_params)
            items.extend(cur.fetchall())
        
        # Sort by reported_at descending
        items.sort(key=lambda x: x.get('reported_at') or '', reverse=True)
        
    finally:
        cur.close()
        conn.close()
    
    return render_template('admin/items.html', items=items)



@admin_bp.route('/reports')
@login_required
def reports_page():
    conn = get_db()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        # Fetch reports with reporter name from both lost and found items
        cur.execute("""
            SELECT li.id, li.name, 'lost' AS type, li.reported_at, li.last_seen AS location, 
                   li.status, u.name AS reporter_name
            FROM lost_items li
            JOIN users u ON li.user_id = u.id
            UNION ALL
            SELECT fi.id, fi.name, 'found' AS type, fi.reported_at, fi.where_found AS location,
                   fi.status, u.name AS reporter_name
            FROM found_items fi
            JOIN users u ON fi.user_id = u.id
            ORDER BY reported_at DESC
        """)
        reports = cur.fetchall()
    finally:
        cur.close()
        conn.close()
    
    return render_template('admin/reports.html', reports=reports)

@admin_bp.route('/settings')
@login_required
def settings_page():
    return render_template('admin/settings.html')