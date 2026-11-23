/* pcimem: read-only PCI BAR dump via /sys/bus/pci/devices/<bdf>/resource<N>.
 * Aligned volatile 32-bit reads only. No write mode.
 * Build: zig cc -target x86_64-linux-musl -static -Os -o pcimem pcimem.c
 */
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

static __attribute__((noreturn)) void usage(void)
{
	fputs("usage: pcimem <bdf> <barN> <offset_hex> <len_hex> [w32|w8]\n"
	      "  bdf DDDD:BB:DD.F or BB:DD.F; barN 0..5; offset/len hex, 4-byte aligned, within BAR\n"
	      "  read-only mmap of resource<N>, volatile aligned 32-bit reads only\n"
	      "  w32 (default) prints words; w8 prints the same reads as little-endian bytes\n",
	      stderr);
	exit(2);
}

static void on_sigbus(int sig)
{
	static const char m[] = "pcimem: SIGBUS during MMIO read, aborting\n";
	(void)sig;
	write(2, m, sizeof m - 1);
	_exit(4);
}

static int parse_hex(const char *s, unsigned long long *out)
{
	char *e;
	unsigned long long v;
	if (*s == '-' || *s == '+') return -1;
	errno = 0;
	v = strtoull(s, &e, 16);
	if (errno || e == s || *e) return -1;
	*out = v;
	return 0;
}

int main(int argc, char **argv)
{
	char path[256], bdf[32];
	const char *b;
	int colons = 0, bar, fd, bytes = 0;
	unsigned long long off, len, size, base, delta, maplen, i;
	long pg;
	struct stat st;
	void *map;
	const volatile uint32_t *p;

	setvbuf(stdout, NULL, _IOLBF, 0); /* keep completed lines if SIGBUS hits */
	if (argc != 5 && argc != 6) usage();

	b = argv[1];
	if (strlen(b) >= 20 || strchr(b, '/') || strstr(b, "..")) usage();
	for (const char *c = b; *c; c++) {
		if (*c == ':') colons++;
		else if (!(*c == '.' || (*c >= '0' && *c <= '9') ||
		           (*c >= 'a' && *c <= 'f') || (*c >= 'A' && *c <= 'F')))
			usage();
	}
	if (colons == 1) snprintf(bdf, sizeof bdf, "0000:%s", b);
	else if (colons == 2) snprintf(bdf, sizeof bdf, "%s", b);
	else usage();

	if (strlen(argv[2]) != 1 || argv[2][0] < '0' || argv[2][0] > '5') usage();
	bar = argv[2][0] - '0';
	if (parse_hex(argv[3], &off) || parse_hex(argv[4], &len)) usage();
	if (argc == 6) {
		if (!strcmp(argv[5], "w8")) bytes = 1;
		else if (strcmp(argv[5], "w32")) usage();
	}
	if (len == 0 || (off & 3) || (len & 3)) {
		fprintf(stderr, "offset and len must be 4-byte aligned, len > 0\n");
		return 2;
	}

	snprintf(path, sizeof path, "/sys/bus/pci/devices/%s/resource%d", bdf, bar);
	fd = open(path, O_RDONLY | O_CLOEXEC);
	if (fd < 0) { fprintf(stderr, "open %s: %s\n", path, strerror(errno)); return 1; }
	if (fstat(fd, &st) < 0) { fprintf(stderr, "fstat: %s\n", strerror(errno)); return 1; }
	size = (unsigned long long)st.st_size;
	if (size == 0) { fprintf(stderr, "%s: size 0 (BAR unassigned?)\n", path); return 1; }
	if (off >= size || len > size - off) {
		fprintf(stderr, "range 0x%llx+0x%llx exceeds BAR size 0x%llx\n", off, len, size);
		return 1;
	}

	pg = sysconf(_SC_PAGESIZE);
	if (pg <= 0) pg = 4096;
	base = off & ~((unsigned long long)pg - 1);
	delta = off - base;
	maplen = (delta + len + (unsigned long long)pg - 1) & ~((unsigned long long)pg - 1);

	map = mmap(NULL, (size_t)maplen, PROT_READ, MAP_SHARED, fd, (off_t)base);
	if (map == MAP_FAILED) {
		int e = errno;
		fprintf(stderr, "mmap %s @0x%llx len 0x%llx: %s\n", path, base, maplen, strerror(e));
		if (e == EINVAL)
			fputs("  (I/O-port BAR, or MEM region exclusive/busy under CONFIG_IO_STRICT_DEVMEM)\n", stderr);
		else if (e == EPERM || e == EACCES)
			fputs("  (needs root / CAP_SYS_ADMIN)\n", stderr);
		return 1;
	}
	close(fd);

	signal(SIGBUS, on_sigbus);
	p = (const volatile uint32_t *)((const volatile uint8_t *)map + delta);

	printf("%s bar%d size 0x%llx\n", bdf, bar, size);
	for (i = 0; i < len / 4; i++) {
		uint32_t v = p[i]; /* single aligned volatile 32-bit load */
		if ((i & 3) == 0) printf("%08llx:", off + i * 4);
		if (bytes)
			printf(" %02x %02x %02x %02x", v & 0xff, (v >> 8) & 0xff,
			       (v >> 16) & 0xff, (v >> 24) & 0xff);
		else
			printf(" %08x", v);
		if ((i & 3) == 3 || i + 1 == len / 4) putchar('\n');
	}
	fflush(stdout);
	munmap(map, (size_t)maplen);
	return 0;
}
