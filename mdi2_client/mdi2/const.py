"""Established MDI2 protocol constants (from the RE in
gminfo_resources/research/MDI2_MANAGER_IDENT_LOG_PULL_AUG2026.md)."""

# --- network ---
DEVICE_IP_DEFAULT = "192.168.171.2"      # MDI2 on the direct link
DISCOVERY_GROUP   = "225.1.1.1"          # device announce multicast
DISCOVERY_PORT    = 8194                 # ~1 Hz, 106-byte beacon from device:42178

# 14-socket "900x" service bank opened per Connect (fresh bank each connect)
SERVICE_PORTS = [9001, 9003, 9006, 9007, 9008, 9009, 9010,
                 9011, 9012, 9013, 9014, 9050, 9051, 9052]
LOG_PORT = 9052                          # "Get Log Files" channel

# other device services (not used by the Manager's 900x path)
FTPS_PORT = 21                           # vsftpd, AUTH TLS, creds firmware:vtx (alt log path)
HTTP_PORT = 80
DPDU_PORT = 10123                        # DPS/SPS D-PDU-API diagnostic tunnel (separate stack)
DOIP_PORT = 13400                        # ISO-13400 DoIP (separate stack)

# --- framing (big-endian; NB: the 10123 D-PDU path is little-endian) ---
# on-wire message: [u32be 0x00000000][u32be payload_len][u32 counter (cleartext)][Blowfish-ECB body]
CONTROL_FRAME_MAGIC = b"\x00\x53\x50\x00"   # 8-byte plaintext control frame 00 53 50 00 00 XX 00 00

# --- module types (bvtx_vci_rt.dll table DAT_10309d60) ---
MODULE_TYPE_ID_MDI_2 = 0x1c
