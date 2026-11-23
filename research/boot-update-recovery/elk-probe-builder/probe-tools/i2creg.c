/* i2creg: read-only I2C register dump (combined write-reg + repeated-start read).
 * Build: zig cc -target x86_64-linux-musl -static -Os -Wall -Wextra -o i2creg i2creg.c
 * No write mode by design. The only bytes put on the bus are the 1-byte
 * register pointer inside each combined-format read transaction.
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

#define XFER_TIMEOUT_10MS 300 /* 3 s per transfer (I2C_TIMEOUT) */
#define WALL_GUARD_S      10  /* whole-run backstop */

/* Current output row, emitted with write() so the alarm handler can flush a
 * partial row async-signal-safely. Cells are stored before g_rowlen advances. */
static char g_row[8 + 16 * 3 + 2];
static volatile sig_atomic_t g_rowlen = 0;
static volatile sig_atomic_t g_reg = -1;

static void on_alarm(int sig)
{
	static const char hx[] = "0123456789abcdef";
	char m[] = "i2creg: wall-clock guard expired at reg 0x??, aborting\n";
	char *q = strstr(m, "??");
	int r = g_reg, n = g_rowlen;
	(void)sig;
	if (n > 0) { write(1, g_row, (size_t)n); write(1, "\n", 1); }
	if (q && r >= 0) { q[0] = hx[(r >> 4) & 0xf]; q[1] = hx[r & 0xf]; }
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

static __attribute__((noreturn)) void usage(void)
{
	fputs("usage: i2creg <bus> <addr_hex> r <start_hex> <end_hex>\n"
	      "  read regs start..end (0x00..0xff) of addr (0x03..0x77) on /dev/i2c-<bus>\n"
	      "  per reg: one I2C_RDWR [S addr+W reg Sr addr+R byte P]; '--' if it fails\n"
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

int main(int argc, char **argv)
{
	long bus, addr, start, end;
	unsigned long funcs = 0;
	char dev[32], cell[8];
	int fd, reg, nok = 0, nfail = 0, nerr = 0, stuck = 0;

	if (argc != 6) usage();
	if (parse_int(argv[1], 10, 0, 1 << 20, &bus) ||
	    parse_int(argv[2], 16, 0x03, 0x77, &addr) ||
	    strcmp(argv[3], "r") != 0 ||
	    parse_int(argv[4], 16, 0x00, 0xff, &start) ||
	    parse_int(argv[5], 16, 0x00, 0xff, &end) || start > end)
		usage();

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

	signal(SIGALRM, on_alarm);
	alarm(WALL_GUARD_S);

	for (reg = (int)start; reg <= (int)end; reg++) {
		uint8_t wbuf = (uint8_t)reg, rbuf = 0;
		struct i2c_msg msgs[2];
		struct i2c_rdwr_ioctl_data x;
		int r;

		g_reg = reg;
		if (g_rowlen == 0) {
			int c;
			snprintf(cell, sizeof cell, "%02x:", reg & 0xf0);
			row_put(cell, 3);
			for (c = reg & 0xf0; c < reg; c++) row_put("   ", 3); /* unaligned start */
		}

		msgs[0].addr = (uint16_t)addr; msgs[0].flags = 0;        msgs[0].len = 1; msgs[0].buf = &wbuf;
		msgs[1].addr = (uint16_t)addr; msgs[1].flags = I2C_M_RD; msgs[1].len = 1; msgs[1].buf = &rbuf;
		x.msgs = msgs;
		x.nmsgs = 2;
		r = ioctl(fd, I2C_RDWR, &x);
		if (r >= 0 && r != 2) { r = -1; errno = EIO; }

		if (r >= 0) {
			snprintf(cell, sizeof cell, " %02x", rbuf);
			nok++;
		} else {
			snprintf(cell, sizeof cell, " --");
			nfail++;
			switch (errno) {
			case ENXIO: case EREMOTEIO: case EIO: case EAGAIN:
				break; /* nack / arbitration: cell shows -- */
			case ETIMEDOUT:
				stuck = 1;
				break;
			default:
				fprintf(stderr, "reg 0x%02x err: %s\n", reg, strerror(errno));
				nerr++;
			}
		}
		row_put(cell, 3);
		if ((reg & 0xf) == 0xf || stuck) row_flush();
		if (stuck) {
			fprintf(stderr, "reg 0x%02x timeout: bus stuck, aborting\n", reg);
			break;
		}
	}
	row_flush();
	alarm(0);
	close(fd);

	fprintf(stderr, "%ld 0x%02lx: %d ok, %d fail (%d other err)%s\n", bus, addr, nok, nfail,
	        nerr, stuck ? ", ABORTED (timeout)" : "");
	return stuck ? 3 : 0;
}
