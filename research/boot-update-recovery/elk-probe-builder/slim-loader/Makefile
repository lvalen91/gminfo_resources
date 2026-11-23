# Y175 slim-loader build. Produces shim.elf (ELF32 x86, MB1 header at image
# start, loaded/entered at 0x00200000), then IPK-packs it to shim_ghs.ipk.
CC      ?= gcc
LD      ?= ld
CFLAGS  = -m32 -ffreestanding -fno-pic -fno-stack-protector -nostdlib -Wall
LDFLAGS = -m elf_i386 -T linker.ld -nostdlib --build-id=none

all: shim_ghs.ipk

boot.o: boot.S
	$(CC) $(CFLAGS) -c boot.S -o boot.o

shim.elf: boot.o linker.ld
	$(LD) $(LDFLAGS) boot.o -o shim.elf

shim_ghs.ipk: shim.elf pack_ipk.py
	python3 -I pack_ipk.py shim.elf shim_ghs.ipk
	python3 -I verify_ipk.py shim_ghs.ipk

clean:
	rm -f boot.o shim.elf shim.bin shim_ghs.ipk

.PHONY: all clean
