#matching.py
import json
import threading
from db import get_db
from services.embeddings import deserialize_embedding
from sklearn.metrics.pairwise import cosine_similarity

# Lazy-load numpy to avoid import-time dependency and reduce boot memory pressure
_np = None
_np_lock = threading.Lock()

def _get_np():
    global _np
    if _np is not None:
        return _np
    with _np_lock:
        if _np is None:
            try:
                import numpy as np
            except Exception as e:
                raise ImportError("numpy is required for matching. Install it or disable matching features.") from e
            _np = np
    return _np

def _get(row, key, idx=None):
    if isinstance(row, dict):
        return row.get(key)
    if idx is None:
        return None
    return row[idx] if row and len(row) > idx else None

def get_lost_items_for_matching():
    """Get all APPROVED lost items with embeddings (case-insensitive status)."""
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, user_id, name, category, color, brand, description, last_seen, last_seen_at, embedding
            FROM lost_items
            WHERE LOWER(status)='approved'
              AND embedding IS NOT NULL
        """)
        items = cur.fetchall()
    finally:
        cur.close()
        conn.close()
    return items if items else []

def get_all_found_items():
    """Get all APPROVED found items with embeddings (case-insensitive status)."""
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, user_id, name, category, color, brand, description, where_found, found_at, embedding
            FROM found_items
            WHERE LOWER(status)='approved'
              AND embedding IS NOT NULL
        """)
        items = cur.fetchall()
    finally:
        cur.close()
        conn.close()
    return items if items else []

def get_match_count_for_lost_ids(lost_ids):
    """Return a dict {lost_item_id: count} for existing matches."""
    if not lost_ids:
        return {}

    conn = get_db()
    cur = conn.cursor()
    try:
        placeholders = ','.join(['%s'] * len(lost_ids))
        cur.execute(
            f"""SELECT lost_item_id, COUNT(*) AS c
                FROM matches
                WHERE lost_item_id IN ({placeholders})
                GROUP BY lost_item_id""",
            tuple(lost_ids),
        )
        rows = cur.fetchall() or []
        # rows may be tuples or dicts depending on cursor; normalize
        out = {}
        for r in rows:
            if isinstance(r, dict):
                out[int(r.get('lost_item_id'))] = int(r.get('c') or 0)
            else:
                out[int(r[0])] = int(r[1] or 0)
        return out
    finally:
        cur.close()
        conn.close()

def compute_cosine_similarity(emb1, emb2):
    """Compute cosine similarity between two embeddings"""
    if not emb1 or not emb2:
        return 0.0
    
    try:
        np = _get_np()
        emb1_array = np.array(emb1).reshape(1, -1)
        emb2_array = np.array(emb2).reshape(1, -1)
        similarity = cosine_similarity(emb1_array, emb2_array)[0][0]
        return float(similarity)
    except Exception:
        return 0.0

def _norm(s):
    return (s or '').strip().lower()

def _prefilter_found_items(lost_row, found_items):
    """Prefilter found candidates using structured attributes.

    - Always filter by category if present.
    - Optionally filter by color and brand if present.

    Comparisons are normalized (trim + lowercase) to avoid case/spacing mismatches.
    """
    lost_category = _norm(_get(lost_row, 'category', 3))
    lost_color = _norm(_get(lost_row, 'color', 4))
    lost_brand = _norm(_get(lost_row, 'brand', 5))

    candidates = found_items

    if lost_category:
        candidates = [f for f in candidates if _norm(_get(f, 'category', 3)) == lost_category]

    if lost_color:
        candidates = [f for f in candidates if _norm(_get(f, 'color', 4)) == lost_color]

    # brand can be sparse/typo-prone; only apply if it doesn't eliminate everything
    if lost_brand:
        brand_filtered = [f for f in candidates if _norm(_get(f, 'brand', 5)) == lost_brand]
        if brand_filtered:
            candidates = brand_filtered

    return candidates

