# 🔔 Notification System - Complete Implementation Guide

## Overview
A full-featured notification system has been implemented to handle admin-to-user and user-to-admin communications for claim approvals, rejections, and submissions.

---

## 📁 Files Created/Modified

### 1. **Core Service Layer**
- **`services/notifications.py`** - Notification business logic
  - `notify()` - Insert notifications
  - `get_unread_count()` - Count unread notifications
  - `get_recent_notifications()` - Fetch recent notifications
  - `mark_as_read()` - Mark single notification as read
  - `mark_all_as_read()` - Mark all as read
  - `get_notification_by_id()` - Get specific notification
  - `delete_notification()` - Delete notification

### 2. **Routes Layer**
- **`services/notifications_routes.py`** - Notification API endpoints
  - `GET /notifications/` - View all notifications page
  - `POST /notifications/<id>/read` - Mark as read
  - `POST /notifications/mark-all-read` - Mark all as read
  - `POST /notifications/<id>/delete` - Delete notification
  - `GET /notifications/api/recent` - AJAX API for recent notifications

### 3. **Trigger Integration**
- **`admin/admin_claims.py`** - Updated to send notifications:
  - When admin approves claim → `claim_approved` notification to claimant
  - When admin rejects claim → `claim_rejected` notification to claimant + other rejected claimants
  
- **`user/user_matches.py`** - Updated to send notifications:
  - When user submits claim → `new_claim` notification to all admins

### 4. **UI Components**
- **`project/templates/partials/notification_bell.html`** - Notification bell dropdown
  - Shows unread count badge
  - Lists 5 most recent notifications
  - Mark as read / Delete buttons
  - Link to full notifications page
  
- **`project/templates/user/notifications.html`** - Full notifications page
  - All notifications with type-based badges
  - Timestamps and read status
  - Bulk "Mark all read" action

### 5. **Layout Integration**
- **`project/templates/layouts/base_user_dashboard.html`** - Updated navbar
  - Includes notification bell in sidebar
  - Links to notifications page

### 6. **Application Setup**
- **`app.py`** - Updated to:
  - Register `notifications_bp` blueprint
  - Add context processor to inject notification data into all templates

---

## 🔄 Notification Flow Diagram

### **Admin Approves Claim**
```
Admin clicks "Approve" on claim
    ↓
admin_claims.py::claim_approve()
    ↓
UPDATE claims SET status='Approved'
UPDATE lost_items SET status='Recovered'
UPDATE found_items SET status='Returned'
    ↓
notify(claimant_user_id, 'claim_approved', ...)
    ↓
INSERT INTO notifications
    ↓
Claimant sees:
  - Bell badge +1
  - Notification in dropdown
  - Full notification on /notifications/ page
```

### **Admin Rejects Claim**
```
Admin clicks "Reject" on claim
    ↓
admin_claims.py::claim_reject()
    ↓
UPDATE claims SET status='Rejected'
    ↓
notify(claimant_user_id, 'claim_rejected', ...)
    ↓
INSERT INTO notifications
    ↓
Claimant sees notification
```

### **User Submits Claim**
```
User fills justification & clicks "Claim"
    ↓
user_matches.py::submit_claim()
    ↓
INSERT INTO claims (status='Pending')
    ↓
GET all admin users
    ↓
FOR EACH admin:
  notify(admin_user_id, 'new_claim', ...)
    ↓
INSERT INTO notifications (for each admin)
    ↓
All admins see:
  - Bell badge +1
  - "New Claim Submitted" in dropdown
```

---

## 📊 Database Schema

**notifications table** (already exists):
```sql
CREATE TABLE notifications (
  id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  user_id INT UNSIGNED NOT NULL,
  type VARCHAR(50) NOT NULL,
  title VARCHAR(150) NOT NULL,
  message TEXT NOT NULL,
  related_id INT UNSIGNED,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  read_at DATETIME,
  FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**Notification Types:**
- `claim_approved` - Admin approved user's claim
- `claim_rejected` - Admin rejected user's claim
- `new_claim` - User submitted new claim (sent to admins)
- `item_match` - New item match found
- `claim_update` - Claim status update (generic)

---

## 🎯 Context Processor

**In `app.py`:**
```python
@app.context_processor
def inject_notifications():
    """Inject notification data into ALL templates"""
    if current_user.is_authenticated:
        return {
            'notifications': {
                'unread_count': get_unread_count(current_user.id),
                'recent_notifications': get_recent_notifications(current_user.id, limit=5)
            }
        }
    return {'notifications': {'unread_count': 0, 'recent_notifications': []}}
```

**Available in all templates as:**
- `{{ notifications.unread_count }}` - Number of unread notifications
- `{{ notifications.recent_notifications }}` - List of 5 most recent notifications

---

## 🎨 UI Components

### Notification Bell
- **Location:** Sidebar in user dashboard
- **Features:**
  - Red badge showing unread count
  - Dropdown with 5 most recent notifications
  - Notification type icons (✅ Approved, ❌ Rejected, 📝 New Claim)
  - Mark as read / Delete buttons
  - Link to full notifications page

### Notifications Page
- **URL:** `/notifications/`
- **Features:**
  - Full list of all notifications
  - Color-coded badges by type
  - Created and read timestamps
  - Bulk "Mark all read" button
  - Delete individual notifications
  - Empty state message

---

## 🚀 How to Use

### For Admins
1. Go to `/admin/claims/` to review claims
2. Click **Approve** or **Reject** button
3. System automatically sends notification to claimant
4. Click notification bell to see incoming new claims

### For Users/Claimants
1. Submit a claim on `/user/matches/`
2. System automatically sends notification to all admins
3. Check notification bell for status updates
4. Visit `/notifications/` to see all notifications

### API Usage
**Get recent notifications (AJAX):**
```bash
GET /notifications/api/recent?limit=10
Response: {
  "unread_count": 2,
  "notifications": [
    {
      "id": 1,
      "type": "claim_approved",
      "title": "Claim Approved! ✅",
      "message": "Your claim has been approved...",
      "related_id": 42,
      "created_at": "2025-12-04 10:30:00",
      "is_read": false
    }
  ]
}
```

---

## ✅ Testing Checklist

- [ ] User submits claim → Admin receives notification
- [ ] Admin approves claim → Claimant receives "approved" notification
- [ ] Admin rejects claim → Claimant receives "rejected" notification
- [ ] Notification bell shows unread count
- [ ] Notification dropdown displays recent notifications
- [ ] Mark as read button works
- [ ] Delete button works
- [ ] Mark all read button works
- [ ] Notifications page displays all notifications
- [ ] Timestamps format correctly

---

## 🔧 Future Enhancements

1. **Real-time Updates**
   - WebSocket integration for instant notifications
   - Polling fallback for older browsers

2. **Email Notifications**
   - Send email when important notifications arrive
   - Digest emails for daily summaries

3. **Notification Preferences**
   - Let users choose which types to receive
   - Set notification delivery frequency

4. **Notification Categories**
   - Group by type (Claims, Items, System)
   - Filter by category

5. **Audit Trail**
   - Log who triggered each notification
   - Track notification delivery

6. **Rich Notifications**
   - Include claim/item preview in notification
   - Direct action buttons (Approve/Reject inline)

---

## 📝 Notes

- Notifications are created in the database immediately
- Context processor runs on every page load for authenticated users
- Notification bell is only shown to authenticated users
- All notification timestamps use server timezone
- Notifications can be marked as read without deletion
- Unread notifications show with blue left border in full list
