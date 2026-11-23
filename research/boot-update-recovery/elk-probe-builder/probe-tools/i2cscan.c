/* i2cscan: read-only I2C bus probe (SMBus receive-byte, never writes).
 * Build: zig cc -target x86_64-linux-musl -static -Os -o i2cscan i2cscan.c
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
#define I2C_SMBUS   0x0720
#define I2C_SMBUS_READ 1
#define I2C_SMBUS_BYTE 1

#define F_I2C             0x00000001UL
#define F_SMBUS_READ_BYTE 0x00020000UL

union i2c_smbus_data { uint8_t byte; uint16_t word; uint8_t block[34]; };
struct i2c_smbus_ioctl_data {
	uint8_t read_write;
	uint8_t command;
	uint32_t size;
	union i2c_smbus_data *data;
};

static const struct { unsigned long bit; const char *name; } fnames[] = {
	{0x00000001, "I2C"},             {0x00000002, "10BIT_ADDR"},
	{0x00000004, "PROTOCOL_MANGLING"}, {0x00000008, "SMBUS_PEC"},
	{0x00000010, "NOSTART"},         {0x00000020, "SLAVE"},
	{0x00008000, "SMBUS_BLOCK_PROC_CALL"}, {0x00010000, "SMBUS_QUICK"},
	{0x00020000, "SMBUS_READ_BYTE"}, {0x00040000, "SMBUS_WRITE_BYTE"},
	{0x00080000, "SMBUS_READ_BYTE_DATA"}, {0x00100000, "SMBUS_WRITE_BYTE_DATA"},
	{0x00200000, "SMBUS_READ_WORD_DATA"}, {0x00400000, "SMBUS_WRITE_WORD_DATA"},
	{0x00800000, "SMBUS_PROC_CALL"}, {0x01000000, "SMBUS_READ_BLOCK_DATA"},
	{0x02000000, "SMBUS_WRITE_BLOCK_DATA"}, {0x04000000, "SMBUS_READ_I2C_BLOCK"},
	{0x08000000, "SMBUS_WRITE_I2C_BLOCK"}, {0x10000000, "SMBUS_HOST_NOTIFY"},
};

#define XFER_TIMEOUT_10MS 300 /* 3 s per transfer (I2C_TIMEOUT) */
#define WALL_GUARD_S      5   /* whole-bus backstop: 3 s xfer timeout + margin */

static volatile sig_atomic_t g_addr = -1;

static void on_alarm(int sig)
{
	static const char hx[] = "0123456789abcdef";
	char m[] = "i2cscan: wall-clock guard expired at addr 0x??, aborting\n";
	char *q = strstr(m, "??");
	int a = g_addr;
	(void)sig;
	if (q && a >= 0) { q[0] = hx[(a >> 4) & 0xf]; q[1] = hx[a & 0xf]; }
	write(2, m, sizeof m - 1);
	_exit(3);
}

