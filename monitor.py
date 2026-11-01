
import logging
import os
import secrets
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from heartbeat import SECRET_ENV, verify_heartbeat

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


def start_service(heartbeat_secret):
    """Launch a monitor-owned service with its private heartbeat key."""

    environment = os.environ.copy()
    environment[SECRET_ENV] = heartbeat_secret
    try:
        process = subprocess.Popen(
            [sys.executable, str(SERVICE_SCRIPT)],
            cwd=str(SERVICE_SCRIPT.parent),
            env=environment,
            stdin=subprocess.DEVNULL
        )
    except OSError as error:
        print(
            f"[{timestamp()}] "
            f"Failed to launch service: {error}"
        )
        logging.error(
            f"Service launch failed: {error}"
        )
        return None

    print(
        f"[{timestamp()}] "
        f"Service launched (PID {process.pid}); "
        "waiting for heartbeats."
    )
    logging.warning(
        "Service launched (PID %s).", process.pid
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

    last_heartbeat = None
    last_sequence = 0
    heartbeat_secret = None
    alert_sent = True
    replacement_process = None
    replacement_started = None
    startup_timeout_reported = False
    next_restart = time.monotonic()
    retry_delay = INITIAL_RETRY_DELAY

    try:
        sock.bind((HOST, PORT))
        sock.settimeout(1)

        print(f"[{timestamp()}] Monitor started on {HOST}:{PORT}")
        print(f"Heartbeat timeout: {TIMEOUT} seconds")
        print(f"Managed service: {SERVICE_SCRIPT.name}")
        print("Starting service. Press Ctrl+C to stop.")

        while True:
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
                heartbeat_secret = secrets.token_hex(32)
                replacement_process = start_service(heartbeat_secret)
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
                    last_heartbeat = None
                    last_sequence = 0

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

            # Only the current child's authenticated heartbeats can clear an outage.
            try:
                data, address = sock.recvfrom(1024)
                sequence = None
                if replacement_process is not None and heartbeat_secret is not None:
                    sequence = verify_heartbeat(
                        data, heartbeat_secret, last_sequence, TIMEOUT
                    )
                if sequence is None:
                    logging.warning("Rejected invalid heartbeat from %s.", address)
                else:
                    last_sequence = sequence
                    last_heartbeat = time.monotonic()
                    if alert_sent:
                        print(f"[{timestamp()}] Service heartbeat restored.")
                    alert_sent = False
                    next_restart = None
                    retry_delay = INITIAL_RETRY_DELAY
                    print(f"[{timestamp()}] Heartbeat received from {address}")
            except TimeoutError:
                pass

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
