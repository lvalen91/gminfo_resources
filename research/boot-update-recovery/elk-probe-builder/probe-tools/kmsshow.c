/*
 * kmsshow <bgra_raw_file> <width> <height>
 *
 * Scan out a raw BGRA8888 image on /dev/dri/card0 via legacy KMS SETCRTC
 * using a dumb buffer (no libdrm, no fbdev).
 *
 * Holds after the modeset: on Linux 4.19, closing the DRM fd (process exit)
 * runs drm_fb_release() -> drm_framebuffer_remove() on every fb this file
 * created; an fb still on a CRTC gets that CRTC disabled (legacy_remove_fb /
 * atomic_remove_fb). So the image only stays up while this process lives.
 * On SIGINT/SIGTERM/SIGHUP/SIGQUIT it restores the CRTC's previous fb+mode
 * (if it had one) and exits.
 */
#include <fcntl.h>
#include <limits.h>
#include <signal.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

#include "drm_min.h"

static int parse_dim(const char *s, const char *what, uint32_t *out)
{
	char *end;
	errno = 0;
	unsigned long v = strtoul(s, &end, 10);
	if (errno || end == s || *end != '\0' || v == 0 || v > 16384) {
		fprintf(stderr, "kmsshow: bad %s '%s' (1..16384)\n", what, s);
		return -1;
	}
	*out = (uint32_t)v;
	return 0;
}

/* Read exactly `need` bytes, and require EOF right after. */
static unsigned char *read_image(const char *path, size_t need)
{
	int fd = open(path, O_RDONLY | O_CLOEXEC);
	if (fd == -1) {
		fprintf(stderr, "open %s: %s\n", path, strerror(errno));
		return NULL;
	}
	struct stat st;
	if (fstat(fd, &st) == -1) {
		fprintf(stderr, "fstat %s: %s\n", path, strerror(errno));
		close(fd);
		return NULL;
	}
	if (S_ISREG(st.st_mode) && (unsigned long long)st.st_size != (unsigned long long)need) {
		fprintf(stderr, "kmsshow: %s is %lld bytes, expected exactly %zu (width*height*4)\n",
			path, (long long)st.st_size, need);
		close(fd);
		return NULL;
	}
	unsigned char *buf = malloc(need);
	if (!buf) {
		perror("malloc image buffer");
		close(fd);
		return NULL;
	}
	size_t got = 0;
	while (got < need) {
		ssize_t n = read(fd, buf + got, need - got);
		if (n == -1) {
			if (errno == EINTR)
				continue;
			fprintf(stderr, "read %s: %s\n", path, strerror(errno));
			goto fail;
		}
		if (n == 0) {
			fprintf(stderr, "kmsshow: %s: short read, got %zu of %zu bytes\n",
				path, got, need);
			goto fail;
		}
		got += (size_t)n;
	}
	unsigned char extra;
	ssize_t n;
	do {
		n = read(fd, &extra, 1);
	} while (n == -1 && errno == EINTR);
	if (n == -1) {
		fprintf(stderr, "read %s (EOF check): %s\n", path, strerror(errno));
		goto fail;
	}
	if (n > 0) {
		fprintf(stderr, "kmsshow: %s is larger than %zu bytes (width*height*4)\n",
			path, need);
		goto fail;
	}
	close(fd);
	return buf;
fail:
	free(buf);
	close(fd);
	return NULL;
}

/* Index of the mode matching w x h (preferred-flagged first), or -1. */
static int find_mode(const struct km_conn *k, uint32_t w, uint32_t h)
{
	int first = -1;
	for (uint32_t i = 0; i < k->c.count_modes; i++) {
		const struct drm_mode_modeinfo *m = &k->modes[i];
		if (m->hdisplay != w || m->vdisplay != h)
			continue;
		if (m->type & DRM_MODE_TYPE_PREFERRED)
			return (int)i;
		if (first < 0)
			first = (int)i;
	}
	return first;
}

static int preferred_mode(const struct km_conn *k)
{
	for (uint32_t i = 0; i < k->c.count_modes; i++)
		if (k->modes[i].type & DRM_MODE_TYPE_PREFERRED)
			return (int)i;
	return 0;
}

