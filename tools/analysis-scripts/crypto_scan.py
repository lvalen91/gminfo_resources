#!/usr/bin/env python3
"""Comprehensive crypto-artifact scanner."""
import os, sys, re, json, struct, hashlib, binascii
from pathlib import Path

try:
    from cryptography.hazmat.primitives.serialization import load_der_public_key, load_der_private_key
    from cryptography.hazmat.backends import default_backend
    from cryptography import x509
    HAVE_CRYPTO = True
except Exception as e:
    HAVE_CRYPTO = False
    print("WARN no cryptography:", e, file=sys.stderr)

KNOWN_HARMAN = bytes.fromhex("a178eb3e")  # known modulus prefix
KNOWN_GMCSM  = bytes.fromhex("b3a5b7")    # known modulus prefix

# Roots to scan
TMP_FILES = [
    "/tmp/elk.bin", "/tmp/ghs_integrity.elf", "/tmp/vip_app.bin",
    "/tmp/vip_boot.bin", "/tmp/oem.key", "/tmp/rot.key", "/tmp/ibbp.man",
]
TMP_DIRS = ["/tmp/dps_real", "/tmp/dps_cab"]
GM_ROOT = "/Users/zeno/Downloads/misc/GM_research/gm_aaos/2024_Silverado_ICE"

# Path filter: include security/key directories; exclude bulky non-crypto.
INCLUDE_EXT = {".pem", ".cer", ".crt", ".der", ".key", ".pub", ".pfx", ".p12",
               ".p7b", ".p7s", ".p7m", ".jks", ".bks", ".keystore", ".sig",
               ".sign", ".mf", ".sf", ".rsa", ".dsa", ".ec",
               ".man", ".mft", ".manifest", ".cab", ".bin", ".img", ".efi",
               ".fv", ".rom", ".fd", ".bios", ".cap", ".elf"}
EXCLUDE_EXT = {".dex", ".odex", ".vdex", ".art", ".apk", ".jar",
               ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ttf", ".otf",
               ".mp3", ".mp4", ".wav", ".ogg", ".woff", ".woff2",
               ".xml", ".json", ".html", ".css", ".js", ".md", ".txt",
               ".log", ".smali", ".java", ".kt", ".cpp", ".c", ".h",
               ".so"}  # libs scanned separately if path matches keyword
KEY_PATH_TOKENS = ("cert", "key", "secur", "crypt", "trust", "pki", "tls", "ssl",
                   "verity", "avb", "vbmeta", "boot", "ifwi", "bios", "csme",
                   "manifest", "signat", "rsa", "ecdsa", "vendor/etc", "system/etc")

MAX_FILE = 80 * 1024 * 1024  # 80MB cap per file

findings = []

def add(f): findings.append(f)

PEM_RE = re.compile(rb"-----BEGIN ([A-Z0-9 ]+)-----[\s\S]{20,200000}?-----END \1-----")
SSH_RE = re.compile(rb"(ssh-rsa|ssh-ed25519|ecdsa-sha2-nistp(?:256|384|521)|ssh-dss)\s+[A-Za-z0-9+/=]{60,}")

# Crypto constants
CONSTS = {
    "SHA1_IV":          bytes.fromhex("67452301efcdab8998badcfe10325476c3d2e1f0"),
    "SHA256_IV":        bytes.fromhex("6a09e667bb67ae853c6ef372a54ff53a510e527f9b05688c1f83d9ab5be0cd19"),
    "SHA512_IV":        bytes.fromhex("6a09e667f3bcc908bb67ae8584caa73b3c6ef372fe94f82ba54ff53a5f1d36f1"),
    "AES_SBOX":         bytes.fromhex("637c777bf26b6fc53001672bfed7ab76"),
    "AES_INV_SBOX":     bytes.fromhex("52096ad53036a538bf40a39e81f3d7fb"),
    "ChaCha20":         b"expand 32-byte k",
    "Salsa20_16":       b"expand 16-byte k",
    "Curve25519_base":  b"\x09" + b"\x00"*31,
    "secp256r1_Gx":     bytes.fromhex("6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296"),
    "secp256k1_Gx":     bytes.fromhex("79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798"),
    "Ed25519_basepoint":bytes.fromhex("5866666666666666666666666666666666666666666666666666666666666666"),
    "RSA_F4_BE":        bytes.fromhex("00010001"),
}

def shannon(b):
    if not b: return 0
    from collections import Counter
    import math
    c = Counter(b); n = len(b)
    return -sum((v/n)*math.log2(v/n) for v in c.values())

