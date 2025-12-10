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