static __attribute__((noreturn)) void usage(void)
{
	fputs("usage: i2cscan <bus> [first last]\n"
	      "  probe /dev/i2c-<bus>, addrs first..last (default 0x08 0x77, allowed 0x03..0x77)\n"
	      "  read-only: I2C_SLAVE (EBUSY -> busy(driver)) + SMBus receive-byte; read() fallback\n"
	      "  sets adapter I2C_TIMEOUT=3s (persists on the adapter after exit); 5s wall guard\n"
	      "  out: '<bus> <addr> ack <value>' | '<bus> <addr> busy(driver)', then a count line\n",
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
	long bus, first = 0x08, last = 0x77;
	unsigned long funcs = 0;
	char dev[32];
	int fd, use_smbus, a, nack = 0, nbusy = 0, nerr = 0, stuck = 0;
	size_t i;

	setvbuf(stdout, NULL, _IOLBF, 0);
	if (argc != 2 && argc != 4) usage();
	if (parse_int(argv[1], 10, 0, 1 << 20, &bus)) usage();
	if (argc == 4 && (parse_int(argv[2], 0, 0x03, 0x77, &first) ||
	                  parse_int(argv[3], 0, 0x03, 0x77, &last) || first > last))
		usage();

	snprintf(dev, sizeof dev, "/dev/i2c-%ld", bus);
	fd = open(dev, O_RDWR | O_CLOEXEC); /* i2c-dev needs O_RDWR for ioctls; no writes issued */
	if (fd < 0) { fprintf(stderr, "open %s: %s\n", dev, strerror(errno)); return 1; }

	if (ioctl(fd, I2C_FUNCS, &funcs) < 0) {
		fprintf(stderr, "I2C_FUNCS: %s\n", strerror(errno));
		return 1;
	}
	printf("%ld funcs 0x%08lx", bus, funcs);
	for (i = 0; i < sizeof fnames / sizeof fnames[0]; i++)
		if (funcs & fnames[i].bit) printf(" %s", fnames[i].name);
	putchar('\n');

	if (funcs & F_SMBUS_READ_BYTE) {
		use_smbus = 1;
	} else if (funcs & F_I2C) {
		use_smbus = 0;
		printf("%ld note: no SMBUS_READ_BYTE, using 1-byte read()\n", bus);
	} else {
		fprintf(stderr, "%ld: adapter supports neither SMBUS_READ_BYTE nor I2C; cannot probe read-only\n", bus);
		return 1;
	}

	if (ioctl(fd, I2C_TIMEOUT, (unsigned long)XFER_TIMEOUT_10MS) < 0)
		fprintf(stderr, "%ld warn: I2C_TIMEOUT: %s (relying on wall guard)\n", bus, strerror(errno));

	signal(SIGALRM, on_alarm);
	alarm(WALL_GUARD_S);

	for (a = (int)first; a <= (int)last; a++) {
		unsigned char v = 0;
		int r;

		g_addr = a;
		/* Never fall through to a read after a failed I2C_SLAVE: the fd would
		 * still be bound to the previous address. */
		if (ioctl(fd, I2C_SLAVE, (unsigned long)a) < 0) {
			if (errno == EBUSY) {
				printf("%ld 0x%02x busy(driver)\n", bus, a);
				nbusy++;
			} else {
				fprintf(stderr, "%ld 0x%02x I2C_SLAVE: %s\n", bus, a, strerror(errno));
				nerr++;
			}
			continue;
		}

		if (use_smbus) {
			union i2c_smbus_data d;
			struct i2c_smbus_ioctl_data args;
			memset(&d, 0, sizeof d);
			args.read_write = I2C_SMBUS_READ;
			args.command = 0;
			args.size = I2C_SMBUS_BYTE;
			args.data = &d;
			r = ioctl(fd, I2C_SMBUS, &args);
			v = d.byte;
		} else {
			ssize_t n = read(fd, &v, 1);
			if (n == 1) r = 0;
			else { r = -1; if (n >= 0) errno = EIO; }
		}

		if (r == 0) {
			printf("%ld 0x%02x ack 0x%02x\n", bus, a, v);
			nack++;
			continue;
		}
		switch (errno) {
		case ENXIO: case EREMOTEIO: case EIO:
			break; /* no ack */
		case ETIMEDOUT:
			fprintf(stderr, "%ld 0x%02x timeout: bus stuck, aborting scan\n", bus, a);
			stuck = 1;
			break;
		default:
			fprintf(stderr, "%ld 0x%02x err: %s\n", bus, a, strerror(errno));
			nerr++;
		}
		if (stuck) break;
	}
	alarm(0);
	close(fd);

	printf("%ld count: %d ack, %d busy, %d err%s\n", bus, nack, nbusy, nerr,
	       stuck ? ", ABORTED (timeout)" : "");
	return stuck ? 3 : 0;
}
