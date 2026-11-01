
# CS456 Mini Group Project 1: Resilient Security Systems

## Project Overview

This project demonstrates fault detection and heartbeat spoofing
in a lightweight security service.

The prototype implements a simple authentication service,
a service-owning heartbeat monitor, and an adversarial audit script.

## Development Environment

- Operating System: Kali Linux (VirtualBox)
- Programming Language: Python 3
- Communication: UDP over 127.0.0.1
- Monitor Port: 9999

## Project Files

- service.py: Security service with random crash simulation
- client.py: Simulated client creating and repeatedly checking a session
- monitor.py: Service supervisor and authenticated heartbeat monitor
- heartbeat.py: Shared HMAC heartbeat encoding and verification
- checkpoint.py: Shared state persistence and restoration
- attacker.py: Heartbeat spoofing attack simulation
- CONTRIBUTIONS.md: Team member contributions
- incidents.log: Timestamped failure records

## System Architecture

The system uses a push-based heartbeat mechanism.

The monitor binds its heartbeat socket, then launches the initial security
service. The service sends an authenticated heartbeat every 2 seconds.

The monitor tracks received heartbeats and raises a
failure alert when no heartbeat arrives for more than
5 seconds.

The monitor operates independently and continues running
even when the security service terminates.

When its child exits, the monitor launches a new instance of service.py
using the same Python interpreter, with capped exponential retry backoff
for failed launches and children that exit before recovery.
Every service instance restores the shared checkpoint, binds the
client endpoint at 127.0.0.1:10000, and uses the same request,
heartbeat, and checkpoint logic. State changes are saved before
successful responses are sent.

Monitor launched instances of service are child processes. PIDs are
recorded in service.pid file for future process management capability.

The monitor never starts another replacement while its retained child is
still alive. Monitor-owned children run without interactive stdin and are
stopped and reaped when the monitor exits.

For every launch, the monitor generates a fresh 256-bit secret using
`secrets.token_hex(32)` and passes it only through the child's environment
(`SERVICE_HEARTBEAT_SECRET`) variable.
The service removes the variable from its environment after reading it.
Heartbeat packets contain a protocol version, increasing sequence number,
Unix timestamp, and HMAC-SHA256 signature. The secret is never transmitted.
The monitor accepts only valid signatures for the current child's key,
strictly increasing sequences, and timestamps no more than 5 seconds old
and not in the future. Invalid packets are rejected and logged without
resetting outage detection or retry backoff. Key rotation rejects packets
from previous children, including after a monitor restart.

## Running the Project

Open two terminals for normal operation, plus an optional attack terminal
in Kali Linux.

### Terminal 1: Start Monitor

```text
python3 monitor.py
```

The monitor starts both the initial service and any replacements
automatically. Do not start service.py separately: it requires the
monitor-generated secret and fails explicitly when it is missing or invalid.
The service uses a random failure probability of 0.10 per heartbeat
interval to simulate unpredictable failures.

### Terminal 2: Start Client

With the monitor running, run:

```text
python3 client.py
```

The client logs in with the demo creds, then checks the
active session. This updates the service request_count
and creates checkpoint data to actually fail-over.

### Optional Terminal 3: Start Attack Simulation

```text
python3 attacker.py
```

The attacker sends plaintext forged heartbeat messages every
2 seconds to the monitor. These are now rejected and recorded in incidents.log.

Press Ctrl+C to stop a running process.

## Baseline Experiment Results (Before Heartbeat Authentication)

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

The original baseline heartbeat protocol did not authenticate
heartbeat messages. Any local process capable of sending
the expected UDP payload can potentially spoof liveness.

The experiment demonstrated successful false recovery
after a legitimate service failure.

The current protocol authenticates heartbeat messages and checks freshness
and sequence numbers to reject spoofing and replay attempts without the key.

## Limitations

This is an educational prototype running on the local
loopback interface, not a production security system.
Authentication does not protect against privileged local attackers or
processes able to inspect the monitor's or child's memory/environment.
Heartbeats are authenticated, not encrypted. Timestamp checks assume a
stable local wall clock; heartbeat outage timers use a monotonic clock.
The current implementation does not automatically stop or fence an
unresponsive service. A hung child is reported but is not replaced until
its exit is confirmed, avoiding duplicate monitor-owned instances.
This is not yet safe failover.
