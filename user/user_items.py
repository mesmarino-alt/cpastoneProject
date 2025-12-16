# routes/user_items.py
from flask import Blueprint, request, redirect, url_for, flash
from flask_login import login_required, current_user
import pymysql.cursors
from db import get_db
from services.notifications import notify

user_items_bp = Blueprint('user_items', __name__)

@user_items_bp.route('/items/claim', methods=['POST'])
@login_required
def claim_item_from_modal():
    """
    Unified endpoint to claim lost or found items.
    Handles deduplication to prevent duplicate claims.
    
    Required form parameters:
    - item_id: ID of the item being claimed
    - item_type: 'lost' or 'found'
    - justification: User's explanation for the claim
    - match_id (optional): If claiming from a match, include this
    """
    print(f"\n[CLAIM] Starting claim submission...")
    print(f"[CLAIM] Request form data: {request.form}")
    print(f"[CLAIM] Current user: {current_user.id} ({current_user.name})")
    
    item_id      = request.form.get('item_id', type=int)
    item_type    = request.form.get('item_type', type=str).lower()  # Convert to lowercase
    justification = (request.form.get('justification') or '').strip()
    match_id     = request.form.get('match_id', type=int)   # optional

    print(f"[CLAIM] Parsed values - item_id: {item_id}, item_type: {item_type}, match_id: {match_id}")
    print(f"[CLAIM] Justification: {justification}")

    if not item_id or item_type not in ('lost', 'found'):
        print(f"[CLAIM] ERROR: Invalid claim request. item_id={item_id}, item_type={item_type}")
        flash('Invalid claim request.', 'danger')
        return redirect(url_for('user.dashboard'))

    # Determine which side of the claim this is
    lost_item_id  = item_id if item_type == 'lost' else None
    found_item_id = item_id if item_type == 'found' else None

    conn = get_db()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        # Deduplication Rule 1: If match_id is provided, check for existing pending claims on this match
        if match_id:
            print(f"[CLAIM] Checking for existing claims on match {match_id}...")
            cur.execute("""
                SELECT id FROM claims
                WHERE match_id=%s AND user_id=%s AND status='Pending'
                LIMIT 1
            """, (match_id, current_user.id))
            if cur.fetchone():
                print(f"[CLAIM] ERROR: User already has pending claim for match {match_id}")
                flash('You already have a pending claim for this match.', 'info')
                return redirect(url_for('user.dashboard'))
        
        # Deduplication Rule 2: Prevent duplicate pending claims for the same item(s)
        # This checks if user already has a pending claim involving this specific item
        print(f"[CLAIM] Checking for duplicate claims on item {item_id}...")
        cur.execute("""
            SELECT id FROM claims
            WHERE user_id=%s
              AND COALESCE(lost_item_id, 0) = COALESCE(%s, 0)
              AND COALESCE(found_item_id, 0) = COALESCE(%s, 0)
              AND status='Pending'
            LIMIT 1
        """, (current_user.id, lost_item_id, found_item_id))
        if cur.fetchone():
            print(f"[CLAIM] ERROR: User already has pending claim for this item")
            flash('You already have a pending claim for this item.', 'info')
            return redirect(url_for('user.dashboard'))

        # Get item details for notification
        if item_type == 'lost':
            cur.execute("SELECT name, user_id FROM lost_items WHERE id=%s", (item_id,))
        else:
            cur.execute("SELECT name, user_id FROM found_items WHERE id=%s", (item_id,))
        
        item_result = cur.fetchone()
        item_name = item_result.get('name') if item_result else 'Item'
        item_owner_id = item_result.get('user_id') if item_result else None
        print(f"[CLAIM] Item name: {item_name}, Item owner ID: {item_owner_id}")

        # Prevent users from claiming their own items
        if item_owner_id == current_user.id:
            print(f"[CLAIM] ERROR: User {current_user.id} tried to claim their own item {item_id}")
            flash('You cannot claim your own item!', 'warning')
            return redirect(url_for('user.dashboard'))

        # Insert the claim
        print(f"[CLAIM] Inserting claim into database...")
        print(f"[CLAIM] Values: match_id={match_id}, lost_item_id={lost_item_id}, found_item_id={found_item_id}, user_id={current_user.id}, justification={justification}")
        
        # If match_id is None, we need to handle it differently since the column doesn't allow NULL
        # Use 0 as a sentinel value for "no match" or create a logic to handle this
        if match_id is None:
            # Insert without match_id reference - just lost/found item claim
            cur.execute("""
                INSERT INTO claims (lost_item_id, found_item_id, user_id, status, justification, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, (lost_item_id, found_item_id, current_user.id, 'Pending', justification))
        else:
            # Insert with match_id reference
            cur.execute("""
                INSERT INTO claims (match_id, lost_item_id, found_item_id, user_id, status, justification, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """, (match_id, lost_item_id, found_item_id, current_user.id, 'Pending', justification))
        
        print(f"[CLAIM] Execute completed, committing...")
        conn.commit()
        print(f"[CLAIM] ✓ Claim inserted successfully")

        # Get the inserted claim ID
        cur.execute("SELECT LAST_INSERT_ID() as claim_id")
        result = cur.fetchone()
        claim_id = result.get('claim_id') if isinstance(result, dict) else result[0]
        print(f"[CLAIM] New claim ID: {claim_id}")
        
        # Verify the claim was inserted
        cur.execute("SELECT id, user_id, status FROM claims WHERE id=%s", (claim_id,))
        verification = cur.fetchone()
        print(f"[CLAIM] Verification - Claim exists: {verification}")

        # Update item status to "Claimed" to indicate a claim is pending
        print(f"[CLAIM] Updating item {item_id} status to 'Claimed'...")
        if item_type == 'found':
            cur.execute("UPDATE found_items SET status='Claimed' WHERE id=%s", (item_id,))
        else:
            cur.execute("UPDATE lost_items SET status='Claimed' WHERE id=%s", (item_id,))
        conn.commit()
        print(f"[CLAIM] ✓ Item status updated to 'Claimed'")

        # Notify admins
        print(f"[CLAIM] Fetching admins for notification...")
        cur.execute("SELECT id FROM users WHERE role='admin'")
        admins = cur.fetchall()
        print(f"[CLAIM] Found {len(admins)} admin(s)")
        
        title = 'New Claim Submitted 📝'
        message = f'User {current_user.name} submitted a claim on {item_type} item: "{item_name}".'
        for admin in admins:
            admin_id = admin.get('id') if isinstance(admin, dict) else admin[0]
            print(f"[CLAIM] Notifying admin {admin_id}...")
            notify(user_id=admin_id, notification_type='new_claim', title=title, message=message, related_id=claim_id)

        print(f"[CLAIM] ✓ Claim submission complete! Claim ID: {claim_id}")
        flash('Your claim has been submitted and is pending review.', 'success')
        return redirect(url_for('user.dashboard'))

    except Exception as e:
        conn.rollback()
        print(f"[CLAIM] ERROR: {str(e)}")
        import traceback
        print(traceback.format_exc())
        flash(f"Error submitting claim: {str(e)}", 'danger')
        return redirect(url_for('user.dashboard'))
    finally:
        cur.close()
        conn.close()
