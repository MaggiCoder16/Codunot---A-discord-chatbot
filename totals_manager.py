# totals_manager.py
import os
import json

TOTAL_COUNTS_FILE = "total_counts.json"

# globals will hold the counts
total_image_count = {}
total_file_count = {}

def save_totals():
    """Save totals to JSON."""
    data = {
        "images": total_image_count,
        "files": total_file_count
    }
    try:
        with open(TOTAL_COUNTS_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"[SAVE TOTALS ERROR] {e}")

def load_totals():
    """Load totals from JSON."""
    global total_image_count, total_file_count
    if os.path.exists(TOTAL_COUNTS_FILE):
        try:
            with open(TOTAL_COUNTS_FILE) as f:
                data = json.load(f)
                total_image_count = {k:int(v) for k,v in data.get("images", {}).items()}
                total_file_count = {k:int(v) for k,v in data.get("files", {}).items()}
        except Exception as e:
            print(f"[LOAD TOTALS ERROR] {e}")
            total_image_count = {}
            total_file_count = {}
    else:
        total_image_count = {}
        total_file_count = {}

def consume_total(chan_id: str, kind: str):
    """Increment total counter and save to disk."""
    global total_image_count, total_file_count
    store = total_image_count if kind == "images" else total_file_count
    store[chan_id] = store.get(chan_id, 0) + 1
    save_totals()

def check_total_limit(chan_id: str, kind: str, limit: float) -> bool:
    """Return True if under limit, False if reached."""
    if limit == float("inf"):
        return True
    store = total_image_count if kind == "images" else total_file_count
    used = store.get(chan_id, 0)
    return used < limit
