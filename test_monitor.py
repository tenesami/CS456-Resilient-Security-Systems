import io
import subprocess
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

import monitor


class MonitorRecoveryTests(unittest.TestCase):
    def run_with_clock(self, start, stop_at, heartbeats=(1,), traffic=False):
        clock = [0]
        sock = Mock()
        output = io.StringIO()

        def receive(_):
            clock[0] += 1
            if clock[0] == stop_at:
                raise KeyboardInterrupt()
            if clock[0] in heartbeats:
                return b"HEARTBEAT", ("127.0.0.1", 12345)
            if traffic:
                return b"OTHER", ("127.0.0.1", 12345)
            raise TimeoutError()

        sock.recvfrom.side_effect = receive
        with patch("monitor.socket.socket", return_value=sock), patch(
            "monitor.time.monotonic", side_effect=lambda: clock[0]
        ), patch("monitor.TIMEOUT", 2), patch(
            "monitor.INITIAL_RETRY_DELAY", 1
        ), patch("monitor.MAX_RETRY_DELAY", 4), patch(
            "monitor.start_service", side_effect=lambda: start(clock[0])
        ), patch("monitor.logging.warning"), patch(
            "monitor.logging.error"
        ), redirect_stdout(output):
            monitor.run_monitor()

        sock.close.assert_called_once_with()
        return output.getvalue()

    def test_retries_replacement_that_exits_before_first_heartbeat(self):
        for returncode in (0, 1):
            with self.subTest(returncode=returncode):
                first = Mock(pid=101)
                first.poll.return_value = returncode
                second = Mock(pid=102)
                second.poll.return_value = None
                clock = [0]
                sock = Mock()

                def receive(_):
                    clock[0] += 1
                    if clock[0] in (1, 7):
                        return b"HEARTBEAT", ("127.0.0.1", 12345)
                    if clock[0] == 8:
                        raise KeyboardInterrupt()
                    raise TimeoutError()

                sock.recvfrom.side_effect = receive
                with patch("monitor.socket.socket", return_value=sock), patch(
                    "monitor.time.monotonic", side_effect=lambda: clock[0]
                ), patch("monitor.TIMEOUT", 2), patch(
                    "monitor.start_service", side_effect=[first, second]
                ) as start, patch("monitor.logging.warning"), patch(
                    "monitor.logging.error"
                ), redirect_stdout(io.StringIO()):
                    monitor.run_monitor()

                self.assertEqual(start.call_count, 2)
                first.poll.assert_called()
                sock.close.assert_called_once_with()

    def test_launch_failures_retry_with_capped_exponential_backoff(self):
        child = Mock(pid=102)
        child.poll.return_value = None
        launches = []

        def start(now):
            launches.append(now)
            return child if len(launches) == 5 else None

        self.run_with_clock(start, 17, heartbeats=(1, 16))
        self.assertEqual(launches, [4, 5, 7, 11, 15])

    def test_alive_child_without_heartbeat_is_not_replaced(self):
        child = Mock(pid=102)
        child.poll.return_value = None
        launches = []

        def start(now):
            launches.append(now)
            return child

        output = self.run_with_clock(start, 12)
        self.assertEqual(launches, [4])
        self.assertEqual(output.count("running without a recovery heartbeat"), 1)
        child.terminate.assert_called_once_with()
        child.wait.assert_called_once_with(timeout=monitor.SHUTDOWN_TIMEOUT)

    def test_recovery_heartbeat_resets_backoff(self):
        first = Mock(pid=101)
        first.poll.side_effect = [None, None, None, 0]
        second = Mock(pid=102)
        second.poll.return_value = None
        launches = []
        results = iter([None, first, second])

        def start(now):
            launches.append(now)
            return next(results)

        self.run_with_clock(start, 12, heartbeats=(1, 6, 11))
        self.assertEqual(launches, [4, 5, 10])

    def test_continuous_unrelated_packets_do_not_starve_retries(self):
        first = Mock(pid=101)
        first.poll.return_value = 1
        second = Mock(pid=102)
        second.poll.return_value = None
        launches = []
        results = iter([first, second])

        def start(now):
            launches.append(now)
            return next(results)

        self.run_with_clock(start, 8, heartbeats=(1, 7), traffic=True)
        self.assertEqual(launches, [4, 6])

    def test_shutdown_escalates_and_waits_for_current_child(self):
        child = Mock(pid=102)
        child.poll.return_value = None
        child.wait.side_effect = [
            subprocess.TimeoutExpired("service", monitor.SHUTDOWN_TIMEOUT), 0
        ]
        with redirect_stdout(io.StringIO()):
            monitor.stop_service(child)

        child.terminate.assert_called_once_with()
        child.kill.assert_called_once_with()
        self.assertEqual(child.wait.call_count, 2)

    def test_shutdown_does_not_terminate_already_exited_child(self):
        child = Mock(pid=102)
        child.poll.return_value = 0
        monitor.stop_service(child)
        child.terminate.assert_not_called()
        child.kill.assert_not_called()


if __name__ == "__main__":
    unittest.main()
