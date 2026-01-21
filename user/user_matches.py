# routes/user_matches.py
from flask import render_template, request, redirect, session, url_for, flash
from flask_login import login_required, current_user
from db import get_db
from user.routes import user_bp
from services.notifications import notify
import pymysql.cursors   # for DictCursor

@user_bp.route('/matches')
@login_required
def matches():
    conn = get_db()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cur.execute("""
            SELECT 
                m.id AS match_id, m.score, m.created_at AS match_created_at,
                li.id AS lost_id, li.name AS lost_name, li.description AS lost_desc, li.user_id AS lost_user_id,
                fi.id AS found_id, fi.name AS found_name, fi.description AS found_desc, fi.user_id AS found_user_id,
                c.id AS claim_id, c.status AS claim_status, c.created_at AS claim_created_at,
                c.user_id AS claimant_user_id
            FROM matches m
            JOIN lost_items li ON li.id = m.lost_item_id
            JOIN found_items fi ON fi.id = m.found_item_id
            LEFT JOIN (
                SELECT c1.*
                FROM claims c1
                JOIN (
                    SELECT match_id, MAX(created_at) AS latest
                    FROM claims
                    GROUP BY match_id
                ) cx ON cx.match_id = c1.match_id AND cx.latest = c1.created_at
            ) c ON c.match_id = m.id
            WHERE li.user_id = %s OR fi.user_id = %s
            ORDER BY m.score DESC, m.created_at DESC
        """, (current_user.id, current_user.id))
        raw_rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    lost_matches = []
    found_matches = []

    for row in raw_rows:
        match = {
            "match_id": row["match_id"],
            "score": row["score"],
            "lost_item": {
                "id": row["lost_id"],
                "name": row["lost_name"],
                "description": row["lost_desc"],
            },
            "found_item": {
                "id": row["found_id"],
                "name": row["found_name"],
                "description": row["found_desc"],
            },
            "claim": {
                "id": row.get("claim_id"),
                "status": row.get("claim_status"),
                "created_at": row.get("claim_created_at"),
                "claimant_user_id": row.get("claimant_user_id"),
            }
        }

        if row["lost_user_id"] == current_user.id:
            lost_matches.append(match)
        else:
            found_matches.append(match)

    # 🔴 Compute badge count: lost matches + found matches with pending claims
    pending_found = sum(1 for m in found_matches if m["claim"]["status"] == "Pending")
    matches_count = len(lost_matches) + pending_found

    session['matches_seen'] = True

    return render_template(
        'user/matches.html',
        lost_matches=lost_matches,
        found_matches=found_matches,
        matches_count=matches_count   # <-- pass to template
    )