def try_decode_der(data, off, length):
    if not HAVE_CRYPTO: return None
    blob = data[off:off+length]
    # Attempt cert
    try:
        c = x509.load_der_x509_certificate(blob, default_backend())
        try: subj = c.subject.rfc4514_string()
        except: subj = "?"
        try: iss = c.issuer.rfc4514_string()
        except: iss = "?"
        try: pk = c.public_key(); kt = type(pk).__name__
        except: kt = "?"
        return {"type":"X509","subject":subj,"issuer":iss,"key":kt,
                "serial":hex(c.serial_number),"sha1":hashlib.sha1(blob).hexdigest()}
    except Exception: pass
    # Public key
    try:
        pk = load_der_public_key(blob, default_backend())
        kt = type(pk).__name__
        bits = getattr(pk,"key_size",None)
        return {"type":"PubKey","alg":kt,"bits":bits,"sha1":hashlib.sha1(blob).hexdigest()}
    except Exception: pass
    # Private key
    try:
        pk = load_der_private_key(blob, None, default_backend())
        return {"type":"PrivKey","alg":type(pk).__name__,
                "bits":getattr(pk,"key_size",None),"sha1":hashlib.sha1(blob).hexdigest()}
    except Exception: pass
    return None

def scan_der(path, data):
    """Scan for DER SEQUENCE markers and try to decode."""
    n = len(data); i = 0
    seen = set()
    while i < n - 6:
        # locate next 30 8?
        j = data.find(b"\x30\x82", i)
        k = data.find(b"\x30\x81", i)
        if j == -1 and k == -1: break
        if j == -1: cur = k; mode = 1
        elif k == -1: cur = j; mode = 2
        else:
            if j < k: cur, mode = j, 2
            else:     cur, mode = k, 1
        i = cur + 1
        try:
            if mode == 2:
                ln = struct.unpack(">H", data[cur+2:cur+4])[0]
                hdr = 4
            else:
                ln = data[cur+2]
                hdr = 3
        except Exception: continue
        if ln < 32: continue  # too small to be cert/key
        if cur + hdr + ln > n: continue
        if ln > 16384: continue
        sig = (cur, ln)
        if sig in seen: continue
        seen.add(sig)
        res = try_decode_der(data, cur, hdr+ln)
        if res:
            res["file"] = path; res["offset"] = cur; res["length"] = hdr+ln
            add(res)

def scan_pem(path, data):
    for m in PEM_RE.finditer(data):
        kind = m.group(1).decode(errors="replace")
        blob = m.group(0)
        try:
            import base64
            inner = re.search(rb"-----BEGIN[^-]+-----([\s\S]+?)-----END",blob).group(1)
            der = base64.b64decode(re.sub(rb"\s+",b"",inner), validate=False)
            res = try_decode_der(der,0,len(der)) or {}
        except Exception: res = {}
        res.update({"type":"PEM","kind":kind,"file":path,"offset":m.start(),
                    "length":len(blob),"sha1":hashlib.sha1(blob).hexdigest()})
        add(res)

def scan_ssh(path, data):
    for m in SSH_RE.finditer(data):
        add({"type":"SSH","kind":m.group(1).decode(),
             "file":path,"offset":m.start(),
             "preview":m.group(0)[:120].decode(errors="replace")})
    if b"BEGIN OPENSSH PRIVATE KEY" in data:
        add({"type":"SSH-PRIV","file":path,
             "offset":data.find(b"BEGIN OPENSSH PRIVATE KEY")})

def scan_pkcs7(path, data):
    # OID 1.2.840.113549.1.7.2 = signedData
    pat = bytes.fromhex("2A864886F70D010702")  # OID encoding
    i = 0
    while True:
        i = data.find(pat, i)
        if i < 0: break
        add({"type":"PKCS7-OID","oid":"1.2.840.113549.1.7.2 signedData",
             "file":path,"offset":i})
        i += 1

def scan_avb(path, data):
    """AVB pubkey: 4B BE bits + 4B n0inv + modulus + rr."""
    for bits, marker in [(2048, b"\x00\x00\x00\x40"), (4096, b"\x00\x00\x00\x80")]:
        # AVB stores num_words (bits/64) BE, e.g., 2048 -> 0x40
        i = 0
        while True:
            i = data.find(marker, i)
            if i < 0: break
            modlen = bits // 8
            if i + 8 + 2*modlen <= len(data):
                blob = data[i+8:i+8+modlen]
                if shannon(blob) > 7.0:
                    add({"type":"AVB-pubkey-candidate","bits":bits,
                         "file":path,"offset":i,
                         "mod_prefix":blob[:16].hex(),
                         "sha1":hashlib.sha1(blob).hexdigest()})
            i += 4

