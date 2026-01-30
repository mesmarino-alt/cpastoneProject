# routes/admin_claims.py
from flask import Blueprint, render_template, request, redirect, session, url_for, flash
from flask_login import login_required, current_user
from db import get_db
import pymysql.cursors
from services.notifications import notify

admin_claims_bp = Blueprint('admin_claims', __name__, url_prefix='/admin/claims', )

def admin_required():
    return current_user.is_authenticated and current_user.is_admin()

@admin_claims_bp.before_request
def guard_admin():
    if not admin_required():
        return redirect(url_for('user.dashboard'))

@admin_claims_bp.route('/', methods=['GET'])
@login_required
def claims_page():
    status_filter = request.args.get('status')

    conn = get_db()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        # Fetch claims - use LEFT JOINs to handle claims that may not have both lost and found items
        sql = """
            SELECT 
                c.id AS claim_id, c.status, c.justification, c.created_at,
                c.match_id, c.user_id AS claimant_user_id,
                c.lost_item_id, c.found_item_id,
                li.id AS lost_id, li.name AS lost_name, li.description AS lost_desc, li.photo AS lost_photo,
                fi.id AS found_id, fi.name AS found_name, fi.description AS found_desc, fi.photo AS found_photo,
                u.name AS claimant_name, u.email AS claimant_email
            FROM claims c
            LEFT JOIN lost_items li ON li.id = c.lost_item_id
            LEFT JOIN found_items fi ON fi.id = c.found_item_id
            LEFT JOIN users u ON u.id = c.user_id
        """
        params = []
        if status_filter:
            sql += " WHERE c.status = %s"
            params.append(status_filter)
        sql += " ORDER BY c.created_at DESC"

        if params:
            cur.execute(sql, tuple(params))
        else:
            cur.execute(sql)
        claims = cur.fetchall()

        # Count pending claims
        cur.execute("SELECT COUNT(*) AS cnt FROM claims WHERE status = 'Pending'")
        pending_count = cur.fetchone()["cnt"]

        # Fetch available lost items (for linking to direct claims that have found items)
        cur.execute("""
            SELECT id, name FROM lost_items 
            WHERE status IN ('Pending', 'Claimed')
            ORDER BY name ASC
        """)
        available_lost_items = cur.fetchall()

        # Fetch available found items (for linking to direct claims that have lost items)
        cur.execute("""
            SELECT id, name FROM found_items 
            WHERE status IN ('Pending', 'Claimed')
            ORDER BY name ASC
        """)
        available_found_items = cur.fetchall()

    except Exception as e:
        print(f"[CLAIMS PAGE] ERROR: {str(e)}")
        import traceback; traceback.print_exc()
        claims = []
        pending_count = 0
        available_lost_items = []
        available_found_items = []
    finally:
        cur.close()
        conn.close()

    # 🔴 Mark claims as seen when visiting this page
    session['claims_seen'] = True

    return render_template(
        'admin/claims.html',
        claims=claims,
        status_filter=status_filter,
        pending_count=pending_count,
        available_lost_items=available_lost_items,
        available_found_items=available_found_items
    )

