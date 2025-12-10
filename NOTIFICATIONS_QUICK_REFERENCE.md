# 🚀 NOTIFICATION SYSTEM - DEVELOPER QUICK REFERENCE

## 📌 At a Glance

**What it does:** Automatically notifies users when admins approve/reject claims and notifies admins when users submit claims.

**Where it is:** 
- Service: `services/notifications.py`
- Routes: `services/notifications_routes.py`
- UI: `templates/partials/notification_bell.html` + `templates/user/notifications.html`

**How to use it:**
```python
from services.notifications import notify

# Send a notification
notify(
    user_id=7,                                    # Who gets it
    notification_type='claim_approved',           # Type
    title='Claim Approved! ✅',                  # Display title
    message='Your claim has been approved...',    # Full message
    related_id=42                                 # Optional: link to claim
)
```

---

## 🔗 Integration Points

### **Admin Approves Claim**
📍 File: `admin/admin_claims.py` → `claim_approve()` function

```python
# Line ~70 in the approve function:
notify(
    user_id=claimant_user_id,
    notification_type='claim_approved',
    title='Claim Approved! ✅',
    message=f'Your claim for "{lost_name}" has been approved...',
    related_id=claim_id
)
```

### **Admin Rejects Claim**
📍 File: `admin/admin_claims.py` → `claim_reject()` function

```python
# Line ~130 in the reject function:
notify(
    user_id=claimant_user_id,
    notification_type='claim_rejected',
    title='Claim Rejected ❌',
    message=f'Your claim for "{lost_name}" has been rejected.',
    related_id=claim_id
)
```

### **User Submits Claim**
📍 File: `user/user_matches.py` → `submit_claim()` function

```python
# Line ~85 in the submit function:
FOR EACH admin:
    notify(
        user_id=admin_id,
        notification_type='new_claim',
        title='New Claim Submitted 📝',
        message=f'User {current_user.name} submitted a claim...',
        related_id=claim_id
    )
```

---

## 🎯 Template Usage

### **Show Unread Count**
```html
{{ notifications.unread_count }}
<!-- Shows: 3 -->
```

### **Show Recent Notifications**
```html
{% for notif in notifications.recent_notifications %}
    <div>{{ notif.title }}</div>
{% endfor %}
```

### **Include Notification Bell**
```html
{% include 'partials/notification_bell.html' %}
```

### **Check if Has Unread**
```html
{% if notifications.unread_count > 0 %}
    <span class="badge">{{ notifications.unread_count }}</span>
{% endif %}
```

---

## 🔌 API Endpoints

### **View All Notifications**
```
GET /notifications/
Response: HTML page
```

### **Mark Single as Read**
```
POST /notifications/5/read
Response: Redirect or JSON { "success": true }
```

### **Mark All as Read**
```
POST /notifications/mark-all-read
Response: Redirect or JSON { "success": true }
```

### **Delete Notification**
```
POST /notifications/5/delete
Response: Redirect or JSON { "success": true }
```

### **Get Recent (AJAX)**
```
GET /notifications/api/recent?limit=10
Response: JSON {
    "unread_count": 2,
    "notifications": [
        {
            "id": 1,
            "type": "claim_approved",
            "title": "Claim Approved! ✅",
            "message": "Your claim...",
            "created_at": "2025-12-04 10:30:00",
            "is_read": false
        }
    ]
}
```

---

## 📊 Database Query Examples

### **Get Unread Count for User**
```sql
SELECT COUNT(*) FROM notifications 
WHERE user_id=7 AND read_at IS NULL;
```

### **Get All Recent**
```sql
SELECT * FROM notifications 
WHERE user_id=7 
ORDER BY read_at IS NULL DESC, created_at DESC 
LIMIT 5;
```

### **Get Unread First**
```sql
SELECT * FROM notifications 
WHERE user_id=7 
ORDER BY read_at IS NULL DESC, created_at DESC;
```

### **Mark All as Read**
```sql
UPDATE notifications 
SET read_at=NOW() 
WHERE user_id=7 AND read_at IS NULL;
```

### **Delete Notification**
```sql
DELETE FROM notifications 
WHERE id=5 AND user_id=7;
```

---

## 🐛 Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| Notification bell not showing | User not logged in | Check `current_user.is_authenticated` |
| Badge not updating | Cache or need refresh | Clear browser cache, F5 refresh |
| Notifications not appearing | notify() not called | Add debug prints to verify function runs |
| Database error | notifications table missing | Run: `CREATE TABLE notifications (...)` |
| Import error | Module path wrong | Verify file paths in imports |
| Timestamp shows incorrectly | Date format issue | Use `.strftime('%b %d, %Y')` in template |

---

## ✅ Testing Checklist

```python
# Test 1: Send notification
from services.notifications import notify
notify(7, 'test', 'Test Title', 'Test Message', 1)

# Test 2: Get count
from services.notifications import get_unread_count
count = get_unread_count(7)
assert count >= 1

# Test 3: Get recent
from services.notifications import get_recent_notifications
notifs = get_recent_notifications(7, 5)
assert len(notifs) > 0

# Test 4: Mark as read
from services.notifications import mark_as_read
mark_as_read(notifs[0][0], 7)

# Test 5: Verify count decreased
count = get_unread_count(7)
assert count == 0
```

