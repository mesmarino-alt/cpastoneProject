# app/commands/run_matching.py
from services.matching import generate_matches, save_matches

def run_matching_job():
    candidates = generate_matches(threshold=0.75)
    save_matches(candidates)
    return len(candidates)
