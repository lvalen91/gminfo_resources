/* i2cwr: ONE deliberate single-byte I2C register write per invocation.
 * Build: zig cc -target x86_64-linux-musl -static -Os -Wall -Wextra -o i2cwr i2cwr.c
 * Bytes on the bus: exactly one I2C_RDWR transaction, one write message
 * [S addr+W reg val P]. No read-back, no multi-byte mode, no loop, by design,
 * so every bus write is one auditable command line.
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
#define WALL_GUARD_S      5   /* whole-run backstop: 3 s xfer timeout + margin */

static void on_alarm(int sig)
{
	static const char m[] =
		"i2cwr: wall-clock guard expired during write, aborting (write state UNKNOWN)\n";
	(void)sig;
	write(2, m, sizeof m - 1);
	_exit(3);
}

static __attribute__((noreturn)) void usage(void)
{
	fputs("usage: i2cwr <bus> <addr_hex> <reg_hex> <val_hex>\n"
	      "  write ONE byte: val (0x00..0xff) to reg (0x00..0xff) of addr (0x03..0x77) on /dev/i2c-<bus>\n"
	      "  one I2C_RDWR [S addr+W reg val P]; no read-back; I2C_SLAVE EBUSY -> report + exit 4\n"
	      "  sets adapter I2C_TIMEOUT=3s (persists on the adapter after exit); 5s wall guard\n"
	      "  exit: 0 ok, 1 setup err, 2 usage, 3 timeout/guard (write state unknown), 4 busy(driver),\n"
	      "        5 write failed (nack/other errno)\n",
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

static const char *errname(int e)
{
	switch (e) {
	case ENXIO:      return "ENXIO";
	case EREMOTEIO:  return "EREMOTEIO";
	case EIO:        return "EIO";
	case EAGAIN:     return "EAGAIN";
	case ETIMEDOUT:  return "ETIMEDOUT";
	case EINVAL:     return "EINVAL";
	case EOPNOTSUPP: return "EOPNOTSUPP";
	case EPROTO:     return "EPROTO";
	case ENODEV:     return "ENODEV";
	case EBUSY:      return "EBUSY";
	default:         return "errno";
	}
}

int main(int argc, char **argv)
{
	long bus, addr, reg, val;
	unsigned long funcs = 0;
	char dev[32];
	uint8_t wbuf[2];
	struct i2c_msg msg;
	struct i2c_rdwr_ioctl_data x;
	int fd, r, e;

	if (argc != 5) usage();
	if (parse_int(argv[1], 10, 0, 1 << 20, &bus) ||
	    parse_int(argv[2], 16, 0x03, 0x77, &addr) ||
	    parse_int(argv[3], 16, 0x00, 0xff, &reg) ||
	    parse_int(argv[4], 16, 0x00, 0xff, &val))
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

	/* I2C_RDWR itself ignores driver ownership; I2C_SLAVE is the busy check.
	 * Bail before any bus traffic if a kernel driver owns the address. */
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

	wbuf[0] = (uint8_t)reg;
	wbuf[1] = (uint8_t)val;
	msg.addr = (uint16_t)addr; msg.flags = 0; msg.len = 2; msg.buf = wbuf;
	x.msgs = &msg;
	x.nmsgs = 1;

	signal(SIGALRM, on_alarm);
	alarm(WALL_GUARD_S);
	r = ioctl(fd, I2C_RDWR, &x);
	e = errno;
	alarm(0);
	if (r >= 0 && r != 1) { r = -1; e = EIO; } /* ioctl returns msgs transferred */
	close(fd);

	if (r >= 0) {
		printf("%ld 0x%02lx write 0x%02lx=0x%02lx ok\n", bus, addr, reg, val);
		return 0;
	}
	fprintf(stderr, "%ld 0x%02lx write 0x%02lx=0x%02lx fail: %s %d (%s)%s\n", bus, addr, reg, val,
	        errname(e), e, strerror(e),
	        e == ETIMEDOUT ? ", bus stuck, write state UNKNOWN" : "");
	return e == ETIMEDOUT ? 3 : 5;
}
