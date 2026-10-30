import json
import os
from pathlib import Path

CHECKPOINT_FILE = Path(__file__).with_name("checkpoint.json")


def save_checkpoint(state):
    """Atomically save the current service state."""
    temp_file = CHECKPOINT_FILE.with_suffix(".json.tmp")

    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(state, file, indent=4)
        file.flush()
        os.fsync(file.fileno())

    os.replace(temp_file, CHECKPOINT_FILE)
    print("[CHECKPOINT] Service state saved.")


def load_checkpoint():
    """Load previously saved service state."""
    if not CHECKPOINT_FILE.exists():
        print("[CHECKPOINT] No checkpoint exists.")
        return {"sessions": {}, "request_count": 0}

    try:
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as file:
            state = json.load(file)

        if not isinstance(state, dict):
            raise ValueError("Checkpoint must contain an object")

        if not isinstance(state.get("sessions"), dict):
            raise ValueError("Invalid session state")

        count = state.get("request_count")
        if type(count) is not int or count < 0:
            raise ValueError("Invalid request count")

        print("[CHECKPOINT] Previous state restored.")
        return state

    except (json.JSONDecodeError, ValueError, OSError) as error:
        print(f"[CHECKPOINT] Recovery failed: {error}")
        raise
