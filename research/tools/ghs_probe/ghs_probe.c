#include <jni.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <linux/types.h>

/* Trusty IPC ioctl definitions (from kernel headers) */
#define TIPC_IOC_MAGIC          'r'
#define TIPC_IOC_CONNECT        _IOW(TIPC_IOC_MAGIC, 0x80, char *)

/* GHS comms ioctl — these are guesses based on typical char device patterns.
 * The actual values would need to come from reversing the kernel driver. */
#define GHS_IOC_MAGIC           'g'
#define GHS_IOC_GET_VERSION     _IOR(GHS_IOC_MAGIC, 0x01, int)
#define GHS_IOC_SEND_MSG        _IOW(GHS_IOC_MAGIC, 0x02, char *)

/* Known Trusty service names to probe */
static const char *trusty_services[] = {
    "com.android.trusty.gatekeeper",
    "com.android.trusty.keymaster",
    "com.android.trusty.keymaster.secure",
    "com.android.trusty.storage",
    "com.android.trusty.secure_dpu",
    "com.android.trusty.confirmationui",
    "com.android.trusty.hwkey",
    "com.android.trusty.hwrng",
    "com.android.trusty.avb",
    "com.android.trusty.crash_test",
    NULL
};

/* GHS device paths */
static const char *ghs_devices[] = {
    "/dev/ghs/cal",
    "/dev/ghs/camera",
    "/dev/ghs/chime",
    "/dev/ghs/ipc",
    "/dev/ghs/ota-isys",
    "/dev/ghs/tee-att",
    "/dev/ghs/audit",
    "/dev/ghs/capture",
    "/dev/ghs/emmc-health",
    "/dev/ghs/textlog",
    "/dev/ghs/snapshot-dbg",
    "/dev/ghscamerafb",
    NULL
};

/* Other interesting devices */
static const char *other_devices[] = {
    "/dev/trusty-ipc-dev0",
    "/dev/ion",
    "/dev/binder",
    "/dev/hwbinder",
    "/dev/vndbinder",
    "/dev/i2c-0",
    "/dev/i2c-1",
    "/dev/i2c-2",
    "/dev/i2c-3",
    "/dev/i2c-7",
    "/dev/ttyACM1",
    "/dev/ttyS0",
    "/dev/ttyS1",
    "/dev/spidev1.0",
    "/dev/spidev2.0",
    "/dev/mei0",
    NULL
};

static char result_buf[65536];
static int buf_pos = 0;

static void log_result(const char *fmt, ...) {
    va_list args;
    va_start(args, fmt);
    buf_pos += vsnprintf(result_buf + buf_pos, sizeof(result_buf) - buf_pos, fmt, args);
    va_end(args);
}

static void probe_device(const char *path) {
    struct stat st;
    int fd;

    if (stat(path, &st) != 0) {
        log_result("[ABSENT] %s — does not exist\n", path);
        return;
    }

    log_result("[EXISTS] %s — mode=%o uid=%d gid=%d major=%d minor=%d\n",
               path, st.st_mode & 07777, st.st_uid, st.st_gid,
               (int)((st.st_rdev >> 8) & 0xff), (int)(st.st_rdev & 0xff));

    /* Try read-only open */
    fd = open(path, O_RDONLY | O_NONBLOCK);
    if (fd >= 0) {
        log_result("  [READ_OK] Opened read-only! fd=%d\n", fd);

        /* Try a small read */
        char buf[64];
        ssize_t n = read(fd, buf, sizeof(buf));
        if (n > 0) {
            log_result("  [DATA] Read %zd bytes:", n);
            for (int i = 0; i < n && i < 32; i++)
                log_result(" %02x", (unsigned char)buf[i]);
            log_result("\n");
        } else if (n == 0) {
            log_result("  [EOF] Read returned 0 bytes\n");
        } else {
            log_result("  [READ_ERR] read(): %s\n", strerror(errno));
        }
        close(fd);
    } else {
        log_result("  [READ_DENIED] open(O_RDONLY): %s (errno=%d)\n", strerror(errno), errno);
    }

    /* Try read-write open */
    fd = open(path, O_RDWR | O_NONBLOCK);
    if (fd >= 0) {
        log_result("  [RDWR_OK] Opened read-write! fd=%d\n", fd);
        close(fd);
    } else {
        log_result("  [RDWR_DENIED] open(O_RDWR): %s (errno=%d)\n", strerror(errno), errno);
    }

    /* Try write-only open */
    fd = open(path, O_WRONLY | O_NONBLOCK);
    if (fd >= 0) {
        log_result("  [WRITE_OK] Opened write-only! fd=%d\n", fd);
        close(fd);
    } else {
        log_result("  [WRITE_DENIED] open(O_WRONLY): %s (errno=%d)\n", strerror(errno), errno);
    }
}

