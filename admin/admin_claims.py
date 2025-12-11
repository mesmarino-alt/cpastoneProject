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
        # Fetch claims
        sql = """
            SELECT 
                c.id AS claim_id, c.status, c.justification, c.created_at,
                c.match_id, c.user_id AS claimant_user_id,
                c.lost_item_id, c.found_item_id,
                li.id AS lost_id, li.name AS lost_name, li.description AS lost_desc, li.photo AS lost_photo,
                fi.id AS found_id, fi.name AS found_name, fi.description AS found_desc, fi.photo AS found_photo,
                u.name AS claimant_name, u.email AS claimant_email
            FROM claims c
            JOIN lost_items li ON li.id = c.lost_item_id
            JOIN found_items fi ON fi.id = c.found_item_id
            JOIN users u ON u.id = c.user_id
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

    except Exception as e:
        print(f"[CLAIMS PAGE] ERROR: {str(e)}")
        import traceback; traceback.print_exc()
        claims = []
        pending_count = 0
    finally:
        cur.close()
        conn.close()

    # 🔴 Mark claims as seen when visiting this page
    session['claims_seen'] = True

    return render_template(
        'admin/claims.html',
        claims=claims,
        status_filter=status_filter,
        pending_count=pending_count
    )

@admin_claims_bp.route('/<int:claim_id>/approve', methods=['POST'])
@login_required
def claim_approve(claim_id):
    """Approve a claim and update item statuses"""
    print(f"\n[CLAIM APPROVE] Admin {current_user.id} approving claim {claim_id}")
    
    conn = get_db()
    cur = conn.cursor()
    try:
        # Get claim + related items + claimant info
        cur.execute("""
            SELECT c.id, c.match_id, c.lost_item_id, c.found_item_id, c.status, c.user_id,
                   li.name as lost_name, fi.name as found_name
            FROM claims c
            JOIN lost_items li ON li.id = c.lost_item_id
            JOIN found_items fi ON fi.id = c.found_item_id
            WHERE c.id=%s LIMIT 1
        """, (claim_id,))
        claim = cur.fetchone()
        
        if not claim:
            flash('Claim not found.', 'warning')
            return redirect(url_for('admin_claims.claims_page'))
        
        # Handle both dict and tuple returns
        status = claim.get('status') if isinstance(claim, dict) else claim[4]
        if status != 'Pending':
            flash('Invalid claim or already processed.', 'warning')
            return redirect(url_for('admin_claims.claims_page'))

        claimant_user_id = claim.get('user_id') if isinstance(claim, dict) else claim[5]
        lost_name = claim.get('lost_name') if isinstance(claim, dict) else None
        
        # Update claim status
        cur.execute("UPDATE claims SET status='Approved' WHERE id=%s", (claim_id,))

        # Update items status
        lost_id = claim.get('lost_item_id') if isinstance(claim, dict) else claim[2]
        found_id = claim.get('found_item_id') if isinstance(claim, dict) else claim[3]
        cur.execute("UPDATE lost_items SET status='Recovered' WHERE id=%s", (lost_id,))
        cur.execute("UPDATE found_items SET status='Returned' WHERE id=%s", (found_id,))

        # Reject other pending claims for this match
        match_id = claim.get('match_id') if isinstance(claim, dict) else claim[1]
        cur.execute("""
            UPDATE claims SET status='Rejected'
            WHERE match_id=%s AND id<>%s AND status='Pending'
        """, (match_id, claim_id))

        conn.commit()
        
        # Send notification to claimant
        notify(
            user_id=claimant_user_id,
            notification_type='claim_approved',
            title='Claim Approved! ✅',
            message=f'Your claim for "{lost_name}" has been approved. The item will be returned to you shortly.',
            related_id=claim_id
        )
        
        # Send notification to admin for other rejected claims
        cur.execute("""
            SELECT DISTINCT user_id FROM claims
            WHERE match_id=%s AND id<>%s AND status='Rejected'
        """, (match_id, claim_id))
        rejected_claimants = cur.fetchall()
        for claimant in rejected_claimants:
            rejected_user_id = claimant.get('user_id') if isinstance(claimant, dict) else claimant[0]
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
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT c.id, c.status, c.user_id, li.name as lost_name
            FROM claims c
            JOIN lost_items li ON li.id = c.lost_item_id
            WHERE c.id=%s LIMIT 1
        """, (claim_id,))
        claim = cur.fetchone()
        
        if not claim:
            flash('Claim not found.', 'warning')
            return redirect(url_for('admin_claims.claims_page'))
        
        # Handle both dict and tuple returns
        status = claim.get('status') if isinstance(claim, dict) else claim[1]
        if status != 'Pending':
            flash('Invalid claim or already processed.', 'warning')
            return redirect(url_for('admin_claims.claims_page'))

        claimant_user_id = claim.get('user_id') if isinstance(claim, dict) else claim[2]
        lost_name = claim.get('lost_name') if isinstance(claim, dict) else None

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


