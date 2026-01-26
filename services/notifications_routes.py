from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
import pymysql.cursors
from db import get_db
from services.notifications import (
    get_recent_notifications, 
    mark_as_read, 
    mark_all_as_read,
    delete_notification,
    get_notification_by_id
)

notifications_bp = Blueprint('notifications', __name__, url_prefix='/notifications')

@notifications_bp.route('/')
@login_required
def notifications_page():
    """Display all notifications for the current user (read + unread)."""
    conn = get_db()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    try:
        cur.execute(
            """SELECT id, type, title, message, related_id, created_at, read_at
               FROM notifications
               WHERE user_id = %s
               ORDER BY created_at DESC
               LIMIT 200""",
            (current_user.id,),
        )
        notifications = cur.fetchall() or []

        cur.execute(
            """SELECT COUNT(*) as count
               FROM notifications
               WHERE user_id = %s AND read_at IS NULL""",
            (current_user.id,),
        )
        unread_count = (cur.fetchone() or {}).get('count', 0)

        # Tab counts (based on all notifications)
        cur.execute(
            """SELECT COUNT(*) as count
               FROM notifications
               WHERE user_id = %s AND type = 'claim_approved'""",
            (current_user.id,),
        )
        approved_count = (cur.fetchone() or {}).get('count', 0)

        cur.execute(
            """SELECT COUNT(*) as count
               FROM notifications
               WHERE user_id = %s AND type = 'claim_rejected'""",
            (current_user.id,),
        )
        rejected_count = (cur.fetchone() or {}).get('count', 0)

        cur.execute(
            """SELECT COUNT(*) as count
               FROM notifications
               WHERE user_id = %s AND type = 'new_claim'""",
            (current_user.id,),
        )
        pending_count = (cur.fetchone() or {}).get('count', 0)

        all_count = len(notifications)

    finally:
        cur.close()
        conn.close()

    return render_template(
        'user/notifications.html',
        notifications=notifications,
        unread_count=int(unread_count or 0),
        approved_count=int(approved_count or 0),
        rejected_count=int(rejected_count or 0),
        pending_count=int(pending_count or 0),
        all_count=int(all_count or 0),
    )

@notifications_bp.route('/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    success = mark_as_read(notification_id, current_user.id)
    if request.is_json:
        return jsonify({'success': success})
    return redirect(request.referrer or url_for('notifications.notifications_page'))

@notifications_bp.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read"""
    success = mark_all_as_read(current_user.id)
    if request.is_json:
        return jsonify({'success': success})
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('notifications.notifications_page'))

@notifications_bp.route('/<int:notification_id>/delete', methods=['POST'])
@login_required
def delete_user_notification(notification_id):
    """Delete a notification"""
    success = delete_notification(notification_id, current_user.id)
    if request.is_json:
        return jsonify({'success': success})
    flash('Notification deleted.', 'success')
    return redirect(request.referrer or url_for('notifications.notifications_page'))

@notifications_bp.route('/api/recent', methods=['GET'])
@login_required
def api_recent_notifications():
    """API endpoint for the navbar dropdown: return only recent unread notifications."""
    limit = request.args.get('limit', 10, type=int)

    conn = get_db()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    try:
        # Always compute unread_count from the full set
        cur.execute(
            """SELECT COUNT(*) as count
               FROM notifications
               WHERE user_id = %s AND read_at IS NULL""",
            (current_user.id,)
        )
        unread_count = (cur.fetchone() or {}).get('count', 0)

        # Dropdown should ONLY show unread, and only the most recent N
        cur.execute(
            """SELECT id, type, title, message, related_id, created_at, read_at
               FROM notifications
               WHERE user_id = %s AND read_at IS NULL
               ORDER BY created_at DESC
               LIMIT %s""",
            (current_user.id, limit),
        )

        notifications = cur.fetchall() or []

        formatted = []
        for notif in notifications:
            formatted.append({
                'id': notif['id'],
                'type': notif['type'],
                'title': notif['title'],
                'message': notif['message'],
                'related_id': notif['related_id'],
                'created_at': notif['created_at'].isoformat() if notif['created_at'] else None,
                'read_at': notif['read_at'].isoformat() if notif['read_at'] else None,
                'is_read': bool(notif['read_at'])
            })

        return jsonify({
            'unread_count': int(unread_count or 0),
            'notifications': formatted
        })
    finally:
        cur.close()
        conn.close()
