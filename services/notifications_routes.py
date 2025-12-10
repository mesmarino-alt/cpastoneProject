from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
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
    """Display all notifications for the current user"""
    notifications = get_recent_notifications(current_user.id, limit=50)
    return render_template('user/notifications.html', notifications=notifications)

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
    """API endpoint to get recent notifications (for AJAX/dropdown)"""
    limit = request.args.get('limit', 10, type=int)
    notifications = get_recent_notifications(current_user.id, limit=limit)
    
    # Format notifications for JSON response
    formatted = []
    for notif in notifications:
        formatted.append({
            'id': notif.get('id') if isinstance(notif, dict) else notif[0],
            'type': notif.get('type') if isinstance(notif, dict) else notif[1],
            'title': notif.get('title') if isinstance(notif, dict) else notif[2],
            'message': notif.get('message') if isinstance(notif, dict) else notif[3],
            'related_id': notif.get('related_id') if isinstance(notif, dict) else notif[4],
            'created_at': str(notif.get('created_at') if isinstance(notif, dict) else notif[5]),
            'read_at': str(notif.get('read_at') if isinstance(notif, dict) else notif[6]) if (notif.get('read_at') if isinstance(notif, dict) else notif[6]) else None,
            'is_read': bool(notif.get('read_at') if isinstance(notif, dict) else notif[6])
        })
    
    return jsonify({
        'unread_count': sum(1 for n in formatted if not n['is_read']),
        'notifications': formatted
    })
