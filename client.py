import json
import socket
import time
from datetime import datetime

HOST = "127.0.0.1"
SERVICE_PORT = 10000
INTERVAL = 2
TIMEOUT = 1
USERNAME = "demo"
PASSWORD = "test123"


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def send_request(request, host=HOST, port=SERVICE_PORT, timeout=TIMEOUT):
    # Separate sockets prevent delayed replies from satisfying a later request.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.send(json.dumps(request).encode("utf-8"))
        data = sock.recv(4096)

    response = json.loads(data.decode("utf-8"))
    if not isinstance(response, dict) or type(response.get("ok")) is not bool:
        raise ValueError("Invalid service response: expected an object with ok")

    action = request["action"]
    if not response["ok"]:
        error = response.get("error")
        if not isinstance(error, str) or not error:
            raise ValueError("Invalid service response: missing error message")
        raise ValueError(f"Service rejected {action}: {error}")

    if action == "login":
        session_id = response.get("session_id")
        if not isinstance(session_id, str) or not session_id:
            raise ValueError("Invalid login response: missing session ID")
    elif action == "get_session":
        session = response.get("session")
        if (
            not isinstance(session, dict)
            or session.get("username") != USERNAME
            or session.get("status") != "active"
        ):
            raise ValueError("Invalid session response: expected active demo session")
    elif action == "status":
        for field in ("sessions", "request_count"):
            value = response.get(field)
            if type(value) is not int or value < 0:
                raise ValueError(f"Invalid status response: invalid {field}")

    return response


def run_client(host=HOST, port=SERVICE_PORT, interval=INTERVAL, timeout=TIMEOUT):
    session_id = None
    unavailable = False
    print(f"[{timestamp()}] Simulated client targeting {host}:{port}")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            try:
                if session_id is None:
                    response = send_request(
                        {
                            "action": "login",
                            "username": USERNAME,
                            "password": PASSWORD
                        },
                        host, port, timeout
                    )
                    session_id = response["session_id"]
                    print(f"[{timestamp()}] Created session: {session_id}")

                send_request(
                    {"action": "get_session", "session_id": session_id},
                    host, port, timeout
                )
                status = send_request({"action": "status"}, host, port, timeout)

                if unavailable:
                    print(
                        f"[{timestamp()}] Service reachable again; "
                        f"original session {session_id} is still active."
                    )
                    unavailable = False

                print(
                    f"[{timestamp()}] Session {session_id} active; "
                    f"sessions={status['sessions']}, "
                    f"request_count={status['request_count']}"
                )

            except (TimeoutError, ConnectionRefusedError, ConnectionResetError) as error:
                unavailable = True
                print(
                    f"[{timestamp()}] Service temporarily unavailable: {error}. "
                    f"Retrying in {interval} seconds without replacing the session."
                )

            except (OSError, ValueError) as error:
                print(f"[{timestamp()}] Client stopped: {error}")
                return 1

            time.sleep(interval)

    except KeyboardInterrupt:
        print(f"\n[{timestamp()}] Client stopped by user.")
        return 0


if __name__ == "__main__":
    raise SystemExit(run_client())