static void probe_trusty_ipc(void) {
    int fd;

    log_result("\n=== TRUSTY IPC PROBE ===\n");

    fd = open("/dev/trusty-ipc-dev0", O_RDWR);
    if (fd < 0) {
        log_result("[DENIED] Cannot open /dev/trusty-ipc-dev0: %s\n", strerror(errno));

        /* Try via socket syscall as alternative */
        int sock = socket(AF_UNIX, SOCK_STREAM, 0);
        if (sock >= 0) {
            log_result("[INFO] AF_UNIX socket created (fd=%d) — not a Trusty path but testing\n", sock);
            close(sock);
        }
        return;
    }

    log_result("[ACCESS] /dev/trusty-ipc-dev0 opened! fd=%d\n", fd);

    /* Try connecting to known Trusty services */
    for (int i = 0; trusty_services[i] != NULL; i++) {
        char service_name[256];
        strncpy(service_name, trusty_services[i], sizeof(service_name) - 1);
        service_name[sizeof(service_name) - 1] = '\0';

        /* Each TIPC_IOC_CONNECT needs a fresh fd */
        int svc_fd = open("/dev/trusty-ipc-dev0", O_RDWR);
        if (svc_fd < 0) {
            log_result("  [ERR] Re-open failed for service probe: %s\n", strerror(errno));
            break;
        }

        int ret = ioctl(svc_fd, TIPC_IOC_CONNECT, service_name);
        if (ret == 0) {
            log_result("  [CONNECTED] Trusty service: %s (fd=%d)\n", trusty_services[i], svc_fd);

            /* Try reading from the connected service */
            char buf[256];
            ssize_t n = read(svc_fd, buf, sizeof(buf));
            if (n > 0) {
                log_result("    [RECV] %zd bytes from service\n", n);
            }
        } else {
            log_result("  [REFUSED] %s: %s (errno=%d)\n",
                       trusty_services[i], strerror(errno), errno);
        }
        close(svc_fd);
    }

    close(fd);
}

static void probe_ghs_ioctl(const char *path) {
    int fd = open(path, O_RDWR);
    if (fd < 0) {
        fd = open(path, O_WRONLY);
        if (fd < 0) {
            fd = open(path, O_RDONLY);
            if (fd < 0) return;
        }
    }

    log_result("  [IOCTL_PROBE] Testing ioctls on %s (fd=%d)\n", path, fd);

    /* Try common ioctl numbers */
    int val = 0;
    for (unsigned long cmd = 0; cmd <= 0x20; cmd++) {
        int ret = ioctl(fd, _IOR('g', cmd, int), &val);
        if (ret == 0) {
            log_result("    [IOCTL_OK] cmd=_IOR('g',0x%02lx,int) returned 0, val=%d\n", cmd, val);
        } else if (errno != ENOTTY && errno != EINVAL && errno != EACCES) {
            log_result("    [IOCTL_ERR] cmd=_IOR('g',0x%02lx,int) errno=%d (%s)\n",
                       cmd, errno, strerror(errno));
        }
    }

    /* Try raw ioctl numbers that might work */
    unsigned long raw_cmds[] = {0, 1, 2, 3, 0x80, 0x100, 0x4700, 0x4701, 0x4702};
    for (int i = 0; i < (int)(sizeof(raw_cmds)/sizeof(raw_cmds[0])); i++) {
        char buf[256] = {0};
        int ret = ioctl(fd, raw_cmds[i], buf);
        if (ret == 0) {
            log_result("    [RAW_IOCTL_OK] cmd=0x%lx returned 0\n", raw_cmds[i]);
        }
    }

    close(fd);
}

static void probe_proc_sysfs(void) {
    log_result("\n=== PROC/SYSFS PROBE ===\n");

    const char *paths[] = {
        "/proc/trusty/version",
        "/proc/trusty/log",
        "/sys/devices/platform/trusty/trusty-log/trusty_log",
        "/sys/class/ghs_comms/ipc/dev",
        "/sys/class/ghs_comms/cal/dev",
        "/sys/class/ghs_comms/camera/dev",
        "/sys/class/trusty_ipc/trusty-ipc-dev0/dev",
        "/sys/devices/pci0000:00/0000:00:03.0/resource",
        "/sys/devices/pci0000:00/0000:00:03.0/config",
        "/sys/devices/pci0000:00/0000:00:03.0/vendor",
        "/sys/devices/pci0000:00/0000:00:03.0/device",
        "/sys/devices/pci0000:00/0000:00:03.0/class",
        "/sys/fs/selinux/enforce",
        "/proc/version",
        "/proc/config.gz",
        NULL
    };

    for (int i = 0; paths[i] != NULL; i++) {
        int fd = open(paths[i], O_RDONLY);
        if (fd >= 0) {
            char buf[512];
            ssize_t n = read(fd, buf, sizeof(buf) - 1);
            if (n > 0) {
                buf[n] = '\0';
                /* Truncate for display */
                if (n > 128) buf[128] = '\0';
                log_result("[READABLE] %s = %s\n", paths[i], buf);
            } else {
                log_result("[EMPTY] %s — opened but no data\n", paths[i]);
            }
            close(fd);
        } else {
            log_result("[DENIED] %s: %s\n", paths[i], strerror(errno));
        }
    }
}

