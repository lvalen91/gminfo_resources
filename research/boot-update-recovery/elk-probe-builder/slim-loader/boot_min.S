/* Y175 slim-loader : minimal proof-of-CONTROL shim. 64-bit, ZERO memory access.
 * Only cli + hlt-loop. Isolates "did we get control and can we hold the CPU"
 * from "can we write to low DRAM at handoff". If THIS holds ~30-60s until the
 * TCO watchdog resets (vs fastboot returning in a few seconds), control transfer
 * works and the earlier marker writes were the fault. If it still fails fast,
 * the problem is the gate/handoff itself, not our code.
 */
    .section .text.mbhdr, "ax"
    .align 8
    .global _start
    .set MB_MAGIC, 0x1BADB002
    .set MB_FLAGS, 0x00000002
    .set MB_CKSUM, -(MB_MAGIC + MB_FLAGS)
mb_header:
    .long MB_MAGIC
    .long MB_FLAGS
    .long MB_CKSUM
    .code64
_start:
    cli
1:  hlt
    jmp 1b
