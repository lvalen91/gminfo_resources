/*
 * drm_min.h - minimal self-contained DRM/KMS uapi subset (no libdrm).
 * Struct layouts and ioctl numbers match Linux 4.19 include/uapi/drm/drm.h
 * and drm_mode.h; sizes and encoded ioctl numbers are checked with
 * _Static_assert below so a layout slip fails the build, not the radio.
 */
#ifndef DRM_MIN_H
#define DRM_MIN_H

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>

/* ---- ioctl encoding (asm-generic, used by x86_64) ---- */
#define KM_IOC(dir, type, nr, size)                                   \
	(((unsigned long)(dir) << 30) | ((unsigned long)(size) << 16) | \
	 ((unsigned long)(type) << 8) | (unsigned long)(nr))
#define KM_DRM_IO(nr)       KM_IOC(0u, 'd', (nr), 0u)
#define KM_DRM_IOWR(nr, T)  KM_IOC(3u, 'd', (nr), sizeof(T))

#define DRM_DISPLAY_MODE_LEN 32

struct drm_mode_modeinfo {
	uint32_t clock;
	uint16_t hdisplay, hsync_start, hsync_end, htotal, hskew;
	uint16_t vdisplay, vsync_start, vsync_end, vtotal, vscan;
	uint32_t vrefresh;
	uint32_t flags;
	uint32_t type;
	char name[DRM_DISPLAY_MODE_LEN];
};

struct drm_mode_card_res {
	uint64_t fb_id_ptr;
	uint64_t crtc_id_ptr;
	uint64_t connector_id_ptr;
	uint64_t encoder_id_ptr;
	uint32_t count_fbs;
	uint32_t count_crtcs;
	uint32_t count_connectors;
	uint32_t count_encoders;
	uint32_t min_width, max_width;
	uint32_t min_height, max_height;
};

struct drm_mode_crtc {
	uint64_t set_connectors_ptr;
	uint32_t count_connectors;
	uint32_t crtc_id;
	uint32_t fb_id;
	uint32_t x, y;
	uint32_t gamma_size;
	uint32_t mode_valid;
	struct drm_mode_modeinfo mode;
};

struct drm_mode_get_encoder {
	uint32_t encoder_id;
	uint32_t encoder_type;
	uint32_t crtc_id;
	uint32_t possible_crtcs;
	uint32_t possible_clones;
};

struct drm_mode_get_connector {
	uint64_t encoders_ptr;
	uint64_t modes_ptr;
	uint64_t props_ptr;
	uint64_t prop_values_ptr;
	uint32_t count_modes;
	uint32_t count_props;
	uint32_t count_encoders;
	uint32_t encoder_id;
	uint32_t connector_id;
	uint32_t connector_type;
	uint32_t connector_type_id;
	uint32_t connection;
	uint32_t mm_width, mm_height;
	uint32_t subpixel;
	uint32_t pad;
};

struct drm_mode_fb_cmd {
	uint32_t fb_id;
	uint32_t width, height;
	uint32_t pitch;
	uint32_t bpp;
	uint32_t depth;
	uint32_t handle;
};

struct drm_mode_fb_cmd2 {
	uint32_t fb_id;
	uint32_t width, height;
	uint32_t pixel_format;
	uint32_t flags;
	uint32_t handles[4];
	uint32_t pitches[4];
	uint32_t offsets[4];
	uint64_t modifier[4];
};

struct drm_mode_create_dumb {
	uint32_t height;
	uint32_t width;
	uint32_t bpp;
	uint32_t flags;
	uint32_t handle;
	uint32_t pitch;
	uint64_t size;
};

struct drm_mode_map_dumb {
	uint32_t handle;
	uint32_t pad;
	uint64_t offset;
};

_Static_assert(sizeof(struct drm_mode_modeinfo) == 68, "modeinfo");
_Static_assert(sizeof(struct drm_mode_card_res) == 64, "card_res");
_Static_assert(sizeof(struct drm_mode_crtc) == 104, "crtc");
_Static_assert(sizeof(struct drm_mode_get_encoder) == 20, "get_encoder");
_Static_assert(sizeof(struct drm_mode_get_connector) == 80, "get_connector");
_Static_assert(sizeof(struct drm_mode_fb_cmd) == 28, "fb_cmd");
_Static_assert(sizeof(struct drm_mode_fb_cmd2) == 104, "fb_cmd2");
_Static_assert(sizeof(struct drm_mode_create_dumb) == 32, "create_dumb");
_Static_assert(sizeof(struct drm_mode_map_dumb) == 16, "map_dumb");

