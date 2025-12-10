import json
from datetime import datetime
from db import get_db

def notify(user_id, notification_type, title, message, related_id=None):
    """
    Insert a notification into the database for a specific user.
    """
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO notifications (user_id, type, title, message, related_id, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (user_id, notification_type, title, message, related_id))
        conn.commit()
        print(f"[NOTIFY] Sent to user {user_id}: {title}")
        return True
    except Exception as e:
        conn.rollback()
        print(f"[NOTIFY] ERROR: {e}")
        return False
    finally:
        cur.close()
        conn.close()


def get_unread_count(user_id):
    """Return count of unread notifications for a user."""
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT COUNT(*) AS count
            FROM notifications
            WHERE user_id = %s AND read_at IS NULL
        """, (user_id,))
        result = cur.fetchone()
        # Result is a dict since connection uses DictCursor
        return result.get('count') if result else 0
    except Exception as e:
        print(f"[GET_UNREAD_COUNT] ERROR: {e}")
        return 0
    finally:
        cur.close()
        conn.close()


def get_recent_notifications(user_id, limit=10):
    """Return recent notifications for a user (unread first)."""
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, type, title, message, related_id, created_at, read_at
            FROM notifications
            WHERE user_id = %s
            ORDER BY read_at IS NULL DESC, created_at DESC
            LIMIT %s
        """, (user_id, limit))
        return cur.fetchall() or []
    except Exception as e:
        print(f"[GET_RECENT_NOTIFICATIONS] ERROR: {e}")
        return []
    finally:
        cur.close()
        conn.close()


def mark_as_read(notification_id, user_id):
    """Mark a single notification as read."""
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE notifications
            SET read_at = NOW()
            WHERE id = %s AND user_id = %s
        """, (notification_id, user_id))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        conn.rollback()
        print(f"[MARK_AS_READ] ERROR: {e}")
        return False
    finally:
        cur.close()
        conn.close()


def mark_all_as_read(user_id):
    """Mark all notifications as read for a user."""
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE notifications
            SET read_at = NOW()
            WHERE user_id = %s AND read_at IS NULL
        """, (user_id,))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        conn.rollback()
        print(f"[MARK_ALL_AS_READ] ERROR: {e}")
        return False
    finally:
        cur.close()
        conn.close()


def get_notification_by_id(notification_id, user_id):
    """Fetch a specific notification by ID."""
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, type, title, message, related_id, created_at, read_at
            FROM notifications
            WHERE id = %s AND user_id = %s
        """, (notification_id, user_id))
        return cur.fetchone()
    except Exception as e:
        print(f"[GET_NOTIFICATION_BY_ID] ERROR: {e}")
        return None
    finally:
        cur.close()
        conn.close()


def delete_notification(notification_id, user_id):
    """Delete a notification."""
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            DELETE FROM notifications
            WHERE id = %s AND user_id = %s
        """, (notification_id, user_id))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        conn.rollback()
        print(f"[DELETE_NOTIFICATION] ERROR: {e}")
        return False
    finally:
        cur.close()
        conn.close()
