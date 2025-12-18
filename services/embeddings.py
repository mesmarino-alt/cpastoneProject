#embeddings.py
from sentence_transformers import SentenceTransformer
import json

# Global model variable - lazy loaded
_model = None

def get_model():
    """Lazy load the model only when first needed."""
    global _model
    if _model is None:
        print("Loading sentence transformer model...")
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def compute_embedding(text: str):
    """Return embedding as a Python list for DB storage (JSON)."""
    if not text:
        return None
    model = get_model()
    return model.encode(text).tolist()

def embed_tensor(text: str):
    """Return embedding as a tensor for similarity calculations."""
    if not text:
        return None
    model = get_model()
    return model.encode(text, convert_to_tensor=True)

def serialize_embedding(embedding_list):
    """Convert list to JSON string for DB storage."""
    return json.dumps(embedding_list)

def deserialize_embedding(embedding_json):
    """Convert JSON string back to Python list."""
    return json.loads(embedding_json)

def build_item_text(name, description, location, date=None):
    """
    Build unified text representation for an item.
    Combines all fields into one string for embedding.
    
    Args:
        name (str): Item name
        description (str): Item description
        location (str): Location (last_seen/where_found)
        date (datetime or str, optional): Date (last_seen_at/found_at)
    
    Returns:
        str: Formatted text combining all fields
    """
    parts = []
    
    if name:
        parts.append(f"Name: {name}")
    
    if description:
        parts.append(f"Description: {description}")
    
    if location:
        parts.append(f"Location: {location}")
    
    if date:
        try:
            # Handle datetime objects
            if hasattr(date, 'strftime'):
                date_str = date.strftime('%Y-%m-%d')
            else:
                date_str = str(date)
        except Exception:
            date_str = str(date)
        parts.append(f"Date: {date_str}")
    
    return ". ".join(parts)

def compute_item_embedding(name, description, location, date=None):
    """
    Compute unified embedding for an item.
    Encodes all fields (name, description, location, date) together.
    
    Args:
        name (str): Item name
        description (str): Item description
        location (str): Location (last_seen/where_found)
        date (datetime or str, optional): Date (last_seen_at/found_at)
    
    Returns:
        list: Embedding vector as list (or None if text is empty)
    """
    text = build_item_text(name, description, location, date)
    if not text:
        return None
    return compute_embedding(text)