def generate_matches(threshold=0.72, max_matches_per_lost=5):
    """Generate matches between lost and found items.

    Important: we allow *multiple* matches per lost item over time.
    To prevent unlimited growth, we cap stored matches per lost item.
    """
    lost_items = get_lost_items_for_matching()
    found_items = get_all_found_items()

    lost_ids = [(_get(li, 'id', 0)) for li in lost_items if _get(li, 'id', 0)]
    existing_counts = get_match_count_for_lost_ids(lost_ids)

    matches = []

    for lost in lost_items:
        lost_id = _get(lost, 'id', 0)
        if not lost_id:
            continue

        # Skip if this lost item already has enough matches stored
        if int(existing_counts.get(int(lost_id), 0)) >= int(max_matches_per_lost):
            continue

        lost_embedding = _get(lost, 'embedding', 9)
        if not lost_embedding:
            continue

        try:
            lost_emb = deserialize_embedding(lost_embedding)
        except (json.JSONDecodeError, TypeError):
            print(f"ERROR: Could not deserialize embedding for lost item {lost_id}")
            continue

        lost_user_id = _get(lost, 'user_id', 1)
        candidates = _prefilter_found_items(lost, found_items)

        for found in candidates:
            found_id = _get(found, 'id', 0)
            if not found_id:
                continue

            found_user_id = _get(found, 'user_id', 1)

            # Block self-matching (same reporter for lost and found)
            if lost_user_id is not None and found_user_id is not None and lost_user_id == found_user_id:
                continue

            found_embedding = _get(found, 'embedding', 9)
            if not found_embedding:
                continue

            try:
                found_emb = deserialize_embedding(found_embedding)
            except (json.JSONDecodeError, TypeError):
                print(f"ERROR: Could not deserialize embedding for found item {found_id}")
                continue

            similarity = compute_cosine_similarity(lost_emb, found_emb)

            if similarity >= threshold:
                matches.append({
                    'lost_item_id': lost_id,
                    'found_item_id': found_id,
                    'score': round(similarity * 100, 2)
                })

    return matches

def _row_first_value(row):
    """Return the first column value from either a dict row or tuple row."""
    if row is None:
        return None
    if isinstance(row, dict):
        # when selecting a single column without alias, key is the column name
        return next(iter(row.values()), None)
    if isinstance(row, (list, tuple)):
        return row[0] if row else None
    return None

def save_matches(matches):
    """Save matches to the database"""
    if not matches:
        print("No matches to save")
        return

    conn = get_db()
    cur = conn.cursor()
    try:
        saved = 0
        for match in matches:
            # Defense-in-depth: ensure this pair isn't a self-match
            cur.execute("SELECT user_id FROM lost_items WHERE id=%s", (match['lost_item_id'],))
            lost_owner = _row_first_value(cur.fetchone())

            cur.execute("SELECT user_id FROM found_items WHERE id=%s", (match['found_item_id'],))
            found_owner = _row_first_value(cur.fetchone())

            if lost_owner is not None and found_owner is not None and int(lost_owner) == int(found_owner):
                continue

            # Check if match already exists
            cur.execute(
                """SELECT id FROM matches 
                   WHERE lost_item_id = %s AND found_item_id = %s""",
                (match['lost_item_id'], match['found_item_id'])
            )

            if cur.fetchone():
                continue

            cur.execute(
                """INSERT INTO matches (lost_item_id, found_item_id, score, created_at)
                   VALUES (%s, %s, %s, NOW())""",
                (match['lost_item_id'], match['found_item_id'], float(match['score']))
            )
            saved += 1

        conn.commit()
        print(f"Successfully saved {saved} matches")

    except Exception as e:
        conn.rollback()
        # Print richer error details (MySQL errors sometimes stringify to just a code)
        err_code = getattr(e, 'args', [None])[0] if getattr(e, 'args', None) else None
        print(f"ERROR saving matches: {e} (code={err_code}, type={type(e).__name__})")

    finally:
        cur.close()
        conn.close()

def run_matching_pipeline(threshold=0.75, max_matches_per_lost=5):
    """Run the complete matching pipeline."""
    print("\n" + "="*60)
    print("STARTING MATCHING PIPELINE")
    print("="*60)

    matches = generate_matches(threshold=threshold, max_matches_per_lost=max_matches_per_lost)
    save_matches(matches)

    print("="*60)
    print(f"PIPELINE COMPLETE - Found {len(matches)} matches")
    print("="*60 + "\n")

    return matches

def get_matching_pipeline():
    """Return a callable that runs the matching pipeline.

    This lets callers import get_matching_pipeline at module import time and
    only execute the (potentially expensive) pipeline when the returned
    callable is invoked.
    """
    def _pipeline(threshold=0.75, max_matches_per_lost=5):
        return run_matching_pipeline(threshold=threshold, max_matches_per_lost=max_matches_per_lost)
    return _pipeline
