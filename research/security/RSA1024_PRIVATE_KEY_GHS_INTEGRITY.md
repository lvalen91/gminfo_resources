# RSA-1024 Candidate — GHS Hypervisor

**Classification:** Security Research Finding
**Date:** 2026-06-29
**Evidence status:** unvalidated scan candidate; security impact not established
**Status (corrected 2026-11-11):** private-key parsing, source location, function and signer relationship remain unverified. This is not a recovered calibration-signing key. See the [central reference](../GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md).

---

## Finding Summary

An earlier automated scan reported a 609-byte RSA-1024 private-key candidate in the
`ghs_integrity.elf` SOC_HOSTOS artifact. The status table in this document has always left
parsing/validation, matching public key and code usage pending. The earlier headline and
claims of a confirmed embedded private key therefore overstated the evidence.

**Correction reason/date (2026-11-11):** no retained validation result establishes that these
bytes are a valid private key, what they do, or that the radio accepts signatures made with
them. The reported decimal offset `12924442` also does not equal the earlier hexadecimal
`0xC53DBA`; its arithmetic conversion is `0xc5361a`. The source location must be
re-established before any extraction result is trusted. Independent stock CSM verification
uses RSA-2048 signers; no relationship to this alleged RSA-1024 candidate was found.

---

## Technical Details

| Field | Value |
|---|---|
| **File** | `ghs_integrity.elf` |
| **Component** | SOC_HOSTOS |
| **File ID** | 85098662 |
| **File size** | 14,929,956 bytes |
| **Binary format** | ELF — header says 32-bit x86 but code is **x86-64** (corrected 2026-08-26: `movabs`/REX, `crt_x64.86`) |
| **Reported candidate offset** | Decimal 12924442; earlier hex 0xC53DBA disagrees; source location unverified |
| **Reported candidate size** | 609 bytes; DER/private-key interpretation unvalidated |
| **Claimed type** | RSA-1024 private-key candidate, not validated |
| **Validation result** | Not supplied |
| **Location** | Embedded directly in the hypervisor image — not a separate partition |

### Validation boundary

The former extraction command used an unverified offset. Re-establish the original artifact
and candidate location, then check parsing and public-key relationships without emitting
private-key material into documentation or logs. No such validation was performed here.

---

## Security relevance

A valid private key would matter only for a verifier that trusts its corresponding public
key and an artifact format that the key can sign. Neither condition is established here.
RSA-1024 sizing or a scan classification alone does not make a key useful for the observed
RSA-2048 CSM containers, Android platform APKs, or signed OTA manifests.

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

### Steps 1–3: Establish the artifact, validate the candidate, compare public identities

First resolve the conflicting offsets against the original SOC_HOSTOS package. Check whether
the candidate parses as a private key rather than a certificate, public key, test vector or
coincidental bytes. Keep private components out of files, reports and logs. Only after a
successful parse should its public identity be compared in memory with known verifier keys.
Record equality and provenance, not key values. These steps are pending, not completed.

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

- The same reported candidate bytes would be present in **both Y177 and Y181**, if located in their shared artifact
- Any capability would still require validation of the candidate and its actual verifier usage
- A downgrade to Y177 does not change the exposure surface with respect to this key

---

## Status

| Item | Status |
|---|---|
| Scan candidate reported | YES; independently unvalidated |
| Candidate offset confirmed | NO; reported decimal/hex disagree |
| Key parsed and validated | PENDING |
| Key function determined | UNKNOWN — REQUIRES INVESTIGATION |
| Matching public key located in corpus | PENDING |
| Key usage found in decompiled code | PENDING |
| Claimed key size | RSA-1024; parsing pending |
| Exploitation attempted | NO |
| Present in Y177 | Candidate location unverified; shared artifact reported |
| Present in Y181 | Candidate location unverified |

---

*Finding identified via automated binary scan of the GM Info 3.7 firmware corpus. All analysis performed on legally obtained firmware images for security research purposes.*
