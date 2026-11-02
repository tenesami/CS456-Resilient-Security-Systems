
# CS456 Mini Group Project 1: Parts 1 and 2
## Team Contributions

### Tesfaye Atomsa

**Development Environment**
- Configured Kali Linux in VirtualBox.
- Verified Python 3 and the project environment.

**Critical Security Service**
- Implemented and tested the Python security service.
- Configured non-deterministic failure simulation.
- Verified service execution and random crashes.

**Heartbeat Monitoring**
- Implemented and tested UDP heartbeat communication.
- Verified the five-second failure detection threshold.
- Implemented timestamped incident logging.

**Adversarial Assessment**
- Implemented and tested the heartbeat spoofing script.
- Demonstrated false service recovery using forged heartbeats.
- Verified failure detection after spoofing stopped.

**Documentation and Testing**
- Collected test results and screenshots.
- Prepared project documentation.

## Additional Team Members

### Nathaniel DeLeon
Video Recording

## Video Demonstration

Nathaniel DeLeon
- Recorded and narrated the video demonstration.
- Demonstrated the security service, heartbeat monitor, and attacker script.
- Explained the random service failure, heartbeat detection, and spoofing attack.

**Adversarial Testing**
- Created "audit_checkpoint." to test checkpoint corruption and restoration.
- Created "audit_false_failover.py" to simulate missing heartbeats while the primary service is still running.
- Submitted both adversarial scripts through separate GitHub pull requests.
- Investigated a heartbeat permission error during false failover testing and updated the script to block incoming packets instead.

**Code Review and Collaboration**
- Reviewed and merged pull requests for the updated recovery implementation.
- Helped integrate changes into the main repository.
- Resolved a README merge conflict.

**Documentation and Demonstration**
- Documented the adversarial testing scripts and their purpose.
- Responsible for recording and narrating the final video demonstration.
- Responsible for submitting the completed group assignment through Canvas.


