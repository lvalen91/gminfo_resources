/* Y175 slim-loader : Milestone-1.5 proof-of-slot shim (64-bit handoff).
 *
 * ROOT-CAUSE FIX (confirmed 3 ways + independent rasm2): the ABL IAS loader
 * ACCEPTS the IPK and jumps e_entry, but hands off with the CPU ALREADY IN
 * 64-BIT LONG MODE (paging on), a GHS/Harman extension of the Multiboot1
 * handoff -- eax=0x2BADB002 is kept, but it is NOT the MB1-spec 32-bit flat PM.
 * The real GHS entry at vaddr 0x200000 decodes as coherent x86-64 (REX.W
 * movabs of canonical 0xffff8000_xxxxxxxx kernel-half addresses). Our earlier
 * .code32 shim mis-decoded instruction #1-2 and triple-faulted -> instant
 * reset -> ELK. This shim is 64-bit, so it actually runs.
 *
 * Container is UNCHANGED: still assembled under -m32 and linked -m elf_i386, so
 * the IPK stays ELFCLASS32/EM_386 exactly like the real GHS image. .code64 only
 * switches the instruction encoder; e_entry still = segment base + 0xc.
 *
 * Milestone-1.5 is still hlt-only (no watchdog change) to preserve the existing
 * watchdog-reset -> ELK auto-recovery path. EXPECTED RESULT ON RETEST:
 *   - ELK returns after ~30-60 s of BLACK (TCO heartbeat=30s, reset on 2nd
 *     timeout)  => the shim RAN and held the CPU until the watchdog fired
 *     = CONTROL TRANSFER PROVEN / SLOT WORKS.
 *   - ELK returns within a second or two (as before) => still not executing
 *     (true load-reject) -- revisit the loader gate.
 * The low-DRAM 'SLIM' marker is a weak secondary signal only (DRAM is retrained
 * across the reset).
 */
    .section .text.mbhdr, "ax"
    .align 8
    .global _start

    /* Multiboot1 header -- plain data, mode-independent. flags=0x2 (MEMORY_INFO,
       no a.out-kludge), matching the real GHS image. */
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
    cld
    /* marker: write 'SLIM' + sentinel to low DRAM (register-indirect; avoids the
       64-bit A3 moffs pitfall that would swallow 8 address bytes) */
    movl  $0x4D494C53, %eax            /* 'SLIM' */
    movq  $0x000dc000, %rdi
    movl  %eax, (%rdi)                 /* ABL consbuf region */
    movq  $0x00001000, %rdi
    movl  %eax, (%rdi)
    movl  $0xB00710AD, %eax
    movq  $0x000dc004, %rdi
    movl  %eax, (%rdi)
1:  hlt
    jmp 1b
