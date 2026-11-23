/* i2creg16: read-only I2C dump for devices with a 16-bit register/object address
 * (Atmel/Microchip maXTouch). Combined write-addr + repeated-start read.
 * Build: zig cc -target x86_64-linux-musl -static -Os -Wall -Wextra -o i2creg16 i2creg16.c
 *
 * No write mode by design. The only bytes put on the bus are the 2-byte address
 * pointer inside each combined-format read transaction.
 *
 * Address byte order: LSB first, then MSB (default). This is the maXTouch wire
 * format: mainline drivers/input/touchscreen/atmel_mxt_ts.c __mxt_read_reg()
 * sends buf[0] = reg & 0xff, buf[1] = reg >> 8. The 'msb' modifier flips it
 * for testing other 16-bit-address parts; it is not correct for maXTouch.
 *
 * Caveat: on maXTouch, reading the T5 message processor object dequeues the
 * message (side effect of a read). Avoid T5's address unless that is intended.
 */
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

/* linux/i2c-dev.h, linux/i2c.h (defined locally, no kernel headers needed) */
#define I2C_TIMEOUT 0x0702 /* arg: units of 10 ms */
#define I2C_SLAVE   0x0703
#define I2C_FUNCS   0x0705
#define I2C_RDWR    0x0707
#define I2C_M_RD    0x0001
#define F_I2C       0x00000001UL

struct i2c_msg {
	uint16_t addr;
	uint16_t flags;
	uint16_t len;
	uint8_t *buf;
};
struct i2c_rdwr_ioctl_data {
	struct i2c_msg *msgs;
	uint32_t nmsgs;
};

#define XFER_TIMEOUT_10MS 300    /* 3 s per transfer (I2C_TIMEOUT) */
#define WALL_GUARD_S      10     /* whole-run backstop */
#define MAX_COUNT         0x1000 /* < i2c-dev 8192-byte msg cap; fits uint16 len */

/* Current output row, emitted with write() so the alarm handler can flush a
 * partial row async-signal-safely. Cells are stored before g_rowlen advances. */
static char g_row[64]; /* "aaaa:" + 16 * " xx" + '\n' = 54 */
static volatile sig_atomic_t g_rowlen = 0;
static volatile sig_atomic_t g_reg = -1;

static void on_alarm(int sig)
{
	static const char hx[] = "0123456789abcdef";
	char m[] = "i2creg16: wall-clock guard expired at addr 0x????, aborting\n";
	char *q = strstr(m, "????");
	int r = g_reg, n = g_rowlen;
	(void)sig;
	if (n > 0) { write(1, g_row, (size_t)n); write(1, "\n", 1); }
	if (q && r >= 0) {
		q[0] = hx[(r >> 12) & 0xf]; q[1] = hx[(r >> 8) & 0xf];
		q[2] = hx[(r >> 4) & 0xf];  q[3] = hx[r & 0xf];
	}
	write(2, m, sizeof m - 1);
	_exit(3);
}

static void row_put(const char *s, size_t n)
{
	memcpy(g_row + g_rowlen, s, n);
	g_rowlen += (sig_atomic_t)n;
}

static void row_flush(void)
{
	if (g_rowlen > 0) {
		g_row[g_rowlen] = '\n';
		write(1, g_row, (size_t)g_rowlen + 1);
		g_rowlen = 0;
	}
}

/* One cell at 16-bit address a; rows of 16 aligned on a & ~0xf. */
static void emit(long a, int ok, uint8_t v)
{
	char cell[8];
	if (g_rowlen == 0) {
		long c;
		snprintf(cell, sizeof cell, "%04lx:", a & ~0xfL);
		row_put(cell, 5);
		for (c = a & ~0xfL; c < a; c++) row_put("   ", 3); /* unaligned start */
	}
	if (ok) snprintf(cell, sizeof cell, " %02x", v);
	else    memcpy(cell, " --", 4);
	row_put(cell, 3);
	if ((a & 0xf) == 0xf) row_flush();
}