def scan_intel_cse(path, data):
    """Intel CSE: ?? ?? ?? ?? 00 01 00 01 followed by 256B modulus."""
    pat = bytes.fromhex("0001000100")  # F4 exponent BE then start of mod
    # Better: search for 00 01 00 01 with high-entropy 256B before/after
    i = 0
    while True:
        i = data.find(b"\x00\x01\x00\x01", i)
        if i < 0: break
        # try modulus AFTER (256B)
        if i + 4 + 256 <= len(data):
            mod = data[i+4:i+4+256]
            if shannon(mod) > 7.3:
                add({"type":"RSA-F4-mod-after","bits":2048,
                     "file":path,"offset":i,
                     "mod_prefix":mod[:16].hex(),
                     "sha1":hashlib.sha1(mod).hexdigest()})
        # try modulus BEFORE
        if i >= 256:
            mod = data[i-256:i]
            if shannon(mod) > 7.3:
                add({"type":"RSA-F4-mod-before","bits":2048,
                     "file":path,"offset":i-256,
                     "mod_prefix":mod[:16].hex(),
                     "sha1":hashlib.sha1(mod).hexdigest()})
        # try 384B (3072) and 512B (4096)
        for sz in (384, 512):
            if i + 4 + sz <= len(data):
                mod = data[i+4:i+4+sz]
                if shannon(mod) > 7.4:
                    add({"type":f"RSA-F4-mod-after-{sz*8}b",
                         "file":path,"offset":i,
                         "mod_prefix":mod[:16].hex(),
                         "sha1":hashlib.sha1(mod).hexdigest()})
        i += 1

def scan_consts(path, data):
    for name, pat in CONSTS.items():
        i = data.find(pat)
        if i >= 0:
            add({"type":"CONST","const":name,"file":path,"offset":i})

def scan_known(path, data):
    if KNOWN_HARMAN in data:
        add({"type":"KNOWN","key":"Harman a178eb3e",
             "file":path,"offset":data.find(KNOWN_HARMAN)})
    if KNOWN_GMCSM in data:
        # GM CSM 3-byte prefix is generic; require larger context
        i = 0
        while True:
            i = data.find(KNOWN_GMCSM, i)
            if i < 0: break
            add({"type":"KNOWN","key":"GM CSM b3a5b7",
                 "file":path,"offset":i})
            i += 1

def scan_file(path):
    try:
        sz = os.path.getsize(path)
    except Exception: return
    if sz == 0 or sz > MAX_FILE: return
    try:
        with open(path,"rb") as f: data = f.read()
    except Exception: return
    scan_pem(path, data)
    scan_ssh(path, data)
    scan_pkcs7(path, data)
    scan_known(path, data)
    scan_consts(path, data)
    scan_avb(path, data)
    scan_intel_cse(path, data)
    scan_der(path, data)

def should_scan(path):
    p = path.lower()
    base = os.path.basename(p)
    ext = os.path.splitext(p)[1]
    if ext in EXCLUDE_EXT: return False
    if ext in INCLUDE_EXT: return True
    if any(tok in p for tok in KEY_PATH_TOKENS): return True
    return False

def walk_targets():
    yielded = 0
    for f in TMP_FILES:
        if os.path.exists(f):
            yield f; yielded += 1
    for d in TMP_DIRS:
        if os.path.isdir(d):
            for root, dirs, files in os.walk(d):
                for fn in files:
                    yield os.path.join(root, fn); yielded += 1
    # GM tree — selective
    for root, dirs, files in os.walk(GM_ROOT):
        # prune obvious bulk
        dirs[:] = [d for d in dirs if d not in ("media","fonts","tts","app","priv-app","overlay","splash","lost+found")]
        for fn in files:
            p = os.path.join(root, fn)
            if should_scan(p):
                yield p

count = 0
for p in walk_targets():
    count += 1
    scan_file(p)
    if count % 500 == 0:
        print(f"scanned {count} files, findings={len(findings)}", file=sys.stderr)

print(f"DONE scanned={count} findings={len(findings)}", file=sys.stderr)
with open("/tmp/crypto_findings.json","w") as f:
    json.dump(findings, f, default=str, indent=1)
