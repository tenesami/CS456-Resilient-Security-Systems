import json
import os
import random
import socket
import time
import uuid
from datetime import datetime
from pathlib import Path

from checkpoint import load_checkpoint, save_checkpoint
from heartbeat import SECRET_ENV, create_heartbeat

# Heartbeat configuration from Part 1
HOST = "127.0.0.1"
PORT = 9999
HEARTBEAT_INTERVAL = 2
FAILURE_PROBABILITY = 0.10

# Client communication
SERVICE_PORT = 10000
PID_FILE = Path(__file__).with_name("service.pid")


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def authenticate(username, password):
    """Validate dummy credentials for demonstration."""
    return username == "demo" and password == "test123"


def handle_request(request, state):
    """Process a client request and update dynamic state."""

    if not isinstance(request, dict):
        return {"ok": False, "error": "Invalid request"}, False

    action = request.get("action")

    if action == "login":
        username = request.get("username")
        password = request.get("password")

        if not authenticate(username, password):
            return {"ok": False, "error": "Invalid credentials"}, False

        session_id = uuid.uuid4().hex

        state["sessions"][session_id] = {
            "username": username,
            "status": "active"
        }

        state["request_count"] += 1

        return {
            "ok": True,
            "session_id": session_id,
            "message": "Authentication successful"
        }, True

    elif action == "get_session":
        session_id = request.get("session_id")
        session = state["sessions"].get(session_id)

        if session is None:
            return {"ok": False, "error": "Session not found"}, False

        state["request_count"] += 1

        return {
            "ok": True,
            "session": session
        }, True

    elif action == "status":
        state["request_count"] += 1

        return {
            "ok": True,
            "sessions": len(state["sessions"]),
            "request_count": state["request_count"]
        }, True

    return {"ok": False, "error": "Unknown action"}, False


def run_service():
    heartbeat_secret = os.environ.pop(SECRET_ENV, None)
    if (
        heartbeat_secret is None
        or len(heartbeat_secret) != 64
        or any(character not in "0123456789abcdef" for character in heartbeat_secret)
    ):
        raise RuntimeError("Missing or invalid heartbeat secret; start monitor.py instead.")

    # Restore state from a previous checkpoint
    state = load_checkpoint()

    heartbeat_sock = socket.socket(
        socket.AF_INET, socket.SOCK_DGRAM
    )

    client_sock = socket.socket(
        socket.AF_INET, socket.SOCK_DGRAM
    )

    try:
        client_sock.bind((HOST, SERVICE_PORT))
        client_sock.settimeout(0.2)

        pid = os.getpid()
        temp_pid_file = PID_FILE.with_suffix(".pid.tmp")
        temp_pid_file.write_text(f"{pid}\n", encoding="utf-8")
        os.replace(temp_pid_file, PID_FILE)

        print(f"[{timestamp()}] Security service started (PID {pid}).")
        print(f"PID recorded in {PID_FILE}")
        print(f"Client service listening on {HOST}:{SERVICE_PORT}")
        print(f"Sending heartbeats every {HEARTBEAT_INTERVAL} seconds.")
        print(f"Restored sessions: {len(state['sessions'])}")
        print("Press Ctrl+C to stop.")

        next_heartbeat = time.monotonic()
        heartbeat_sequence = 0

        while True:

            # Preserve random crash behavior from Part 1
            if time.monotonic() >= next_heartbeat:

                if random.random() < FAILURE_PROBABILITY:
                    print(f"[{timestamp()}] Simulated service failure!")
                    break

                heartbeat_sequence += 1
                heartbeat_sock.sendto(
                    create_heartbeat(heartbeat_secret, heartbeat_sequence),
                    (HOST, PORT)
                )

                print(f"[{timestamp()}] Heartbeat sent to monitor.")

                next_heartbeat = (
                    time.monotonic() + HEARTBEAT_INTERVAL
                )

            # Handle incoming client requests
            try:
                data, address = client_sock.recvfrom(4096)

            except TimeoutError:
                continue

            try:
                request = json.loads(data.decode("utf-8"))
                response, changed = handle_request(request, state)

                # Save state BEFORE confirming a successful request
                if changed:
                    save_checkpoint(state)

                client_sock.sendto(
                    json.dumps(response).encode("utf-8"),
                    address
                )

                print(f"[{timestamp()}] Client request processed.")

            except (ValueError, UnicodeDecodeError) as error:
                client_sock.sendto(
                    json.dumps({
                        "ok": False,
                        "error": "Invalid request"
                    }).encode("utf-8"),
                    address
                )
                print(f"[{timestamp()}] Invalid request: {error}")

            except OSError as error:
                print(f"[{timestamp()}] Service error: {error}")
                break

    except KeyboardInterrupt:
        print(f"\n[{timestamp()}] Service stopped by user.")

    finally:
        heartbeat_sock.close()
        client_sock.close()


if __name__ == "__main__":
    run_service()