static __attribute__((noreturn)) void usage(void)
{
	fputs("usage: i2creg16 <bus> <addr_hex> <start16_hex> <count_hex> [burst] [msb]\n"
	      "  read <count> (1..0x1000) bytes from 16-bit address start16 (0x0000..0xffff,\n"
	      "  no wrap) of addr (0x03..0x77) on /dev/i2c-<bus>\n"
	      "  default: per byte one I2C_RDWR [S addr+W lo hi Sr addr+R byte P], address\n"
	      "           re-sent each byte (no auto-increment assumed); '--' if it fails\n"
	      "  burst:   one I2C_RDWR [S addr+W lo hi Sr addr+R <count> bytes P]\n"
	      "           (tests in-transaction auto-increment); all '--' if it fails\n"
	      "  address bytes LSB first (maXTouch); 'msb' sends MSB first instead\n"
	      "  read-only (no write mode); I2C_SLAVE EBUSY -> report + exit 4\n"
	      "  sets adapter I2C_TIMEOUT=3s (persists on the adapter after exit); 10s wall guard\n"
	      "  exit: 0 ok, 1 setup err, 2 usage, 3 timeout/guard, 4 busy(driver)\n",
	      stderr);
	exit(2);
}

static int parse_int(const char *s, int base, long lo, long hi, long *out)
{
	char *e;
	long v;
	errno = 0;
	v = strtol(s, &e, base);
	if (errno || e == s || *e || v < lo || v > hi) return -1;
	*out = v;
	return 0;
}

static void put_addr(uint8_t w[2], long a, int msb)
{
	if (msb) { w[0] = (uint8_t)(a >> 8); w[1] = (uint8_t)a; }
	else     { w[0] = (uint8_t)a;        w[1] = (uint8_t)(a >> 8); }
}

/* Classify a failed transfer. Returns 1 if the bus looks stuck (timeout). */
static int classify(long a, int *nerr)
{
	switch (errno) {
	case ENXIO: case EREMOTEIO: case EIO: case EAGAIN:
		return 0; /* nack / arbitration: cell shows -- */
	case ETIMEDOUT:
		return 1;
	default:
		fprintf(stderr, "addr 0x%04lx err: %s\n", a, strerror(errno));
		(*nerr)++;
		return 0;
	}
}

static uint8_t g_buf[MAX_COUNT];

