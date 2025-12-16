#matching.py
import json
import numpy as np
from db import get_db
from services.embeddings import deserialize_embedding
from sklearn.metrics.pairwise import cosine_similarity

def get_unmatched_lost_items():
    """Get all lost items that haven't been matched yet"""
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, description, embedding
            FROM lost_items
            WHERE embedding IS NOT NULL
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
    """Get all found items with embeddings"""
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, description, embedding
            FROM found_items
            WHERE embedding IS NOT NULL
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

def generate_matches(threshold=0.75):
    """Generate matches between lost and found items"""
    lost_items = get_unmatched_lost_items()
    found_items = get_all_found_items()
    
    matches = []
    
    for lost in lost_items:
        # Handle both dict and tuple returns
        lost_embedding = lost.get('embedding') if isinstance(lost, dict) else (lost[2] if lost and len(lost) > 2 else None)
        if not lost_embedding:
            continue
        
        try:
            lost_emb = deserialize_embedding(lost_embedding)
        except (json.JSONDecodeError, TypeError):
            lost_id = lost.get('id') if isinstance(lost, dict) else (lost[0] if lost and len(lost) > 0 else '?')
            print(f"ERROR: Could not deserialize embedding for lost item {lost_id}")
            continue
        
        for found in found_items:
            found_embedding = found.get('embedding') if isinstance(found, dict) else (found[2] if found and len(found) > 2 else None)
            if not found_embedding:
                continue
            
            try:
                found_emb = deserialize_embedding(found_embedding)
            except (json.JSONDecodeError, TypeError):
                found_id = found.get('id') if isinstance(found, dict) else (found[0] if found and len(found) > 0 else '?')
                print(f"ERROR: Could not deserialize embedding for found item {found_id}")
                continue
            
            similarity = compute_cosine_similarity(lost_emb, found_emb)
            
            if similarity >= threshold:
                lost_id = lost.get('id') if isinstance(lost, dict) else (lost[0] if lost and len(lost) > 0 else None)
                found_id = found.get('id') if isinstance(found, dict) else (found[0] if found and len(found) > 0 else None)
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