---

## 📝 Adding a New Notification Type

### Step 1: Add to notification sending code
```python
# In admin/admin_claims.py or user/user_matches.py:
notify(
    user_id=user_id,
    notification_type='your_new_type',
    title='Your Title Here',
    message='Your message here',
    related_id=item_id
)
```

### Step 2: Add icon in notification_bell.html
```html
{% elif notif.type == 'your_new_type' %}
  <i class="bi bi-your-icon text-your-color"></i>
```

### Step 3: Add badge style in notifications.html
```html
{% elif notif.type == 'your_new_type' %}
  <span class="badge bg-your-color me-2">
    <i class="bi bi-your-icon"></i> Your Label
  </span>
```

---

## 🎨 Notification Type Colors

| Type | Color | Icon |
|------|-------|------|
| `claim_approved` | `bg-success` (green) | `bi-check-circle` ✅ |
| `claim_rejected` | `bg-danger` (red) | `bi-x-circle` ❌ |
| `new_claim` | `bg-info` (blue) | `bi-file-earmark-check` 📝 |
| `item_match` | `bg-warning` (yellow) | `bi-link-45deg` 🔗 |
| `claim_update` | `bg-secondary` (gray) | `bi-info-circle` ℹ️ |

---

## 🔄 Data Flow Quick Diagram

```
User/Admin Action
        ↓
Route Handler (admin_claims.py / user_matches.py)
        ↓
notify(user_id, type, title, message, related_id)
        ↓
INSERT INTO notifications
        ↓
User/Admin refreshes page
        ↓
Context Processor: get_unread_count() + get_recent_notifications()
        ↓
Template: {{ notifications.unread_count }}, {{ notifications.recent_notifications }}
        ↓
UI Update: Badge appears, Bell updates, Dropdown shows
```

---

## 📦 What Gets Injected Into Templates

**Every template has access to:**
```python
notifications = {
    'unread_count': int,                    # Number: 0, 1, 2, ...
    'recent_notifications': [               # List of dicts:
        {
            'id': int,
            'user_id': int,
            'type': str,                     # 'claim_approved', etc
            'title': str,
            'message': str,
            'related_id': int,
            'created_at': datetime,
            'read_at': datetime or None
        },
        # ... up to 5 items
    ]
}
```

---

## 🚀 Performance Tips

1. **Limit Recent Notifications**
   - Default: 5 notifications
   - Change in context processor if needed
   - Balances UI performance with functionality

2. **Add Indexes**
   ```sql
   CREATE INDEX idx_user_read ON notifications(user_id, read_at);
   CREATE INDEX idx_user_created ON notifications(user_id, created_at DESC);
   ```

3. **Archive Old Notifications**
   ```sql
   DELETE FROM notifications 
   WHERE read_at < DATE_SUB(NOW(), INTERVAL 30 DAY);
   ```

4. **Cache Unread Count** (Future enhancement)
   - Use Redis for faster lookups
   - Invalidate cache on new notification

---

## 📞 Function Reference

### `notify(user_id, notification_type, title, message, related_id=None)`
Insert a notification into the database.
- Returns: `True` on success, `False` on error
- Logs success/error to console

### `get_unread_count(user_id)`
Get count of unread notifications for a user.
- Returns: Integer count
- Returns: 0 if error

### `get_recent_notifications(user_id, limit=10)`
Get recent notifications (unread first).
- Returns: List of notification records
- Returns: Empty list if error

### `mark_as_read(notification_id, user_id)`
Mark a single notification as read.
- Returns: `True` on success, `False` on error

### `mark_all_as_read(user_id)`
Mark all notifications as read for a user.
- Returns: `True` on success, `False` on error

### `get_notification_by_id(notification_id, user_id)`
Get a specific notification (security check included).
- Returns: Notification record or `None`

### `delete_notification(notification_id, user_id)`
Delete a notification (security check included).
- Returns: `True` on success, `False` on error

---

## 🎯 Key Points to Remember

✅ **Notifications are automatic** - No manual triggering needed
✅ **Database-first approach** - All data persisted immediately
✅ **Context processor magic** - Data available everywhere
✅ **Security built-in** - user_id checks prevent unauthorized access
✅ **Bootstrap icons** - Uses Bootstrap Icons library for icons
✅ **Responsive design** - Works on mobile and desktop
✅ **Scalable structure** - Easy to add new notification types
✅ **Error handling** - Graceful failures with logging

---

## 🎓 Learning Resources

- **Bootstrap Icons**: https://icons.getbootstrap.com/
- **Flask Context Processors**: https://flask.palletsprojects.com/
- **Bootstrap Dropdowns**: https://getbootstrap.com/docs/5.3/components/dropdowns/
- **MySQL Timestamps**: https://dev.mysql.com/doc/refman/8.0/en/datetime.html

---

**Need help? Check the implementation files:**
- Sending: `services/notifications.py`
- Routes: `services/notifications_routes.py`
- UI: `templates/partials/notification_bell.html`
- Page: `templates/user/notifications.html`

**Ready to extend? Start in one of these files:**
- Add trigger: `admin/admin_claims.py` or `user/user_matches.py`
- Add UI: `templates/partials/notification_bell.html`
- Add API: `services/notifications_routes.py`