int main(int argc, char **argv)
{
	long bus, addr, start, count, a;
	unsigned long funcs = 0;
	char dev[32];
	int fd, i, burst = 0, msb = 0, nok = 0, nfail = 0, nerr = 0, stuck = 0;

	if (argc < 5 || argc > 7) usage();
	if (parse_int(argv[1], 10, 0, 1 << 20, &bus) ||
	    parse_int(argv[2], 16, 0x03, 0x77, &addr) ||
	    parse_int(argv[3], 16, 0x0000, 0xffff, &start) ||
	    parse_int(argv[4], 16, 1, MAX_COUNT, &count) ||
	    start + count - 1 > 0xffff)
		usage();
	for (i = 5; i < argc; i++) {
		if (!burst && strcmp(argv[i], "burst") == 0) burst = 1;
		else if (!msb && strcmp(argv[i], "msb") == 0) msb = 1;
		else usage();
	}

	snprintf(dev, sizeof dev, "/dev/i2c-%ld", bus);
	fd = open(dev, O_RDWR | O_CLOEXEC); /* i2c-dev needs O_RDWR for ioctls */
	if (fd < 0) { fprintf(stderr, "open %s: %s\n", dev, strerror(errno)); return 1; }

	if (ioctl(fd, I2C_FUNCS, &funcs) < 0) {
		fprintf(stderr, "I2C_FUNCS: %s\n", strerror(errno));
		return 1;
	}
	if (!(funcs & F_I2C)) {
		fprintf(stderr, "%ld: adapter lacks I2C_FUNC_I2C (funcs 0x%08lx); I2C_RDWR unavailable\n",
		        bus, funcs);
		return 1;
	}

	/* I2C_RDWR itself ignores driver ownership; I2C_SLAVE is the busy check. */
	if (ioctl(fd, I2C_SLAVE, (unsigned long)addr) < 0) {
		if (errno == EBUSY) {
			printf("%ld 0x%02lx busy(driver)\n", bus, addr);
			return 4;
		}
		fprintf(stderr, "%ld 0x%02lx I2C_SLAVE: %s\n", bus, addr, strerror(errno));
		return 1;
	}

	if (ioctl(fd, I2C_TIMEOUT, (unsigned long)XFER_TIMEOUT_10MS) < 0)
		fprintf(stderr, "%ld warn: I2C_TIMEOUT: %s (relying on wall guard)\n", bus, strerror(errno));

	printf("# bus %ld addr 0x%02lx start 0x%04lx count 0x%lx mode %s order %s\n",
	       bus, addr, start, count, burst ? "burst" : "per-byte", msb ? "msb-first" : "lsb-first");
	fflush(stdout); /* rows below go out via write() */

	signal(SIGALRM, on_alarm);
	alarm(WALL_GUARD_S);

	if (burst) {
		uint8_t wbuf[2];
		struct i2c_msg msgs[2];
		struct i2c_rdwr_ioctl_data x;
		int r;

		g_reg = (int)start;
		put_addr(wbuf, start, msb);
		msgs[0].addr = (uint16_t)addr; msgs[0].flags = 0;        msgs[0].len = 2;               msgs[0].buf = wbuf;
		msgs[1].addr = (uint16_t)addr; msgs[1].flags = I2C_M_RD; msgs[1].len = (uint16_t)count; msgs[1].buf = g_buf;
		x.msgs = msgs;
		x.nmsgs = 2;
		r = ioctl(fd, I2C_RDWR, &x);
		if (r >= 0 && r != 2) { r = -1; errno = EIO; }

		if (r >= 0) nok = (int)count;
		else { nfail = (int)count; stuck = classify(start, &nerr); }
		for (a = start; a < start + count; a++) emit(a, r >= 0, g_buf[a - start]);
		row_flush();
		if (stuck) fprintf(stderr, "addr 0x%04lx timeout: bus stuck\n", start);
	} else {
		for (a = start; a < start + count; a++) {
			uint8_t wbuf[2], rbuf = 0;
			struct i2c_msg msgs[2];
			struct i2c_rdwr_ioctl_data x;
			int r;

			g_reg = (int)a;
			put_addr(wbuf, a, msb);
			msgs[0].addr = (uint16_t)addr; msgs[0].flags = 0;        msgs[0].len = 2; msgs[0].buf = wbuf;
			msgs[1].addr = (uint16_t)addr; msgs[1].flags = I2C_M_RD; msgs[1].len = 1; msgs[1].buf = &rbuf;
			x.msgs = msgs;
			x.nmsgs = 2;
			r = ioctl(fd, I2C_RDWR, &x);
			if (r >= 0 && r != 2) { r = -1; errno = EIO; }

			if (r >= 0) nok++;
			else { nfail++; stuck = classify(a, &nerr); }
			emit(a, r >= 0, rbuf);
			if (stuck) {
				row_flush();
				fprintf(stderr, "addr 0x%04lx timeout: bus stuck, aborting\n", a);
				break;
			}
		}
		row_flush();
	}
	alarm(0);
	close(fd);

	fprintf(stderr, "%ld 0x%02lx: %d ok, %d fail (%d other err)%s\n", bus, addr, nok, nfail,
	        nerr, stuck ? ", ABORTED (timeout)" : "");
	return stuck ? 3 : 0;
}
