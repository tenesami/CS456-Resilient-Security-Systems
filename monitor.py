
import logging
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Heartbeat monitor configuration
HOST = "127.0.0.1"
PORT = 9999
TIMEOUT = 5

SERVICE_SCRIPT = Path(__file__).with_name("service.py")

# Log detected service failures
logging.basicConfig(
    filename="incidents.log",
    level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def start_service():
    """Launch a replacement using the shared service implementation."""

    try:
        process = subprocess.Popen(
            [sys.executable, str(SERVICE_SCRIPT)],
            cwd=str(SERVICE_SCRIPT.parent)
        )
    except OSError as error:
        print(
            f"[{timestamp()}] "
            f"Failed to launch replacement service: {error}"
        )
        logging.error(
            f"Replacement service launch failed: {error}"
        )
        return None

    print(
        f"[{timestamp()}] "
        f"Replacement service launched (PID {process.pid}); "
        "waiting for heartbeats."
    )
    logging.warning(
        "Replacement service launched (PID %s).", process.pid
    )
    return process


def run_monitor():
    sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM
    )

    sock.bind((HOST, PORT))
    sock.settimeout(1)

    print(f"[{timestamp()}] Monitor started on {HOST}:{PORT}")
    print(f"Heartbeat timeout: {TIMEOUT} seconds")
    print(f"Replacement service: {SERVICE_SCRIPT.name}")
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
                        print(
                            f"[{timestamp()}] "
                            "Service heartbeat restored."
                        )

                    alert_sent = False

                    print(
                        f"[{timestamp()}] "
                        f"Heartbeat received from {address}"
                    )

            except TimeoutError:

                if last_heartbeat is not None:
                    elapsed = (
                        time.monotonic() - last_heartbeat
                    )

                    if elapsed > TIMEOUT and not alert_sent:
                        alert = (
                            "Service failure detected! "
                            f"No heartbeat for {elapsed:.1f} seconds."
                        )

                        print(
                            f"[{timestamp()}] ALERT: {alert}"
                        )

                        logging.warning(alert)

                        alert_sent = True

                        start_service()

    except KeyboardInterrupt:
        print(
            f"\n[{timestamp()}] Monitor stopped."
        )

    finally:
        sock.close()


if __name__ == "__main__":
    run_monitor()
