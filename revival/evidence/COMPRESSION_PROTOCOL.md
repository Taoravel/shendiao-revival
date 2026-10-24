# GNET downstream compression evidence

Method: `research` uses the mapped original executable as the primary source;
`codebase-design` places MPPC history management behind the small
`Encoder.encode(plaintext) -> bytes` interface. No compressor state belongs in
callers other than keeping one Encoder per connection.

## Confirmed direction and factory

The parent authentication investigation established native security factory
type 2 is ARCFourSecurity (constructor `0x78cd00`, vtable `0x2472044`) and type 6
is DecompressARCFourSecurity (constructor `0x78d600`, vtable `0x24720c4`).
The latter's Update slot is `0x78d670`: it calls the embedded RC4 Update first,
then `0x78c390` on its embedded decompressor at object offset `0x118`.
Consequently the server downlink pipeline is plaintext protocol frame -> MPPC
encoding -> continuous RC4. The client uplink uses plain continuous RC4.
These direction labels follow the authentication agent's installation analysis;
this investigation independently confirms the type 6 Update call order.

## Bitstream (directly verified against original decoder)

- Bits are most significant first.
- Literal byte 0..127 is its ordinary 8 bits.
- Literal byte 128..255 is `10` followed by its low seven bits (9 bits total).
- Offset-zero token `1111000000` terminates a block. Zero bits align the next
  block to the next byte. There is no PPP header, coherence counter, or extra
  MPPC length field on this stream.
- Example plaintext `010203807f80ff` encodes as `010203803fc02ffe00`.
- The dictionary write position persists across block terminators and input
  calls. At a terminator the original decoder resets its history pointer only
  when it equals the end of its 8192-byte history.
- Therefore an Encoder must split blocks at the next history wrap even when
  that occurs partway through a protocol frame. Resetting an Encoder for each
  send is incorrect after enough accumulated plaintext.

Native proof locations in `native-image.bin` (loaded at `0x400000`):

- `0x78c390`: decompressor Update; preserves unfinished input using Octets.
- `0x78c4a0`..`0x78c51e`: 8-bit / 9-bit literal branches.
- `0x78c51e`..`0x78c5af`: 10-bit short-offset branch, zero-offset flush,
  alignment, and wrap only when history cursor equals `0x2000`.
- `0x78c8d2`..`0x78c91e`: rollback an incomplete token at a fragmented input.
- `0x78c91e`..`0x78c966`: return emitted plaintext and retain pending bytes.
- `0x1918cb0`: original pure compressor, independently executed by
  `research_auth.py --self-check` (four matching literal encodings).

[RFC 2118, section 4.1](https://www.rfc-editor.org/rfc/rfc2118#section-4.1)
provides the matching standard literal vocabulary. Its PPP packet wrapper is
not the GNET transport wrapper. GNET's zero-offset EOS and stream lifetime
above are findings from the executable, not assumptions from the RFC.

## Implementation and validation

`revival/mppc.py` deliberately emits only legal literal tokens. It trades
compression ratio for a small, predictable implementation; no history references
or compressor match search are needed. Per-connection position tracking is
retained because the receiving decoder still writes every literal to history.

`revival/verify_mppc_native.py` runs the actual original x86 decoder with Unicorn
against this encoder. Only four Octets allocation/append/erase helpers are
replaced by ordinary private buffers; bit parsing, EOS, input rollback and history
remain original executable instructions. No running client is accessed.

Validation passed:

- 30 cases: plaintext sizes 0, 1, 7, 256, 8192 and 20000; input delivered in
  chunks of 1, 2, 3, 7 and whole encoded length.
- 12 consecutive encode/decode operations on the same Encoder/decoder pair,
  including empty blocks, nonzero starting history cursor, and multiple wraps.
- The initial stateless-per-frame implementation failed the consecutive-stream
  check. This failure led to the connection-owned Encoder; the corrected version
  passes. This is why callers must keep Encoder state.

Machine-readable results: `mppc-native-validation.json` in this directory.
Reproduce with the bundled Python executable and `revival/verify_mppc_native.py`.

Unverified here: RC4 keys/handshake integration, actual client network acceptance,
role creation/world packets, match-reference compression, and malformed input
behavior. The production encoder intentionally does not implement decompression.
