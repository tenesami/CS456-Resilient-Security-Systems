
# CS456 Mini Group Project 1: Resilient Security Systems

## Project Overview

This project demonstrates fault detection and heartbeat spoofing
in a lightweight security service.

The prototype implements a simple authentication service,
an independent heartbeat monitor, and an adversarial audit script.

## Development Environment

- Operating System: Kali Linux (VirtualBox)
- Programming Language: Python 3
- Communication: UDP over 127.0.0.1
- Monitor Port: 9999

## Project Files

- service.py: Security service with random crash simulation
- monitor.py: Independent heartbeat monitor
- checkpoint.py: Shared state persistence and restoration
- attacker.py: Heartbeat spoofing attack simulation
- CONTRIBUTIONS.md: Team member contributions
- incidents.log: Timestamped failure records

## System Architecture

The system uses a push-based heartbeat mechanism.

The security service sends a HEARTBEAT message to the
monitor every 2 seconds.

The monitor tracks received heartbeats and raises a
failure alert when no heartbeat arrives for more than
5 seconds.

The monitor operates independently and continues running
even when the security service terminates.

When a heartbeat timeout is detected, the monitor launches a
new instance of service.py using the same Python interpreter.
Every service instance restores the shared checkpoint, binds the
client endpoint at 127.0.0.1:10000, and uses the same request,
heartbeat, and checkpoint logic. State changes are saved before
successful responses are sent.

Monitor launched instances of service are child processes. PIDs are
recorded in service.pid file for future process management capability.

## Running the Project

Open three terminals in Kali Linux.

### Terminal 1: Start Monitor

python3 monitor.py

### Terminal 2: Start Security Service

python3 service.py

The service sends heartbeat messages every 2 seconds.
It uses a random probability of 0.10 per loop iteration
to simulate unpredictable failures.

### Terminal 3: Start Attack Simulation

python3 attacker.py

The attacker sends forged heartbeat messages every
2 seconds to the monitor.

Press Ctrl+C to stop a running process.

## Test Results

1. The service successfully generated random failures.
2. The monitor detected missing heartbeats after
   approximately 5 seconds.
3. Failure alerts were saved in incidents.log.
4. The attacker successfully injected forged heartbeats.
5. The monitor accepted forged messages and falsely
   reported service recovery.
6. When forged heartbeats stopped, the monitor generated
   another timeout alert.

## Security Assessment

The baseline heartbeat protocol does not authenticate
heartbeat messages. Any local process capable of sending
the expected UDP payload can potentially spoof liveness.

The experiment demonstrated successful false recovery
after a legitimate service failure.

A possible improvement would be authenticated heartbeat
messages with freshness checks to prevent spoofing
and replay attacks.

## Limitations

This is an educational prototype running on the local
loopback interface, not a production security system.
The monitor does not authenticate heartbeat senders.
The current implementation does not automatically
stop or fence an unresponsive service before launching its replacement.
A hung service can still hold the client port, causing the replacement
to fail to bind. This consolidation is not yet safe failover.