@admin_claims_bp.route('/<int:claim_id>/approve', methods=['POST'])
@login_required
def claim_approve(claim_id):
    """Approve a claim and update item statuses"""
    print(f"\n[CLAIM APPROVE] Admin {current_user.id} approving claim {claim_id}")
    
    conn = get_db()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        # Get claim + related items + claimant info - use LEFT JOINs to handle direct item claims
        cur.execute("""
            SELECT c.id, c.match_id, c.lost_item_id, c.found_item_id, c.status, c.user_id,
                   li.name as lost_name, li.status as lost_status, fi.name as found_name, fi.status as found_status
            FROM claims c
            LEFT JOIN lost_items li ON li.id = c.lost_item_id
            LEFT JOIN found_items fi ON fi.id = c.found_item_id
            WHERE c.id=%s LIMIT 1
        """, (claim_id,))
        claim = cur.fetchone()
        
        if not claim:
            flash('Claim not found.', 'warning')
            return redirect(url_for('admin_claims.claims_page'))
        
        status = claim.get('status')
        if status != 'Pending':
            flash('Invalid claim or already processed.', 'warning')
            return redirect(url_for('admin_claims.claims_page'))

        claimant_user_id = claim.get('user_id')
        lost_name = claim.get('lost_name') or 'item'
        lost_id = claim.get('lost_item_id')
        found_id = claim.get('found_item_id')
        match_id = claim.get('match_id')
        
        print(f"[CLAIM APPROVE] Claim status: {status}, Lost ID: {lost_id}, Found ID: {found_id}")
        print(f"[CLAIM APPROVE] Lost status: {claim.get('lost_status')}, Found status: {claim.get('found_status')}")
        
        # Update claim status first
        cur.execute("UPDATE claims SET status='Approved' WHERE id=%s", (claim_id,))
        print(f"[CLAIM APPROVE] Updated claim status to 'Approved'")

        # Update items status to 'reviewed' (indicates both report and claim approved)
        if lost_id:
            cur.execute("UPDATE lost_items SET status=%s WHERE id=%s", ('reviewed', lost_id))
            print(f"[CLAIM APPROVE] Updated lost_items {lost_id} status to 'reviewed'")
            
        if found_id:
            cur.execute("UPDATE found_items SET status=%s WHERE id=%s", ('reviewed', found_id))
            print(f"[CLAIM APPROVE] Updated found_items {found_id} status to 'reviewed'")

        # Reject other pending claims for this match (if match_id exists)
        if match_id:
            cur.execute("""
                UPDATE claims SET status='Rejected'
                WHERE match_id=%s AND id<>%s AND status='Pending'
            """, (match_id, claim_id))
            print(f"[CLAIM APPROVE] Rejected other pending claims for match {match_id}")

        conn.commit()
        print(f"[CLAIM APPROVE] Transaction committed")

        # --- Post-commit diagnostics ---
        try:
            # Check for any triggers on the item tables that might reset status
            cur.execute("""
                SELECT TRIGGER_NAME, EVENT_MANIPULATION, ACTION_STATEMENT
                FROM information_schema.TRIGGERS
                WHERE TRIGGER_SCHEMA = DATABASE()
                  AND EVENT_OBJECT_TABLE IN ('lost_items','found_items')
            """)
            triggers = cur.fetchall()
            print(f"[CLAIM APPROVE] DB triggers affecting lost_items/found_items: {triggers}")
        except Exception as e:
            print(f"[CLAIM APPROVE] Could not read triggers: {e}")

        # Re-check statuses using a fresh connection (in case some external process/trigger runs after commit)
        import time
        time.sleep(0.8)
        try:
            conn2 = get_db()
            cur2 = conn2.cursor(pymysql.cursors.DictCursor)
            if lost_id:
                cur2.execute("SELECT id, status FROM lost_items WHERE id=%s", (lost_id,))
                row = cur2.fetchone()
                print(f"[CLAIM APPROVE] Post-commit check (fresh conn) - Lost item {lost_id}: {row}")
                if not row or not row.get('status'):
                    print(f"[CLAIM APPROVE] WARNING: Lost item {lost_id} status is empty after commit. Attempting forced update...")
                    try:
                        cur2.execute("UPDATE lost_items SET status=CAST(%s AS CHAR) WHERE id=%s", ('reviewed', lost_id))
                        conn2.commit()
                        cur2.execute("SELECT id, status FROM lost_items WHERE id=%s", (lost_id,))
                        row2 = cur2.fetchone()
                        print(f"[CLAIM APPROVE] After forced update - Lost item {lost_id}: {row2}")
                    except Exception as e:
                        print(f"[CLAIM APPROVE] Forced update failed for lost_items {lost_id}: {e}")

            if found_id:
                cur2.execute("SELECT id, status FROM found_items WHERE id=%s", (found_id,))
                row = cur2.fetchone()
                print(f"[CLAIM APPROVE] Post-commit check (fresh conn) - Found item {found_id}: {row}")
                if not row or not row.get('status'):
                    print(f"[CLAIM APPROVE] WARNING: Found item {found_id} status is empty after commit. Attempting forced update...")
                    try:
                        cur2.execute("UPDATE found_items SET status=CAST(%s AS CHAR) WHERE id=%s", ('reviewed', found_id))
                        conn2.commit()
                        cur2.execute("SELECT id, status FROM found_items WHERE id=%s", (found_id,))
                        row2 = cur2.fetchone()
                        print(f"[CLAIM APPROVE] After forced update - Found item {found_id}: {row2}")
                    except Exception as e:
                        print(f"[CLAIM APPROVE] Forced update failed for found_items {found_id}: {e}")
        except Exception as e:
            print(f"[CLAIM APPROVE] Post-commit fresh-connection check failed: {e}")
        finally:
            try:
                cur2.close(); conn2.close()
            except Exception:
                pass
        
        # Verify the updates were successful
        if lost_id:
            cur.execute("SELECT status FROM lost_items WHERE id=%s", (lost_id,))
            result = cur.fetchone()
            actual_status = result.get('status') if result else None
            print(f"[CLAIM APPROVE] Verification - Lost item {lost_id} status is now: '{actual_status}'")
            
        if found_id:
            cur.execute("SELECT status FROM found_items WHERE id=%s", (found_id,))
            result = cur.fetchone()
            actual_status = result.get('status') if result else None
            print(f"[CLAIM APPROVE] Verification - Found item {found_id} status is now: '{actual_status}'")
        
        # Send notification to claimant
        notify(
            user_id=claimant_user_id,
            notification_type='claim_approved',
            title='Claim Approved! ✅',
            message=f'Your claim for "{lost_name}" has been approved. The item will be returned to you shortly.',
            related_id=claim_id
        )
        
        # Send notification to other rejected claimants for this match
        if match_id:
            cur.execute("""
                SELECT DISTINCT user_id FROM claims
                WHERE match_id=%s AND id<>%s AND status='Rejected'
            """, (match_id, claim_id))
            rejected_claimants = cur.fetchall()
            for claimant in rejected_claimants:
                rejected_user_id = claimant.get('user_id')
                notify(
                    user_id=rejected_user_id,
                    notification_type='claim_rejected',
                    title='Claim Rejected ❌',
                    message='Your claim has been rejected. Another claimant was approved for this item.',
                    related_id=claim_id
                )
        
        flash('Claim approved successfully.', 'success')
        print(f"[CLAIM APPROVE] ✓ Claim {claim_id} approved. Notifications sent.")
    except Exception as e:
        conn.rollback()
        flash(f'Error approving claim: {str(e)}', 'danger')
        print(f"[CLAIM APPROVE] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('admin_claims.claims_page'))


@admin_claims_bp.route('/<int:claim_id>/reject', methods=['POST'])
@login_required
def claim_reject(claim_id):
    """Reject a claim"""
    print(f"\n[CLAIM REJECT] Admin {current_user.id} rejecting claim {claim_id}")
    
    reason = request.form.get('reason', '').strip()
    conn = get_db()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cur.execute("""
            SELECT c.id, c.status, c.user_id, li.name as lost_name, fi.name as found_name
            FROM claims c
            LEFT JOIN lost_items li ON li.id = c.lost_item_id
            LEFT JOIN found_items fi ON fi.id = c.found_item_id
            WHERE c.id=%s LIMIT 1
        """, (claim_id,))
        claim = cur.fetchone()
        
        if not claim:
            flash('Claim not found.', 'warning')
            return redirect(url_for('admin_claims.claims_page'))
        
        status = claim.get('status')
        if status != 'Pending':
            flash('Invalid claim or already processed.', 'warning')
            return redirect(url_for('admin_claims.claims_page'))

        claimant_user_id = claim.get('user_id')
        lost_name = claim.get('lost_name') or claim.get('found_name') or 'item'

        cur.execute("UPDATE claims SET status='Rejected' WHERE id=%s", (claim_id,))
        conn.commit()
        
        # Send notification to claimant
        message = f'Your claim for "{lost_name}" has been rejected.'
        if reason:
            message += f' Reason: {reason}'
        
        notify(
            user_id=claimant_user_id,
            notification_type='claim_rejected',
            title='Claim Rejected ❌',
            message=message,
            related_id=claim_id
        )
        
        flash('Claim rejected.', 'info')
        print(f"[CLAIM REJECT] ✓ Claim {claim_id} rejected. Notification sent to claimant.")
    except Exception as e:
        conn.rollback()
        flash(f'Error rejecting claim: {str(e)}', 'danger')
        print(f"[CLAIM REJECT] ERROR: {str(e)}")
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('admin_claims.claims_page'))

