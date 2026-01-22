#embeddings.py
from sentence_transformers import SentenceTransformer
import json

# Load model once at import
model = SentenceTransformer('all-MiniLM-L6-v2')

def compute_embedding(text: str):
    """Return embedding as a Python list for DB storage (JSON)."""
    if not text:
        return None
    return model.encode(text).tolist()

def embed_tensor(text: str):
    """Return embedding as a tensor for similarity calculations."""
    if not text:
        return None
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

def _clean(v):
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None

def build_item_text_structured(*,
    name=None,
    category=None,
    color=None,
    brand=None,
    shape=None,
    material=None,
    features=None,
    location=None,
    date=None,
):
    """Build canonical text representation for embeddings using structured inputs.

    This keeps wording consistent across users by emitting stable key/value fields.
    Only non-empty fields are included.
    """
    parts = []

    name = _clean(name)
    category = _clean(category)
    color = _clean(color)
    brand = _clean(brand)
    shape = _clean(shape)
    material = _clean(material)
    features = _clean(features)
    location = _clean(location)

    if name:
        parts.append(f"Name: {name}")
    if category:
        parts.append(f"Category: {category}")
    if brand:
        parts.append(f"Brand: {brand}")
    if color:
        parts.append(f"Color: {color}")
    if shape:
        parts.append(f"Shape: {shape}")
    if material:
        parts.append(f"Material: {material}")
    if features:
        parts.append(f"Features: {features}")

    if location:
        parts.append(f"Location: {location}")

    if date:
        try:
            if hasattr(date, 'strftime'):
                date_str = date.strftime('%Y-%m-%d')
            else:
                date_str = str(date)
        except Exception:
            date_str = str(date)
        date_str = _clean(date_str)
        if date_str:
            parts.append(f"Date: {date_str}")

    return "; ".join(parts)

def compute_item_embedding_structured(**kwargs):
    """Compute embedding from build_item_text_structured output."""
    text = build_item_text_structured(**kwargs)
    if not text:
        return None
    return compute_embedding(text)
