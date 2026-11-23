/* Load/run at 0x00200000 -- the exact physical base the real GHS ELF loads at
 * (PH0 vaddr/paddr=0x00200000), so the address is proven clear on this SoC.
 * The MB1 header section is forced first so it sits at the image start, well
 * within the first 8 KiB. e_entry = _start (ENTRY below). */
ENTRY(_start)
SECTIONS
{
    . = 0x00200000;
    .text : {
        *(.text.mbhdr)
        *(.text .text.*)
        *(.rodata*)
        *(.data*)
    }
    _load_end = .;
    .bss : { *(.bss) *(COMMON) }
    _bss_end = .;
    /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
