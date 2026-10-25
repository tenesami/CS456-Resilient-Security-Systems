
import random
import socket
import time
from datetime import datetime

HOST = "127.0.0.1"
PORT = 9999
HEARTBEAT_INTERVAL = 2
FAILURE_PROBABILITY = 0.10


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def authenticate(username, password):
    """Demonstration authentication using dummy credentials."""
    return username == "demo" and password == "test123"


def run_service():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print(f"[{timestamp()}] Security service started.")
    print("Sending heartbeats every 2 seconds.")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            if random.random() < FAILURE_PROBABILITY:
                print(f"[{timestamp()}] Simulated service failure!")
                break

            sock.sendto(b"HEARTBEAT", (HOST, PORT))

            print(f"[{timestamp()}] Heartbeat sent to monitor.")

            time.sleep(HEARTBEAT_INTERVAL)

    except KeyboardInterrupt:
        print(f"\n[{timestamp()}] Service stopped by user.")

    finally:
        sock.close()


if __name__ == "__main__":
    run_service()

