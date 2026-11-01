import os
import shutil
import sys

from checkpoint import CHECKPOINT_FILE

STATE_FILE = CHECKPOINT_FILE
BACKUP_FILE = CHECKPOINT_FILE.with_name(
    CHECKPOINT_FILE.name + ".audit_backup"
)

def corrupt_state():
    if not os.path.isfile(STATE_FILE):
        print("Checkpoint file not found.")
        return

    if os.path.exists(BACKUP_FILE):
        print("Backup already exists. Restore it first.")
        return

    shutil.copyfile(STATE_FILE, BACKUP_FILE)

    with open(STATE_FILE, "w", encoding="utf-8") as file:
        file.write("{ invalid checkpoint data")

    print("Checkpoint corrupted.")
    print("Original checkpoint saved as backup.")


def restore_state():
    if not os.path.isfile(BACKUP_FILE):
        print("No backup found.")
        return

    shutil.copyfile(BACKUP_FILE, STATE_FILE)
    os.remove(BACKUP_FILE)

    print("Original checkpoint restored.")


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 audit_checkpoint.py corrupt")
        print("       python3 audit_checkpoint.py restore")
        return

    if sys.argv[1] == "corrupt":
        corrupt_state()
    elif sys.argv[1] == "restore":
        restore_state()
    else:
        print("Invalid option.")


if __name__ == "__main__":
    main()
