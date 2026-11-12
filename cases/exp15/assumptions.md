# exp15 verification contract — main@10d248a

Target: unmodified myCPU/axi_bridge.v from commit 10d248abc6af8811e506909dd61cc3ddc498ccaf.

- Single clock aclk. Active-low synchronous aresetn, asserted for the first two sampled edges, then released. Mid-transaction/analog/asynchronous reset behavior is outside these runs.
- IF requests are word-aligned reads of size=2. MEM accesses are aligned byte/halfword/word transfers with legal write strobes. Address and payload otherwise range over their full widths.
- Requests and payload may change/withdraw before acceptance. Acceptance is req && addr_ok. No stability assumption is imposed on unaccepted class-SRAM requests.
- General profile permits up to TWO accepted, not-yet-completed requests per class-SRAM port. single_* permits ONE, matching current CPU intended usage. At the configured credit limit, the source pauses new requests. This is an explicit verification scope bound, not a proof of bridge capacity/backpressure behavior beyond it.
- ARREADY/AWREADY/WREADY are arbitrary and independent; AW/W may complete in either order. There is no eventual-ready assumption.
- R responses follow an earlier accepted AR with RID 0/1, in order within each ID; RLAST=1, RRESP=OKAY. Response data are arbitrary; different IDs may interleave. No response-latency bound or eventual response is assumed.
- B responses follow an earlier write whose AW and W both completed; BID=1 and BRESP=OKAY. B ordering follows the one write ID. R and B may coincide or arrive in either order.
- Slave response VALID and payload remain stable while blocked. No DUT output correctness is assumed.
- Safety/reachability checks only, not liveness or memory-content proofs. Independent request records check emitted payloads and class-SRAM completion order/data; AXI input data are not constrained to a RAM model.
- STABILITY_ONLY omits transaction-ledger assertions for independent covers. It still checks reset, fixed single-beat fields and stalled AXI payload/VALID stability.
- Combinational dependencies are checked separately. Four-state X/Z, implementation timing, whole-CPU behavior and board operation are outside this harness.
