

import socket
import time
import logging
from datetime import datetime

HOST = "127.0.0.1"
PORT = 9999
TIMEOUT = 5

logging.basicConfig(
    filename="incidents.log",
    level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def run_monitor():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    sock.settimeout(1)

    print(f"[{timestamp()}] Monitor started on {HOST}:{PORT}")
    print("Waiting for heartbeats. Press Ctrl+C to stop.")

    last_heartbeat = None
    alert_sent = False

    try:
        while True:
            try:
                data, address = sock.recvfrom(1024)
                message = data.decode("utf-8")

                if message == "HEARTBEAT":
                    last_heartbeat = time.monotonic()

                    if alert_sent:
                        print(f"[{timestamp()}] Service heartbeat restored.")

                    alert_sent = False

                    print(
                        f"[{timestamp()}] Heartbeat received from {address}"
                    )

            except socket.timeout:
                if last_heartbeat is not None:
                    elapsed = time.monotonic() - last_heartbeat

                    if elapsed > TIMEOUT and not alert_sent:
                        alert = (
                            f"Service failure detected! "
                            f"No heartbeat for {elapsed:.1f} seconds."
                        )

                        print(f"[{timestamp()}] ALERT: {alert}")
                        logging.warning(alert)
                        alert_sent = True

    except KeyboardInterrupt:
        print(f"\n[{timestamp()}] Monitor stopped.")

    finally:
        sock.close()


if __name__ == "__main__":
    run_monitor()

