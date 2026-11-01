
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
INITIAL_RETRY_DELAY = 1
MAX_RETRY_DELAY = 30
SHUTDOWN_TIMEOUT = 2

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


def stop_service(process):
    """Stop and reap the monitor's current child during shutdown."""
    if process.poll() is not None:
        return

    try:
        process.terminate()
        try:
            process.wait(timeout=SHUTDOWN_TIMEOUT)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=SHUTDOWN_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as error:
        logging.error("Failed to stop service PID %s: %s", process.pid, error)
        print(f"[{timestamp()}] Failed to stop service PID {process.pid}: {error}")
        raise

    print(f"[{timestamp()}] Service child PID {process.pid} stopped.")


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
    replacement_process = None
    replacement_started = None
    startup_timeout_reported = False
    next_restart = None
    retry_delay = INITIAL_RETRY_DELAY

    try:
        while True:
            # Received heartbeats clear the outage and reset retry backoff.
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
                    next_restart = None
                    retry_delay = INITIAL_RETRY_DELAY

                    print(
                        f"[{timestamp()}] "
                        f"Heartbeat received from {address}"
                    )

            except TimeoutError:
                pass

            now = time.monotonic()

            # Confirm child exit before releasing its handle and scheduling a retry.
            if replacement_process is not None:
                returncode = replacement_process.poll()
                if returncode is not None:
                    alert = (
                        f"Service child PID {replacement_process.pid} "
                        f"exited with code {returncode}. "
                        f"Retrying in {retry_delay} seconds."
                    )
                    print(f"[{timestamp()}] ALERT: {alert}")
                    logging.warning(alert)
                    replacement_process = None
                    alert_sent = True
                    next_restart = now + retry_delay
                    retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)

            # Report a new heartbeat outage once and schedule immediate recovery.
            if last_heartbeat is not None and not alert_sent:
                elapsed = now - last_heartbeat
                if elapsed > TIMEOUT:
                    alert = (
                        "Service failure detected! "
                        f"No heartbeat for {elapsed:.1f} seconds."
                    )

                    print(f"[{timestamp()}] ALERT: {alert}")
                    logging.warning(alert)
                    alert_sent = True
                    next_restart = now

            # Launch when the retry is due, but only if no retained child is alive.
            if (
                alert_sent
                and replacement_process is None
                and next_restart is not None
                and now >= next_restart
            ):
                replacement_process = start_service()
                if replacement_process is None:
                    next_restart = now + retry_delay
                    print(
                        f"[{timestamp()}] Retrying service launch "
                        f"in {retry_delay} seconds."
                    )
                    retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)
                else:
                    next_restart = None
                    replacement_started = now
                    startup_timeout_reported = False

            # Report a live-but-silent child once; do not replace it until it exits.
            if (
                alert_sent
                and replacement_process is not None
                and replacement_started is not None
                and now - replacement_started > TIMEOUT
                and not startup_timeout_reported
            ):
                alert = (
                    f"Service child PID {replacement_process.pid} is still "
                    "running without a recovery heartbeat. Waiting for "
                    "confirmed exit before launching another replacement."
                )
                print(f"[{timestamp()}] ALERT: {alert}")
                logging.warning(alert)
                startup_timeout_reported = True

    except KeyboardInterrupt:
        print(
            f"\n[{timestamp()}] Monitor stopped."
        )

    # Stop and wait for the retained child; always close the monitor socket.
    finally:
        try:
            if replacement_process is not None:
                stop_service(replacement_process)
        finally:
            sock.close()


if __name__ == "__main__":
    run_monitor()
