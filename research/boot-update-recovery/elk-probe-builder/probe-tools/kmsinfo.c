/*
 * kmsinfo - dump DRM/KMS topology of /dev/dri/card0 (no libdrm).
 * Steps: open, GETRESOURCES, GETCONNECTOR per connector, GETENCODER,
 * plus GETCRTC for each CRTC's current state. Changes no KMS state
 * (note: GETCONNECTOR's count pass makes the kernel re-probe connectors).
 */
#include <fcntl.h>
#include <unistd.h>

#include "drm_min.h"

static void print_mode(const struct drm_mode_modeinfo *m, const char *indent)
{
	printf("%s\"%.*s\" %ux%u@%.2f (clock %u kHz, vrefresh %u, type 0x%x%s, flags 0x%x)\n",
	       indent, km_mode_name_len(m), m->name, m->hdisplay, m->vdisplay,
	       km_mode_hz(m), m->clock, m->vrefresh, m->type,
	       (m->type & DRM_MODE_TYPE_PREFERRED) ? " preferred" : "", m->flags);
}

static void print_mask(const struct km_res *res, uint32_t mask)
{
	int any = 0;
	printf("[");
	for (uint32_t i = 0; i < res->r.count_crtcs && i < 32; i++)
		if (mask & (1u << i)) {
			printf("%s%u", any ? " " : "", res->crtcs[i]);
			any = 1;
		}
	printf("]");
}

int main(int argc, char **argv)
{
	(void)argv;
	if (argc != 1) {
		fprintf(stderr, "usage: kmsinfo   (no arguments)\n");
		return 2;
	}

	int fd = open("/dev/dri/card0", O_RDWR | O_CLOEXEC);
	if (fd == -1) {
		perror("open /dev/dri/card0");
		return 1;
	}

	struct km_res res;
	if (km_get_resources(fd, &res) != 0)
		return 1;

	printf("card0: %u fbs(own), %u crtcs, %u connectors, %u encoders; fb size %ux%u .. %ux%u\n",
	       res.r.count_fbs, res.r.count_crtcs, res.r.count_connectors,
	       res.r.count_encoders, res.r.min_width, res.r.min_height,
	       res.r.max_width, res.r.max_height);

	int rc = 0;

	printf("\nCRTCs:\n");
	for (uint32_t i = 0; i < res.r.count_crtcs; i++) {
		struct drm_mode_crtc c;
		if (km_get_crtc(fd, res.crtcs[i], &c) != 0) {
			rc = 1;
			continue;
		}
		printf("  crtc %u (index %u): fb %u pos %u,%u gamma_size %u %s\n",
		       c.crtc_id, i, c.fb_id, c.x, c.y, c.gamma_size,
		       c.mode_valid ? "active:" : "inactive");
		if (c.mode_valid)
			print_mode(&c.mode, "    ");
	}

	printf("\nEncoders:\n");
	for (uint32_t i = 0; i < res.r.count_encoders; i++) {
		struct drm_mode_get_encoder e;
		if (km_get_encoder(fd, res.encs[i], &e) != 0) {
			rc = 1;
			continue;
		}
		printf("  encoder %u: type %s(%u) crtc %u possible_crtcs 0x%x ",
		       e.encoder_id, km_enc_type(e.encoder_type), e.encoder_type,
		       e.crtc_id, e.possible_crtcs);
		print_mask(&res, e.possible_crtcs);
		printf(" possible_clones 0x%x\n", e.possible_clones);
	}

	printf("\nConnectors:\n");
	for (uint32_t i = 0; i < res.r.count_connectors; i++) {
		struct km_conn k;
		if (km_get_connector(fd, res.conns[i], &k) != 0) {
			rc = 1;
			continue;
		}
		printf("  connector %u: %s-%u %s (%u) %ux%u mm, encoder %u, encoders [",
		       k.c.connector_id, km_conn_type(k.c.connector_type),
		       k.c.connector_type_id, km_conn_status(k.c.connection),
		       k.c.connection, k.c.mm_width, k.c.mm_height, k.c.encoder_id);
		for (uint32_t j = 0; j < k.c.count_encoders; j++)
			printf("%s%u", j ? " " : "", k.encs[j]);
		printf("], %u modes\n", k.c.count_modes);

		const char *how;
		uint32_t crtc = km_pick_crtc(fd, &res, &k, &how);
		if (crtc)
			printf("    crtc for kmsshow: %u (%s)\n", crtc, how);
		else
			printf("    crtc for kmsshow: none found\n");

		for (uint32_t j = 0; j < k.c.count_modes; j++)
			print_mode(&k.modes[j], "    ");
		km_conn_free(&k);
	}

	km_res_free(&res);
	if (close(fd) == -1) {
		perror("close /dev/dri/card0");
		rc = 1;
	}
	if (fflush(stdout) != 0) {
		perror("fflush stdout");
		rc = 1;
	}
	return rc;
}
