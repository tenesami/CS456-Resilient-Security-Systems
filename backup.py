
import json
import socket
import time
from datetime import datetime

from checkpoint import load_checkpoint, save_checkpoint
from service import handle_request

# Recovery configuration
HOST = "127.0.0.1"
ACTIVATION_PORT = 10001
CLIENT_PORT = 10000
MONITOR_PORT = 9999
HEARTBEAT_INTERVAL = 2
CHECKPOINT_REFRESH_INTERVAL = 5


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def run_backup():
    control_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    service_sock = None
    heartbeat_sock = None

    try:
        control_sock.bind((HOST, ACTIVATION_PORT))
        control_sock.settimeout(0.2)

        # Load saved session state
        state = load_checkpoint()
        next_refresh = time.monotonic() + CHECKPOINT_REFRESH_INTERVAL

        print(
            f"[{timestamp()}] Backup ready on "
            f"{HOST}:{ACTIVATION_PORT} (STANDBY)"
        )

        # Remain on standby until activated
        while service_sock is None:
            try:
                signal, _ = control_sock.recvfrom(1024)
            except socket.timeout:
                signal = None

            if signal == b"ACTIVATE":
                print(f"[{timestamp()}] Activation signal received.")

                candidate = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

                try:
                    # Take over the original client port
                    candidate.bind((HOST, CLIENT_PORT))

                    # Restore the latest checkpoint
                    state = load_checkpoint()
                    candidate.settimeout(0.2)

                except (OSError, ValueError) as error:
                    candidate.close()
                    print(f"[{timestamp()}] Activation failed: {error}")
                    print("Standby will continue waiting for activation.")
                    continue

                service_sock = candidate

                print(
                    f"[{timestamp()}] Backup ACTIVE "
                    f"on {HOST}:{CLIENT_PORT}"
                )
                break

            # Periodically refresh standby state
            if time.monotonic() >= next_refresh:
                try:
                    state = load_checkpoint()
                except (OSError, ValueError) as error:
                    print(
                        f"[{timestamp()}] "
                        f"Checkpoint refresh failed: {error}"
                    )

                next_refresh = (
                    time.monotonic() + CHECKPOINT_REFRESH_INTERVAL
                )

        # Backup now operates as the active service
        heartbeat_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        next_heartbeat = time.monotonic()

        while True:
            # Continue heartbeats after recovery
            if time.monotonic() >= next_heartbeat:
                heartbeat_sock.sendto(
                    b"HEARTBEAT",
                    (HOST, MONITOR_PORT)
                )

                next_heartbeat = (
                    time.monotonic() + HEARTBEAT_INTERVAL
                )

            try:
                data, address = service_sock.recvfrom(4096)
            except socket.timeout:
                continue

            try:
                request = json.loads(data.decode("utf-8"))

                # Reuse the original service request handler
                response, changed = handle_request(request, state)

                if changed:
                    save_checkpoint(state)

            except (ValueError, UnicodeDecodeError):
                response = {
                    "ok": False,
                    "error": "Invalid request"
                }

            except OSError as error:
                print(f"[{timestamp()}] State save failed: {error}")
                break

            try:
                service_sock.sendto(
                    json.dumps(response).encode("utf-8"),
                    address
                )

            except OSError as error:
                print(f"[{timestamp()}] Client response failed: {error}")
                break

    except KeyboardInterrupt:
        print(f"\n[{timestamp()}] Backup stopped by user.")

    finally:
        control_sock.close()

        if service_sock is not None:
            service_sock.close()

        if heartbeat_sock is not None:
            heartbeat_sock.close()


if __name__ == "__main__":
    run_backup()