@admin_claims_bp.route('/<int:claim_id>/link-item', methods=['POST'])
@login_required
def link_claim_to_item(claim_id):
    """Link a direct claim to a matching item (for claims that only have one side)"""
    print(f"\n[LINK CLAIM] Admin {current_user.id} linking claim {claim_id} to item")
    
    item_id = request.form.get('item_id', type=int)
    item_type = request.form.get('item_type', type=str).lower()  # 'lost' or 'found'
    
    if not item_id or item_type not in ('lost', 'found'):
        flash('Invalid item selection.', 'danger')
        return redirect(url_for('admin_claims.claims_page'))
    
    conn = get_db()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        # Get current claim state
        cur.execute("""
            SELECT c.id, c.lost_item_id, c.found_item_id, c.status
            FROM claims c
            WHERE c.id=%s LIMIT 1
        """, (claim_id,))
        claim = cur.fetchone()
        
        if not claim:
            flash('Claim not found.', 'warning')
            return redirect(url_for('admin_claims.claims_page'))
        
        lost_item_id = claim.get('lost_item_id')
        found_item_id = claim.get('found_item_id')
        
        # Validate: can only link if one side is missing
        if (item_type == 'lost' and lost_item_id) or (item_type == 'found' and found_item_id):
            flash('This claim already has a linked item on that side.', 'warning')
            return redirect(url_for('admin_claims.claims_page'))
        
        # Verify item exists
        table = 'lost_items' if item_type == 'lost' else 'found_items'
        cur.execute(f"SELECT id, name FROM {table} WHERE id=%s", (item_id,))
        item = cur.fetchone()
        
        if not item:
            flash(f'{item_type.title()} item not found.', 'warning')
            return redirect(url_for('admin_claims.claims_page'))
        
        item_name = item.get('name')
        
        # Link the item to the claim
        if item_type == 'lost':
            cur.execute("UPDATE claims SET lost_item_id=%s WHERE id=%s", (item_id, claim_id))
        else:
            cur.execute("UPDATE claims SET found_item_id=%s WHERE id=%s", (item_id, claim_id))
        
        conn.commit()
        
        flash(f'Successfully linked {item_type} item "{item_name}" to claim #{claim_id}.', 'success')
        print(f"[LINK CLAIM] ✓ Claim {claim_id} linked to {item_type} item {item_id}")
    
    except Exception as e:
        conn.rollback()
        flash(f'Error linking item: {str(e)}', 'danger')
        print(f"[LINK CLAIM] ERROR: {str(e)}")
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('admin_claims.claims_page'))


