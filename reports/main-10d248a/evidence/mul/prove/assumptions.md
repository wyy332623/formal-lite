# mul contract

- DUT: `myCPU/mul.v`, fixed commit and SHA-256 in source.json / sources.lock.json.
- Pure combinational 32x32 -> 64-bit product. `clk` is only the formal sampling clock; DUT has no clock, reset, latency, handshake or outstanding transaction state.
- `mul_signed=0`: unsigned product. `mul_signed=1`: two's-complement signed product. Both operands use the same signedness. All 64 output bits are checked.
- `prove` / `bmc`: arbitrary 32-bit operands and signedness at every sample. No output assumptions. Oracle: unsigned product minus sign corrections modulo 2^64, independently expressed from DUT signed 33-bit extension.
- `small`: full-width DUT with operands restricted to unsigned 8-bit values or sign-extended signed 8-bit values. This proves ONLY that input subdomain.
- `corners`: 128 constant instances, all 8x8 operand pairs in both signed/unsigned modes from {0, 1, 0xffffffff, 0x80000000, 0x7fffffff, 0xffff0000, 0x00010000, 0xaaaaaaaa}. Reference products use explicit signed 64-bit / unsigned 64-bit language semantics, not the DUT's 33-bit format. These are ONLY 128 directed full-width examples, not arbitrary x or y. Constant instances avoid a hard variable-multiplier equivalence query.
- `cover`: unrestricted input reachability, with product assertions enabled.
- `fault`: deliberate checker-output bit flip under SMALL_OPERANDS. Must FAIL and emit VCD; not a DUT defect.
- A timeout/unknown on the full-width multiplier is an incomplete proof, never converted into a pass by the restricted tasks.
