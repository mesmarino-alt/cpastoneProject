#matching.py
import json
import numpy as np
from db import get_db
from services.embeddings import deserialize_embedding
from sklearn.metrics.pairwise import cosine_similarity

def _get(row, key, idx=None):
    if isinstance(row, dict):
        return row.get(key)
    if idx is None:
        return None
    return row[idx] if row and len(row) > idx else None

def get_unmatched_lost_items():
    """Get all APPROVED lost items that haven't been matched yet"""
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, user_id, name, category, color, brand, description, last_seen, last_seen_at, embedding
            FROM lost_items
            WHERE status='approved'
            AND embedding IS NOT NULL
            AND id NOT IN (
                SELECT DISTINCT lost_item_id FROM matches
            )
        """)
        items = cur.fetchall()
    finally:
        cur.close()
        conn.close()
    return items if items else []

def get_all_found_items():
    """Get all APPROVED found items with embeddings"""
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, user_id, name, category, color, brand, description, where_found, found_at, embedding
            FROM found_items
            WHERE status='approved'
            AND embedding IS NOT NULL
        """)
        items = cur.fetchall()
    finally:
        cur.close()
        conn.close()
    return items if items else []

def compute_cosine_similarity(emb1, emb2):
    """Compute cosine similarity between two embeddings"""
    if not emb1 or not emb2:
        return 0.0
    
    try:
        emb1_array = np.array(emb1).reshape(1, -1)
        emb2_array = np.array(emb2).reshape(1, -1)
        similarity = cosine_similarity(emb1_array, emb2_array)[0][0]
        return float(similarity)
    except Exception:
        return 0.0

def _prefilter_found_items(lost_row, found_items):
    """Prefilter found candidates using structured attributes.

    - Always filter by category if present.
    - Optionally filter by color and brand if present.
    """
    lost_category = (_get(lost_row, 'category', 3) or '').strip()
    lost_color = (_get(lost_row, 'color', 4) or '').strip()
    lost_brand = (_get(lost_row, 'brand', 5) or '').strip()

    candidates = found_items

    if lost_category:
        candidates = [f for f in candidates if (_get(f, 'category', 3) or '').strip() == lost_category]

    if lost_color:
        candidates = [f for f in candidates if (_get(f, 'color', 4) or '').strip() == lost_color]

    # brand can be sparse/typo-prone; only apply if it doesn't eliminate everything
    if lost_brand:
        brand_filtered = [f for f in candidates if (_get(f, 'brand', 5) or '').strip().lower() == lost_brand.lower()]
        if brand_filtered:
            candidates = brand_filtered

    return candidates

def generate_matches(threshold=0.72):
    """Generate matches between lost and found items using unified embeddings + structured prefilter."""
    lost_items = get_unmatched_lost_items()
    found_items = get_all_found_items()

    matches = []

    for lost in lost_items:
        lost_embedding = _get(lost, 'embedding', 9)
        if not lost_embedding:
            continue

        try:
            lost_emb = deserialize_embedding(lost_embedding)
        except (json.JSONDecodeError, TypeError):
            lost_id = _get(lost, 'id', 0) or '?'
            print(f"ERROR: Could not deserialize embedding for lost item {lost_id}")
            continue

        lost_user_id = _get(lost, 'user_id', 1)

        candidates = _prefilter_found_items(lost, found_items)

        for found in candidates:
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
                found_id = _get(found, 'id', 0) or '?'
                print(f"ERROR: Could not deserialize embedding for found item {found_id}")
                continue

            similarity = compute_cosine_similarity(lost_emb, found_emb)

            if similarity >= threshold:
                lost_id = _get(lost, 'id', 0)
                found_id = _get(found, 'id', 0)
                if lost_id and found_id:
                    matches.append({
                        'lost_item_id': lost_id,
                        'found_item_id': found_id,
                        'score': round(similarity * 100, 2)
                    })
                    print(f"MATCH FOUND: Lost {lost_id} ↔ Found {found_id} (Score: {similarity:.2%})")

    return matches

def save_matches(matches):
    """Save matches to the database"""
    if not matches:
        print("No matches to save")
        return
    
    conn = get_db()
    cur = conn.cursor()
    try:
        for match in matches:
            # Defense-in-depth: ensure this pair isn't a self-match
            cur.execute("SELECT user_id FROM lost_items WHERE id=%s", (match['lost_item_id'],))
            lost_owner = (cur.fetchone() or [None])[0]
            cur.execute("SELECT user_id FROM found_items WHERE id=%s", (match['found_item_id'],))
            found_owner = (cur.fetchone() or [None])[0]
            if lost_owner is not None and found_owner is not None and lost_owner == found_owner:
                continue

            # Check if match already exists
            cur.execute("""
                SELECT id FROM matches 
                WHERE lost_item_id = %s AND found_item_id = %s
            """, (match['lost_item_id'], match['found_item_id']))
            
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO matches (lost_item_id, found_item_id, score, created_at)
                    VALUES (%s, %s, %s, NOW())
                """, (match['lost_item_id'], match['found_item_id'], match['score']))
                print(f"Saved match: Lost {match['lost_item_id']} ↔ Found {match['found_item_id']}")
        
        conn.commit()
        print(f"Successfully saved {len(matches)} matches")
    except Exception as e:
        conn.rollback()
        print(f"ERROR saving matches: {str(e)}")
    finally:
        cur.close()
        conn.close()

def run_matching_pipeline(threshold=0.75):
    """Run the complete matching pipeline"""
    print("\n" + "="*60)
    print("STARTING MATCHING PIPELINE")
    print("="*60)
    
    matches = generate_matches(threshold=threshold)
    save_matches(matches)
    
    print("="*60)
    print(f"PIPELINE COMPLETE - Found {len(matches)} matches")
    print("="*60 + "\n")
    
    return matches