#define DRM_IOCTL_SET_MASTER          KM_DRM_IO(0x1e)
#define DRM_IOCTL_MODE_GETRESOURCES   KM_DRM_IOWR(0xA0, struct drm_mode_card_res)
#define DRM_IOCTL_MODE_GETCRTC        KM_DRM_IOWR(0xA1, struct drm_mode_crtc)
#define DRM_IOCTL_MODE_SETCRTC        KM_DRM_IOWR(0xA2, struct drm_mode_crtc)
#define DRM_IOCTL_MODE_GETENCODER     KM_DRM_IOWR(0xA6, struct drm_mode_get_encoder)
#define DRM_IOCTL_MODE_GETCONNECTOR   KM_DRM_IOWR(0xA7, struct drm_mode_get_connector)
#define DRM_IOCTL_MODE_ADDFB          KM_DRM_IOWR(0xAE, struct drm_mode_fb_cmd)
#define DRM_IOCTL_MODE_CREATE_DUMB    KM_DRM_IOWR(0xB2, struct drm_mode_create_dumb)
#define DRM_IOCTL_MODE_MAP_DUMB       KM_DRM_IOWR(0xB3, struct drm_mode_map_dumb)
#define DRM_IOCTL_MODE_ADDFB2         KM_DRM_IOWR(0xB8, struct drm_mode_fb_cmd2)

/* Known-good encoded values (as seen in strace of libdrm clients). */
_Static_assert(DRM_IOCTL_SET_MASTER == 0x641eUL, "SET_MASTER");
_Static_assert(DRM_IOCTL_MODE_GETRESOURCES == 0xC04064A0UL, "GETRESOURCES");
_Static_assert(DRM_IOCTL_MODE_GETCRTC == 0xC06864A1UL, "GETCRTC");
_Static_assert(DRM_IOCTL_MODE_SETCRTC == 0xC06864A2UL, "SETCRTC");
_Static_assert(DRM_IOCTL_MODE_GETENCODER == 0xC01464A6UL, "GETENCODER");
_Static_assert(DRM_IOCTL_MODE_GETCONNECTOR == 0xC05064A7UL, "GETCONNECTOR");
_Static_assert(DRM_IOCTL_MODE_ADDFB == 0xC01C64AEUL, "ADDFB");
_Static_assert(DRM_IOCTL_MODE_CREATE_DUMB == 0xC02064B2UL, "CREATE_DUMB");
_Static_assert(DRM_IOCTL_MODE_MAP_DUMB == 0xC01064B3UL, "MAP_DUMB");
_Static_assert(DRM_IOCTL_MODE_ADDFB2 == 0xC06864B8UL, "ADDFB2");

#define DRM_MODE_CONNECTED          1
#define DRM_MODE_DISCONNECTED       2
#define DRM_MODE_UNKNOWNCONNECTION  3
#define DRM_MODE_TYPE_PREFERRED     (1u << 3)
#define DRM_MODE_FLAG_INTERLACE     (1u << 4)
#define DRM_MODE_FLAG_DBLSCAN       (1u << 5)
/* fourcc('X','R','2','4'): [31:0] x:R:G:B 8:8:8:8 little endian */
#define DRM_FORMAT_XRGB8888         0x34325258u

/* ---- helpers ---- */

static inline int km_ioctl(int fd, unsigned long req, void *arg)
{
	int r;
	do {
		r = ioctl(fd, req, arg);
	} while (r == -1 && (errno == EINTR || errno == EAGAIN));
	return r;
}

static inline uint64_t km_ptr(const void *p) { return (uint64_t)(uintptr_t)p; }

static inline const char *km_conn_type(uint32_t t)
{
	static const char *const n[] = {
		"Unknown", "VGA", "DVI-I", "DVI-D", "DVI-A", "Composite",
		"SVIDEO", "LVDS", "Component", "DIN", "DP", "HDMI-A",
		"HDMI-B", "TV", "eDP", "Virtual", "DSI", "DPI", "Writeback",
	};
	return t < sizeof(n) / sizeof(n[0]) ? n[t] : "?";
}

static inline const char *km_enc_type(uint32_t t)
{
	static const char *const n[] = {
		"None", "DAC", "TMDS", "LVDS", "TVDAC", "Virtual", "DSI",
		"DPMST", "DPI",
	};
	return t < sizeof(n) / sizeof(n[0]) ? n[t] : "?";
}

