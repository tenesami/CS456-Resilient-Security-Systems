import io
import json
import socket
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

import client


class ClientTests(unittest.TestCase):
    def test_sends_real_protocol_and_closes_request_socket(self):
        sock = Mock()
        sock.recv.return_value = json.dumps(
            {"ok": True, "session_id": "original-session"}
        ).encode("utf-8")
        request = {
            "action": "login", "username": "demo", "password": "test123"
        }
        with patch("client.socket.socket") as factory:
            factory.return_value.__enter__.return_value = sock
            response = client.send_request(request)

        self.assertEqual(response["session_id"], "original-session")
        sock.connect.assert_called_once_with((client.HOST, client.SERVICE_PORT))
        sock.settimeout.assert_called_once_with(client.TIMEOUT)
        self.assertEqual(json.loads(sock.send.call_args.args[0]), request)
        factory.return_value.__exit__.assert_called_once()

    def test_rejects_malformed_and_failed_responses(self):
        responses = [
            b"not json", b"\xff", b"[]", b'{"ok": 1}',
            b'{"ok": false}', b'{"ok": true}',
            b'{"ok": false, "error": "Invalid credentials"}'
        ]
        for data in responses:
            with self.subTest(data=data), patch("client.socket.socket") as factory:
                factory.return_value.__enter__.return_value.recv.return_value = data
                with self.assertRaises(ValueError):
                    client.send_request({"action": "login"})

    def test_retries_startup_timeout_then_creates_session(self):
        responses = [
            socket.timeout("no response"),
            {"ok": True, "session_id": "original-session"},
            {"ok": True, "session": {"username": "demo", "status": "active"}},
            {"ok": True, "sessions": 1, "request_count": 3}
        ]
        with patch("client.send_request", side_effect=responses) as send, patch(
            "client.time.sleep", side_effect=[None, KeyboardInterrupt()]
        ), redirect_stdout(io.StringIO()):
            self.assertEqual(client.run_client(), 0)

        actions = [call.args[0]["action"] for call in send.call_args_list]
        self.assertEqual(actions, ["login", "login", "get_session", "status"])

    def test_outage_reuses_original_session_without_login(self):
        responses = [
            {"ok": True, "session_id": "original-session"},
            {"ok": True, "session": {"username": "demo", "status": "active"}},
            {"ok": True, "sessions": 1, "request_count": 3},
            socket.timeout("primary unavailable"),
            {"ok": True, "session": {"username": "demo", "status": "active"}},
            {"ok": True, "sessions": 1, "request_count": 5}
        ]
        output = io.StringIO()
        with patch("client.send_request", side_effect=responses) as send, patch(
            "client.time.sleep", side_effect=[None, None, KeyboardInterrupt()]
        ), redirect_stdout(output):
            self.assertEqual(client.run_client(), 0)

        requests = [call.args[0] for call in send.call_args_list]
        self.assertEqual(sum(r["action"] == "login" for r in requests), 1)
        session_requests = [r for r in requests if r["action"] == "get_session"]
        self.assertEqual(len(session_requests), 3)
        self.assertTrue(
            all(r["session_id"] == "original-session" for r in session_requests)
        )
        self.assertIn(
            "original session original-session is still active", output.getvalue()
        )
        self.assertIn("request_count=5", output.getvalue())

    def test_missing_restored_session_stops_instead_of_logging_in_again(self):
        output = io.StringIO()
        with patch(
            "client.send_request",
            side_effect=[
                {"ok": True, "session_id": "original-session"},
                ValueError("Service rejected get_session: Session not found")
            ]
        ) as send, redirect_stdout(output):
            self.assertEqual(client.run_client(), 1)

        self.assertEqual(send.call_count, 2)
        self.assertIn("Session not found", output.getvalue())

    def test_rejects_invalid_session_and_status_shapes(self):
        cases = [
            ("get_session", {"ok": True, "session": {}}),
            ("status", {"ok": True, "sessions": True, "request_count": 1}),
            ("status", {"ok": True, "sessions": 1, "request_count": -1})
        ]
        for action, response in cases:
            with self.subTest(action=action, response=response), patch(
                "client.socket.socket"
            ) as factory:
                factory.return_value.__enter__.return_value.recv.return_value = (
                    json.dumps(response).encode("utf-8")
                )
                with self.assertRaises(ValueError):
                    client.send_request({"action": action})


if __name__ == "__main__":
    unittest.main()
