# RSA-1024 Private Key Discovery in GHS INTEGRITY Hypervisor

**Classification:** Security Research Finding
**Date:** 2026-06-29
**Severity:** HIGH — Embedded private key in production hypervisor binary
**Status:** Key identified; function under investigation

---

## Finding Summary

During binary analysis of `ghs_integrity.elf` (the GHS INTEGRITY IoT 2020.18.19 hypervisor binary shipped in GM Info 3.7), an RSA-1024 private key was found embedded at byte offset **12924442**, 609 bytes in length (SHA1: `78d9a50f`).

This is the **only private key** found across the entire GM Info 3.7 binary corpus in all analyzed firmware files. Its presence in the hypervisor image itself — rather than in a keystore, certificate partition, or protected enclave — is anomalous and warrants immediate investigation to determine what it signs or authenticates, and whether possession of it confers any exploitable capability.

---

## Technical Details

| Field | Value |
|---|---|
| **File** | `ghs_integrity.elf` |
| **Component** | SOC_HOSTOS |
| **File ID** | 85098662 |
| **File size** | 14,929,956 bytes |
| **Binary format** | ELF 32-bit x86 |
| **Key offset** | 12924442 (0xC53DBA) |
| **Key size** | 609 bytes (DER-encoded) |
| **Key type** | RSA-1024 PRIVATE KEY |
| **SHA1** | 78d9a50f... |
| **Location** | Embedded directly in the hypervisor image — not a separate partition |

### Extraction Command

```bash
dd if=ghs_integrity.elf bs=1 skip=12924442 count=609 | openssl rsa -inform DER -check
```

---

## RSA-1024 Security Posture

RSA-1024 is cryptographically weak by contemporary standards and has been for over a decade:

- **NIST deprecation:** NIST deprecated RSA-1024 in 2013 (SP 800-131A) and prohibited its use in federal systems as of 2014
- **Factorization feasibility:** Academic and commercial literature estimates factorization of a 1024-bit RSA modulus costs on the order of $1–10M USD in compute as of 2020; this cost has decreased with improved hardware and algorithms since then
- **Practical risk:** If the modulus is factorizable, an attacker who derives the private key from the public modulus could forge any artifact this key is used to sign — regardless of whether the embedded key itself is extracted

The embedded private key exacerbates this: even without performing the factorization, an attacker already possesses the private key material directly.

---

## Hypotheses for Key Function

The actual purpose of this key is unknown. The following are candidate functions based on common GHS INTEGRITY IPC and firmware validation architectures:

1. **IPC channel authentication** — GHS INTEGRITY supports signed inter-partition connection channels in certain configurations. This key may authenticate the hypervisor's IPC endpoints to guest partitions (e.g., to the Android guest).

2. **Hypervisor attestation** — The key may be used by the GHS layer to attest to the Android guest's boot state or to sign health reports consumed by other ECUs.

3. **Firmware / update package signing** — The key may be used to sign VIP or ABL update packages at the GHS layer, independent of the AVB/vbmeta chain that governs the Android partition.

4. **Encrypted partition channel** — The key may establish an encrypted session between GHS partitions (e.g., between the safety partition and the infotainment partition).

5. **Development / debug artifact** — The key may be a leftover from a test or debug build configuration and not active in production. This is common in automotive ECU firmware; keys used during factory provisioning or CI signing are sometimes not stripped before release.

These hypotheses are mutually exclusive only in degree — the key could serve more than one function, or could be entirely dormant.

---

## Investigation Steps

### Step 1: Confirm key type and validity

Extract the key material and verify it parses as a valid RSA-1024 private key rather than a public key, certificate, or coincidental byte pattern:

```python
import subprocess

# Extract 609 bytes at offset 12924442
result = subprocess.run(
    ["dd", "if=ghs_integrity.elf", "bs=1", "skip=12924442", "count=609"],
    capture_output=True
)

# Write to temp file
with open("/tmp/candidate_key.der", "wb") as f:
    f.write(result.stdout)

# Attempt to parse as RSA private key
subprocess.run(["openssl", "rsa", "-inform", "DER", "-in", "/tmp/candidate_key.der", "-check", "-text", "-noout"])
```

Alternatively, if the key is PEM-encoded within the binary, extract the PEM block directly:

```bash
strings -n 20 ghs_integrity.elf | grep -A 50 "BEGIN RSA PRIVATE KEY"
```

### Step 2: Extract the public modulus

Once confirmed, extract the public modulus from the private key. This modulus is what can be matched against signatures or public keys found elsewhere:

```bash
openssl rsa -inform DER -in /tmp/candidate_key.der -pubout -out /tmp/candidate_pubkey.pem
openssl rsa -pubin -in /tmp/candidate_pubkey.pem -text -noout | grep -A 20 "Modulus"
```

### Step 3: Search the binary corpus for matching public keys

Search all other firmware files in the GM Info 3.7 corpus for the extracted public modulus. If any file contains the corresponding public key or a certificate embedding this modulus, that narrows the key's role:

```bash
# Search for the modulus bytes in all ELF/binary files
grep -rl <modulus-hex-pattern> /path/to/firmware/corpus/
```

### Step 4: Locate key usage in decompiled code

In a decompiler (Ghidra, Binary Ninja, IDA), locate the key's offset and find all cross-references to the memory region containing it. Functions that load or dereference this offset reveal the key's runtime role. Search for:

- RSA sign/verify call sites near the key offset
- String references such as `"rsa"`, `"sign"`, `"verify"`, `"ipc"`, `"auth"`, `"attest"`
- GHS INTEGRITY kernel API calls related to connection authentication (`INTEGRITY_Connect`, `RequestConnection`, etc.)

### Step 5: Check update packages for matching signatures

If any update packages (OTA, calibration, VIP) in the corpus bear detached RSA signatures, attempt verification using the extracted public key:

```bash
openssl dgst -sha256 -verify /tmp/candidate_pubkey.pem -signature <sig_file> <payload_file>
```

A successful verification confirms this key is part of the update signing chain.

---

## Relevance to Y177 Downgrade

If this key is involved in signing or authenticating any component of the update/downgrade package validation chain — at the GHS layer, outside of the AVB/vbmeta path — then possession of the private key could allow construction of signed packages that pass GHS-layer validation without requiring exploitation of the AVB chain.

Even if the key is not directly exploitable in the current attack surface, characterizing what it signs narrows the trust boundary and may reveal additional paths. Understanding every link in the validation chain is prerequisite to knowing which links are actually load-bearing for a downgrade to Y177.

---

## Note on Cross-Version Binary Sharing

The GHS INTEGRITY binary (file ID 85098662) is **byte-for-byte identical** between Y177 and Y181. The SHA1 of the file matches across both firmware versions.

This means:

- This private key is present in **both Y177 and Y181**
- Any capability conferred by this key applies regardless of which version is currently running
- A downgrade to Y177 does not change the exposure surface with respect to this key

---

## Status

| Item | Status |
|---|---|
| Key identified in binary | YES |
| Key offset confirmed | YES (12924442 / 0xC53DBA) |
| Key parsed and validated | PENDING |
| Key function determined | UNKNOWN — REQUIRES INVESTIGATION |
| Matching public key located in corpus | PENDING |
| Key usage found in decompiled code | PENDING |
| Key strength | WEAK — RSA-1024, deprecated since 2013 |
| Exploitation attempted | NO |
| Present in Y177 | YES (binary identical to Y181) |
| Present in Y181 | YES |

---

*Finding identified via automated binary scan of the GM Info 3.7 firmware corpus. All analysis performed on legally obtained firmware images for security research purposes.*