static inline const char *km_conn_status(uint32_t c)
{
	switch (c) {
	case DRM_MODE_CONNECTED: return "connected";
	case DRM_MODE_DISCONNECTED: return "disconnected";
	case DRM_MODE_UNKNOWNCONNECTION: return "unknown";
	default: return "?";
	}
}

static inline double km_mode_hz(const struct drm_mode_modeinfo *m)
{
	if (m->clock && m->htotal && m->vtotal) {
		double r = (double)m->clock * 1000.0 /
			   ((double)m->htotal * (double)m->vtotal);
		if (m->flags & DRM_MODE_FLAG_INTERLACE) r *= 2.0;
		if (m->flags & DRM_MODE_FLAG_DBLSCAN) r /= 2.0;
		if (m->vscan > 1) r /= (double)m->vscan;
		return r;
	}
	return (double)m->vrefresh;
}

static inline int km_mode_name_len(const struct drm_mode_modeinfo *m)
{
	return (int)strnlen(m->name, DRM_DISPLAY_MODE_LEN);
}

struct km_res {
	struct drm_mode_card_res r;
	uint32_t *fbs, *crtcs, *conns, *encs;
};

static inline void km_res_free(struct km_res *k)
{
	free(k->fbs); free(k->crtcs); free(k->conns); free(k->encs);
	memset(k, 0, sizeof(*k));
}

/* Two-pass GETRESOURCES; retries if counts grew between the passes
 * (kernel copies only when the user count >= actual, and always
 * writes back the actual count). */
static inline int km_get_resources(int fd, struct km_res *out)
{
	memset(out, 0, sizeof(*out));
	for (int attempt = 0; attempt < 8; attempt++) {
		struct drm_mode_card_res q;
		memset(&q, 0, sizeof(q));
		if (km_ioctl(fd, DRM_IOCTL_MODE_GETRESOURCES, &q) == -1) {
			perror("DRM_IOCTL_MODE_GETRESOURCES (count pass)");
			return -1;
		}
		struct km_res k;
		memset(&k, 0, sizeof(k));
		k.fbs   = calloc(q.count_fbs ? q.count_fbs : 1, sizeof(uint32_t));
		k.crtcs = calloc(q.count_crtcs ? q.count_crtcs : 1, sizeof(uint32_t));
		k.conns = calloc(q.count_connectors ? q.count_connectors : 1, sizeof(uint32_t));
		k.encs  = calloc(q.count_encoders ? q.count_encoders : 1, sizeof(uint32_t));
		if (!k.fbs || !k.crtcs || !k.conns || !k.encs) {
			perror("calloc (GETRESOURCES arrays)");
			km_res_free(&k);
			return -1;
		}
		k.r = q;
		k.r.fb_id_ptr = km_ptr(k.fbs);
		k.r.crtc_id_ptr = km_ptr(k.crtcs);
		k.r.connector_id_ptr = km_ptr(k.conns);
		k.r.encoder_id_ptr = km_ptr(k.encs);
		if (km_ioctl(fd, DRM_IOCTL_MODE_GETRESOURCES, &k.r) == -1) {
			perror("DRM_IOCTL_MODE_GETRESOURCES (fill pass)");
			km_res_free(&k);
			return -1;
		}
		if (k.r.count_fbs > q.count_fbs || k.r.count_crtcs > q.count_crtcs ||
		    k.r.count_connectors > q.count_connectors ||
		    k.r.count_encoders > q.count_encoders) {
			km_res_free(&k);
			continue;
		}
		*out = k;
		return 0;
	}
	fprintf(stderr, "DRM_IOCTL_MODE_GETRESOURCES: counts kept changing, giving up\n");
	return -1;
}

struct km_conn {
	struct drm_mode_get_connector c;
	uint32_t *encs;
	struct drm_mode_modeinfo *modes;
};

static inline void km_conn_free(struct km_conn *k)
{
	free(k->encs); free(k->modes);
	memset(k, 0, sizeof(*k));
}

/* Two-pass GETCONNECTOR. Pass 1 has count_modes == 0, which makes the
 * kernel (re)probe the connector (fill_modes). count_props is forced to 0
 * on pass 2: the kernel writes props whenever count_props > 0, and with a
 * NULL props_ptr that would be -EFAULT. */