int main(int argc, char **argv)
{
	if (argc != 4) {
		fprintf(stderr, "usage: kmsshow <bgra_raw_file> <width> <height>\n");
		return 2;
	}
	uint32_t w, h;
	if (parse_dim(argv[2], "width", &w) || parse_dim(argv[3], "height", &h))
		return 2;
	const size_t row = (size_t)w * 4u;
	const size_t need = row * (size_t)h;

	/* A dead stdout pipe (e.g. adb shell gone) must not kill us before
	 * the restore path runs. */
	if (signal(SIGPIPE, SIG_IGN) == SIG_ERR) {
		perror("signal SIGPIPE");
		return 1;
	}

	/* Validate input before touching KMS at all. */
	unsigned char *img = read_image(argv[1], need);
	if (!img)
		return 1;

	/* 1. open */
	int fd = open("/dev/dri/card0", O_RDWR | O_CLOEXEC);
	if (fd == -1) {
		perror("open /dev/dri/card0");
		return 1;
	}
	/* SETCRTC requires DRM master. The first opener gets it implicitly;
	 * SET_MASTER is root-only and fails EINVAL if another fd holds it. */
	if (km_ioctl(fd, DRM_IOCTL_SET_MASTER, NULL) == -1)
		fprintf(stderr, "warning: DRM_IOCTL_SET_MASTER: %s (continuing; SETCRTC "
			"will fail EACCES if another process holds DRM master)\n",
			strerror(errno));

	/* 2. resources */
	struct km_res res;
	if (km_get_resources(fd, &res) != 0)
		return 1;
	if (res.r.count_connectors == 0 || res.r.count_crtcs == 0) {
		fprintf(stderr, "kmsshow: card0 reports %u connectors, %u crtcs\n",
			res.r.count_connectors, res.r.count_crtcs);
		return 1;
	}
	if ((res.r.max_width && w > res.r.max_width) ||
	    (res.r.max_height && h > res.r.max_height) ||
	    w < res.r.min_width || h < res.r.min_height) {
		fprintf(stderr, "kmsshow: %ux%u outside card fb limits %ux%u..%ux%u\n",
			w, h, res.r.min_width, res.r.min_height,
			res.r.max_width, res.r.max_height);
		return 1;
	}

	/* 3. connectors */
	struct km_conn *conns = calloc(res.r.count_connectors, sizeof(*conns));
	if (!conns) {
		perror("calloc connectors");
		return 1;
	}
	int ci = -1, mi = -1, matched = 0;
	for (uint32_t i = 0; i < res.r.count_connectors; i++) {
		if (km_get_connector(fd, res.conns[i], &conns[i]) != 0)
			return 1;
		const struct km_conn *k = &conns[i];
		if (k->c.connection != DRM_MODE_CONNECTED || k->c.count_modes == 0)
			continue;
		int m = find_mode(k, w, h);
		if (m >= 0 && !matched) {
			ci = (int)i;
			mi = m;
			matched = 1;
		} else if (ci < 0) {
			ci = (int)i;
			mi = preferred_mode(k);
		}
	}
	if (ci < 0) {
		fprintf(stderr, "kmsshow: no connector with connection==connected and >=1 mode "
			"(run kmsinfo)\n");
		return 1;
	}
	const struct km_conn *conn = &conns[ci];
	struct drm_mode_modeinfo mode = conn->modes[mi];
	uint32_t conn_id = conn->c.connector_id;

	if (mode.hdisplay > w || mode.vdisplay > h) {
		fprintf(stderr, "kmsshow: connector %u has no %ux%u mode; chosen mode \"%.*s\" "
			"%ux%u is larger than the %ux%u fb (SETCRTC would fail ENOSPC)\n",
			conn_id, w, h, km_mode_name_len(&mode), mode.name,
			mode.hdisplay, mode.vdisplay, w, h);
		return 1;
	}

	/* 4. encoder -> crtc */
	const char *how;
	uint32_t crtc_id = km_pick_crtc(fd, &res, conn, &how);
	if (!crtc_id) {
		fprintf(stderr, "kmsshow: no usable CRTC for connector %u\n", conn_id);
		return 1;
	}

	/* Save the CRTC's current state and the connectors routed to it, for
	 * restore on signal. */
	struct drm_mode_crtc saved;
	if (km_get_crtc(fd, crtc_id, &saved) != 0)
		return 1;
	uint32_t *old_conns = calloc(res.r.count_connectors, sizeof(uint32_t));
	if (!old_conns) {
		perror("calloc old_conns");
		return 1;
	}
	uint32_t n_old = 0;
	int old_known = 1;
	for (uint32_t i = 0; i < res.r.count_connectors; i++) {
		struct drm_mode_get_encoder e;
		if (!conns[i].c.encoder_id)
			continue;
		if (km_get_encoder(fd, conns[i].c.encoder_id, &e) != 0) {
			old_known = 0;
			continue;
		}
		if (e.crtc_id == crtc_id)
			old_conns[n_old++] = conns[i].c.connector_id;
	}

	/* 5. dumb buffer */
	struct drm_mode_create_dumb cd;
	memset(&cd, 0, sizeof(cd));
	cd.width = w;
	cd.height = h;
	cd.bpp = 32;
	if (km_ioctl(fd, DRM_IOCTL_MODE_CREATE_DUMB, &cd) == -1) {
		perror("DRM_IOCTL_MODE_CREATE_DUMB");
		return 1;
	}
	if (cd.pitch < row || cd.size < (uint64_t)cd.pitch * h || cd.size > SIZE_MAX) {
		fprintf(stderr, "kmsshow: CREATE_DUMB returned pitch %u size %llu, too small for %ux%u\n",
			cd.pitch, (unsigned long long)cd.size, w, h);
		return 1;
	}

	/* 6. map */
	struct drm_mode_map_dumb md;
	memset(&md, 0, sizeof(md));
	md.handle = cd.handle;
	if (km_ioctl(fd, DRM_IOCTL_MODE_MAP_DUMB, &md) == -1) {
		perror("DRM_IOCTL_MODE_MAP_DUMB");
		return 1;
	}
	if (md.offset > (uint64_t)LLONG_MAX) {
		fprintf(stderr, "kmsshow: MAP_DUMB offset 0x%llx out of off_t range\n",
			(unsigned long long)md.offset);
		return 1;
	}
	unsigned char *map = mmap(NULL, (size_t)cd.size, PROT_READ | PROT_WRITE,
				  MAP_SHARED, fd, (off_t)md.offset);
	if (map == MAP_FAILED) {
		perror("mmap dumb buffer");
		return 1;
	}

	/* 7. copy row by row honouring pitch; zero any pitch padding */
	for (uint32_t y = 0; y < h; y++) {
		unsigned char *dst = map + (size_t)y * cd.pitch;
		memcpy(dst, img + (size_t)y * row, row);
		if (cd.pitch > row)
			memset(dst + row, 0, cd.pitch - row);
	}
	if (munmap(map, (size_t)cd.size) == -1) {
		perror("munmap dumb buffer");
		return 1;
	}
	free(img);

	/* 8. framebuffer: ADDFB2 XRGB8888, fall back to legacy ADDFB 32/24
	 * (which the kernel maps to the same XRGB8888 format). */
	uint32_t fb_id = 0;
	const char *fb_via = "ADDFB2 XRGB8888";
	struct drm_mode_fb_cmd2 f2;
	memset(&f2, 0, sizeof(f2));
	f2.width = w;
	f2.height = h;
	f2.pixel_format = DRM_FORMAT_XRGB8888;
	f2.handles[0] = cd.handle;
	f2.pitches[0] = cd.pitch;
	f2.offsets[0] = 0;
	if (km_ioctl(fd, DRM_IOCTL_MODE_ADDFB2, &f2) == 0) {
		fb_id = f2.fb_id;
	} else {
		perror("DRM_IOCTL_MODE_ADDFB2 (falling back to ADDFB)");
		struct drm_mode_fb_cmd f1;
		memset(&f1, 0, sizeof(f1));
		f1.width = w;
		f1.height = h;
		f1.pitch = cd.pitch;
		f1.bpp = 32;
		f1.depth = 24;
		f1.handle = cd.handle;
		if (km_ioctl(fd, DRM_IOCTL_MODE_ADDFB, &f1) == -1) {
			perror("DRM_IOCTL_MODE_ADDFB");
			return 1;
		}
		fb_id = f1.fb_id;
		fb_via = "ADDFB bpp32/depth24";
	}

	/* Block termination signals before the modeset so one arriving between
	 * SETCRTC and sigwait is queued, not fatal (fatal == CRTC disabled
	 * without restore). */
	sigset_t sigs;
	sigemptyset(&sigs);
	sigaddset(&sigs, SIGINT);
	sigaddset(&sigs, SIGTERM);
	sigaddset(&sigs, SIGHUP);
	sigaddset(&sigs, SIGQUIT);
	if (sigprocmask(SIG_BLOCK, &sigs, NULL) == -1) {
		perror("sigprocmask");
		return 1;
	}

	/* 9. modeset */
	struct drm_mode_crtc sc;
	memset(&sc, 0, sizeof(sc));
	sc.crtc_id = crtc_id;
	sc.fb_id = fb_id;
	sc.x = 0;
	sc.y = 0;
	sc.set_connectors_ptr = km_ptr(&conn_id);
	sc.count_connectors = 1;
	sc.mode_valid = 1;
	sc.mode = mode;
	if (km_ioctl(fd, DRM_IOCTL_MODE_SETCRTC, &sc) == -1) {
		perror("DRM_IOCTL_MODE_SETCRTC");
		return 1;
	}

	/* 10. report */
	printf("connector %u (%s-%u), crtc %u (%s), fb %u (%s, dumb handle %u pitch %u), "
	       "mode \"%.*s\" %ux%u@%.2f, image %ux%u%s\n",
	       conn_id, km_conn_type(conn->c.connector_type), conn->c.connector_type_id,
	       crtc_id, how, fb_id, fb_via, cd.handle, cd.pitch,
	       km_mode_name_len(&mode), mode.name, mode.hdisplay, mode.vdisplay,
	       km_mode_hz(&mode), w, h,
	       matched ? "" : " (no exact-size mode; image cropped to mode at 0,0)");
	if (saved.mode_valid && saved.fb_id)
		printf("previous: fb %u mode \"%.*s\" %ux%u on %u connector(s)\n",
		       saved.fb_id, km_mode_name_len(&saved.mode), saved.mode.name,
		       saved.mode.hdisplay, saved.mode.vdisplay, n_old);
	else
		printf("previous: crtc %u was inactive\n", crtc_id);
	printf("holding (pid %d): image stays up while this process lives; "
	       "SIGINT/SIGTERM/SIGHUP restores previous state and exits\n", (int)getpid());
	if (fflush(stdout) != 0)
		perror("fflush stdout (continuing to hold)");

	int sig = 0;
	int e = sigwait(&sigs, &sig);
	if (e != 0) {
		fprintf(stderr, "sigwait: %s\n", strerror(e));
		return 1;
	}

	if (saved.mode_valid && saved.fb_id && n_old > 0 && old_known) {
		struct drm_mode_crtc rs = saved;
		rs.set_connectors_ptr = km_ptr(old_conns);
		rs.count_connectors = n_old;
		if (km_ioctl(fd, DRM_IOCTL_MODE_SETCRTC, &rs) == -1) {
			fprintf(stderr, "DRM_IOCTL_MODE_SETCRTC (restore fb %u on crtc %u): %s; "
				"crtc will be disabled on exit\n",
				saved.fb_id, crtc_id, strerror(errno));
			return 1;
		}
		printf("signal %d: restored fb %u on crtc %u\n", sig, saved.fb_id, crtc_id);
	} else if (saved.mode_valid && saved.fb_id) {
		fprintf(stderr, "signal %d: previous connector routing for crtc %u unknown; "
			"not restoring, crtc will be disabled on exit\n", sig, crtc_id);
		return 1;
	} else {
		printf("signal %d: crtc %u was inactive before; exiting disables it\n",
		       sig, crtc_id);
	}
	if (fflush(stdout) != 0)
		perror("fflush stdout");
	return 0;
}
