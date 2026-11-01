
import logging
import socket
import time
from datetime import datetime

# Heartbeat monitor configuration
HOST = "127.0.0.1"
PORT = 9999
TIMEOUT = 5

# Mini Project 2: Standby activation configuration
BACKUP_PORT = 10001

# Log detected service failures
logging.basicConfig(
    filename="incidents.log",
    level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def activate_backup(sock):
    """Notify the standby service to take over."""

    try:
        sock.sendto(
            b"ACTIVATE",
            (HOST, BACKUP_PORT)
        )

        print(
            f"[{timestamp()}] "
            "Activation signal sent to standby service."
        )

        logging.warning(
            "Standby activation signal sent."
        )

    except OSError as error:
        print(
            f"[{timestamp()}] "
            f"Failed to notify standby: {error}"
        )

        logging.error(
            f"Standby activation notification failed: {error}"
        )


def run_monitor():
    sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM
    )

    sock.bind((HOST, PORT))
    sock.settimeout(1)

    print(f"[{timestamp()}] Monitor started on {HOST}:{PORT}")
    print(f"Heartbeat timeout: {TIMEOUT} seconds")
    print(f"Standby activation port: {BACKUP_PORT}")
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

                        # Mini Project 2:
                        # Notify standby to begin recovery
                        activate_backup(sock)

    except KeyboardInterrupt:
        print(
            f"\n[{timestamp()}] Monitor stopped."
        )

    finally:
        sock.close()


if __name__ == "__main__":
    run_monitor()