static inline int km_get_connector(int fd, uint32_t id, struct km_conn *out)
{
	memset(out, 0, sizeof(*out));
	for (int attempt = 0; attempt < 8; attempt++) {
		struct drm_mode_get_connector q;
		memset(&q, 0, sizeof(q));
		q.connector_id = id;
		if (km_ioctl(fd, DRM_IOCTL_MODE_GETCONNECTOR, &q) == -1) {
			fprintf(stderr, "DRM_IOCTL_MODE_GETCONNECTOR (count pass, id %u): %s\n",
				id, strerror(errno));
			return -1;
		}
		struct km_conn k;
		memset(&k, 0, sizeof(k));
		k.encs = calloc(q.count_encoders ? q.count_encoders : 1, sizeof(uint32_t));
		k.modes = calloc(q.count_modes ? q.count_modes : 1,
				 sizeof(struct drm_mode_modeinfo));
		if (!k.encs || !k.modes) {
			perror("calloc (GETCONNECTOR arrays)");
			km_conn_free(&k);
			return -1;
		}
		memset(&k.c, 0, sizeof(k.c));
		k.c.connector_id = id;
		k.c.count_encoders = q.count_encoders;
		k.c.encoders_ptr = km_ptr(k.encs);
		k.c.count_modes = q.count_modes;
		k.c.modes_ptr = km_ptr(k.modes);
		k.c.count_props = 0;
		if (km_ioctl(fd, DRM_IOCTL_MODE_GETCONNECTOR, &k.c) == -1) {
			fprintf(stderr, "DRM_IOCTL_MODE_GETCONNECTOR (fill pass, id %u): %s\n",
				id, strerror(errno));
			km_conn_free(&k);
			return -1;
		}
		if (k.c.count_encoders > q.count_encoders ||
		    k.c.count_modes > q.count_modes) {
			km_conn_free(&k);
			continue;
		}
		*out = k;
		return 0;
	}
	fprintf(stderr, "DRM_IOCTL_MODE_GETCONNECTOR (id %u): counts kept changing, giving up\n", id);
	return -1;
}

static inline int km_get_encoder(int fd, uint32_t id, struct drm_mode_get_encoder *e)
{
	memset(e, 0, sizeof(*e));
	e->encoder_id = id;
	if (km_ioctl(fd, DRM_IOCTL_MODE_GETENCODER, e) == -1) {
		fprintf(stderr, "DRM_IOCTL_MODE_GETENCODER (id %u): %s\n", id, strerror(errno));
		return -1;
	}
	return 0;
}

static inline int km_get_crtc(int fd, uint32_t id, struct drm_mode_crtc *c)
{
	memset(c, 0, sizeof(*c));
	c->crtc_id = id;
	if (km_ioctl(fd, DRM_IOCTL_MODE_GETCRTC, c) == -1) {
		fprintf(stderr, "DRM_IOCTL_MODE_GETCRTC (id %u): %s\n", id, strerror(errno));
		return -1;
	}
	return 0;
}

/* First CRTC id whose bit is set in mask (bit i == res.crtcs[i]), or 0. */
static inline uint32_t km_crtc_from_mask(const struct km_res *res, uint32_t mask)
{
	for (uint32_t i = 0; i < res->r.count_crtcs && i < 32; i++)
		if (mask & (1u << i))
			return res->crtcs[i];
	return 0;
}

/* Step 4: CRTC for a connector. Current encoder's CRTC if bound, else the
 * first CRTC allowed by the current encoder, else by any of the connector's
 * encoders. Returns 0 (no CRTC) on failure; *how says which rule matched. */
static inline uint32_t km_pick_crtc(int fd, const struct km_res *res,
				    const struct km_conn *k, const char **how)
{
	struct drm_mode_get_encoder e;
	*how = "none";
	if (k->c.encoder_id && km_get_encoder(fd, k->c.encoder_id, &e) == 0) {
		if (e.crtc_id) {
			*how = "current encoder->crtc";
			return e.crtc_id;
		}
		uint32_t c = km_crtc_from_mask(res, e.possible_crtcs);
		if (c) {
			*how = "current encoder possible_crtcs";
			return c;
		}
	}
	for (uint32_t i = 0; i < k->c.count_encoders; i++) {
		if (km_get_encoder(fd, k->encs[i], &e) != 0)
			continue;
		uint32_t c = km_crtc_from_mask(res, e.possible_crtcs);
		if (c) {
			*how = "connector encoders possible_crtcs";
			return c;
		}
	}
	return 0;
}

#endif /* DRM_MIN_H */