static void get_selinux_context(void) {
    log_result("\n=== SELINUX CONTEXT ===\n");

    int fd = open("/proc/self/attr/current", O_RDONLY);
    if (fd >= 0) {
        char ctx[256] = {0};
        read(fd, ctx, sizeof(ctx) - 1);
        log_result("Process SELinux context: %s\n", ctx);
        close(fd);
    }

    fd = open("/proc/self/status", O_RDONLY);
    if (fd >= 0) {
        char buf[2048] = {0};
        read(fd, buf, sizeof(buf) - 1);
        /* Extract UID/GID lines */
        char *line = strtok(buf, "\n");
        while (line) {
            if (strncmp(line, "Uid:", 4) == 0 || strncmp(line, "Gid:", 4) == 0 ||
                strncmp(line, "Groups:", 7) == 0 || strncmp(line, "CapEff:", 7) == 0 ||
                strncmp(line, "CapPrm:", 7) == 0 || strncmp(line, "CapBnd:", 7) == 0) {
                log_result("%s\n", line);
            }
            line = strtok(NULL, "\n");
        }
        close(fd);
    }
}

JNIEXPORT jstring JNICALL
Java_com_research_ghsprobe_GHSProber_probeAll(JNIEnv *env, jobject thiz) {
    buf_pos = 0;
    memset(result_buf, 0, sizeof(result_buf));

    log_result("========================================\n");
    log_result(" GHS INTEGRITY HYPERVISOR PROBE RESULTS\n");
    log_result("========================================\n\n");

    /* 1. SELinux context */
    get_selinux_context();

    /* 2. Probe GHS devices */
    log_result("\n=== GHS DEVICE PROBE ===\n");
    for (int i = 0; ghs_devices[i] != NULL; i++) {
        probe_device(ghs_devices[i]);
    }

    /* 3. Probe Trusty IPC */
    probe_trusty_ipc();

    /* 4. Probe other interesting devices */
    log_result("\n=== OTHER DEVICE PROBE ===\n");
    for (int i = 0; other_devices[i] != NULL; i++) {
        probe_device(other_devices[i]);
    }

    /* 5. Try GHS ioctl on any device we can open */
    log_result("\n=== GHS IOCTL PROBE ===\n");
    for (int i = 0; ghs_devices[i] != NULL; i++) {
        probe_ghs_ioctl(ghs_devices[i]);
    }

    /* 6. Proc/sysfs probe */
    probe_proc_sysfs();

    log_result("\n=== PROBE COMPLETE ===\n");

    return (*env)->NewStringUTF(env, result_buf);
}

JNIEXPORT jstring JNICALL
Java_com_research_ghsprobe_GHSProber_probeTrustyService(JNIEnv *env, jobject thiz, jstring serviceName) {
    const char *svc = (*env)->GetStringUTFChars(env, serviceName, NULL);
    buf_pos = 0;
    memset(result_buf, 0, sizeof(result_buf));

    int fd = open("/dev/trusty-ipc-dev0", O_RDWR);
    if (fd < 0) {
        log_result("[DENIED] /dev/trusty-ipc-dev0: %s (errno=%d)\n", strerror(errno), errno);
    } else {
        char name[256];
        strncpy(name, svc, sizeof(name) - 1);
        int ret = ioctl(fd, TIPC_IOC_CONNECT, name);
        if (ret == 0) {
            log_result("[CONNECTED] %s\n", svc);
            char buf[1024];
            ssize_t n = read(fd, buf, sizeof(buf));
            log_result("[READ] %zd bytes\n", n);
        } else {
            log_result("[REFUSED] %s: %s\n", svc, strerror(errno));
        }
        close(fd);
    }

    (*env)->ReleaseStringUTFChars(env, serviceName, svc);
    return (*env)->NewStringUTF(env, result_buf);
}
