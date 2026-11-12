# Smoke model assumptions

- Single-clock synchronous model.
- Reset is asserted at the first sampled edge, then remains deasserted.
- Input valid, payload and receiver ready are otherwise unconstrained.
- No eventual-ready assumption is used: this is a safety proof, not a completion proof.

Assertions: an output held under backpressure keeps its valid and payload.
Cover: two or more stalled cycles followed by acceptance.
The `fault` task deliberately overwrites stalled payloads and must produce FAIL plus a VCD counterexample. This expected failure validates the checker; it is not a design passing its properties.