@user_bp.route('/claim', methods=['POST'])
@login_required
def submit_claim():
    match_id      = request.form.get('match_id', type=int)
    lost_item_id  = request.form.get('lost_item_id', type=int)
    found_item_id = request.form.get('found_item_id', type=int)
    justification = request.form.get('justification', '').strip()

    print(f"\n[MATCH CLAIM] User {current_user.id} submitting claim for match {match_id}")
    print(f"[MATCH CLAIM] Lost item: {lost_item_id}, Found item: {found_item_id}")

    if not (match_id and lost_item_id and found_item_id and justification):
        print(f"[MATCH CLAIM] ERROR: Invalid claim request - missing required fields")
        flash("Invalid claim request.", "danger")
        return redirect(url_for('user.matches'))

    conn = get_db()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        # 🔒 DEDUPLICATION CHECK 1: Prevent duplicate pending claims on same match by this user
        print(f"[MATCH CLAIM] Checking for existing claims on match {match_id}...")
        cur.execute("""
            SELECT id, status FROM claims
            WHERE match_id=%s AND user_id=%s AND status IN ('Pending', 'Approved')
            LIMIT 1
        """, (match_id, current_user.id))
        
        existing_match_claim = cur.fetchone()
        if existing_match_claim:
            status = existing_match_claim.get('status')
            print(f"[MATCH CLAIM] ERROR: User already has {status} claim on match {match_id}")
            flash(f"You already have a {status.lower()} claim for this match.", "warning")
            return redirect(url_for('user.matches'))

        # 🔒 DEDUPLICATION CHECK 2: Prevent duplicate claims for same item pair
        print(f"[MATCH CLAIM] Checking for duplicate claims on items {lost_item_id}/{found_item_id}...")
        cur.execute("""
            SELECT id, status FROM claims
            WHERE user_id=%s 
              AND lost_item_id=%s 
              AND found_item_id=%s 
              AND status IN ('Pending', 'Approved')
            LIMIT 1
        """, (current_user.id, lost_item_id, found_item_id))
        
        existing_item_claim = cur.fetchone()
        if existing_item_claim:
            status = existing_item_claim.get('status')
            print(f"[MATCH CLAIM] ERROR: User already has {status} claim for these items")
            flash(f"You already have a {status.lower()} claim for these items.", "warning")
            return redirect(url_for('user.matches'))

        # 🔒 DEDUPLICATION CHECK 3: Verify user is not claiming their own items
        # User SHOULD be able to claim if they own ONE side (they reported either lost OR found)
        # User should NOT be able to claim if they own BOTH sides (they reported both items)
        cur.execute("SELECT user_id FROM lost_items WHERE id=%s", (lost_item_id,))
        lost_item = cur.fetchone()
        lost_owner = lost_item.get('user_id') if lost_item else None

        cur.execute("SELECT user_id FROM found_items WHERE id=%s", (found_item_id,))
        found_item = cur.fetchone()
        found_owner = found_item.get('user_id') if found_item else None

        # Only prevent claim if user owns BOTH items (not just one)
        if lost_owner == current_user.id and found_owner == current_user.id:
            print(f"[MATCH CLAIM] ERROR: User {current_user.id} tried to claim their own items (both)")
            flash("You cannot claim if you reported both items!", "warning")
            return redirect(url_for('user.matches'))

        # 🔒 DEDUPLICATION CHECK 4: Verify items haven't been already claimed/recovered
        cur.execute("""
            SELECT status FROM lost_items WHERE id=%s AND status NOT IN ('Recovered', 'Returned', 'Closed')
        """, (lost_item_id,))
        lost_available = cur.fetchone()

        cur.execute("""
            SELECT status FROM found_items WHERE id=%s AND status NOT IN ('Recovered', 'Returned', 'Closed')
        """, (found_item_id,))
        found_available = cur.fetchone()

        if not lost_available or not found_available:
            print(f"[MATCH CLAIM] ERROR: One or both items are no longer available")
            flash("One or both items are no longer available for claiming.", "warning")
            return redirect(url_for('user.matches'))

        # Get item names for notification
        lost_name = lost_item.get('name') if lost_item else 'Item'
        found_name = found_item.get('name') if found_item else 'Item'

        # All validations passed - Insert the claim
        print(f"[MATCH CLAIM] Inserting claim into database...")
        cur.execute("""
            INSERT INTO claims (match_id, lost_item_id, found_item_id, user_id, status, justification, created_at)
            VALUES (%s, %s, %s, %s, 'Pending', %s, NOW())
        """, (match_id, lost_item_id, found_item_id, current_user.id, justification))
        conn.commit()

        # Get the inserted claim ID
        cur.execute("SELECT LAST_INSERT_ID() as claim_id")
        result = cur.fetchone()
        claim_id = result.get('claim_id') if isinstance(result, dict) else result[0]

        print(f"[MATCH CLAIM] ✓ Claim {claim_id} inserted successfully")

        # Get admin users to notify
        cur.execute("SELECT id FROM users WHERE role='admin'")
        admins = cur.fetchall()

        # Send notification to all admins
        for admin in admins:
            admin_id = admin.get('id') if isinstance(admin, dict) else admin[0]
            notify(
                user_id=admin_id,
                notification_type='new_claim',
                title='New Claim Submitted 📝',
                message=f'User {current_user.name} submitted a claim for "{lost_name}" and "{found_name}".',
                related_id=claim_id
            )

        flash("Your claim has been submitted and is pending review.", "success")
        print(f"[MATCH CLAIM] ✓ Claim submission complete!")
        return redirect(url_for('user.matches'))
    except Exception as e:
        conn.rollback()
        print(f"[MATCH CLAIM] ERROR: {str(e)}")
        import traceback
        print(traceback.format_exc())
        flash(f"Error submitting claim: {str(e)}", "danger")
        return redirect(url_for('user.matches'))
    finally:
        cur.close()
        conn.close()
