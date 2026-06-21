#!/usr/bin/env python3
import struct, hashlib, os, sys, subprocess

Y181="/Users/zeno/Downloads/misc/GM_research/gm_aaos/2024_Silverado_ICE/firmware/update_packages/Y181"
EP="/Users/zeno/Downloads/misc/GM_research/gm_aaos/2024_Silverado_ICE/firmware/extracted_partitions"

def hexd(b,n=16): return b[:n].hex()

# ---------- 1. AVB vbmeta ----------
print("="*70); print("1. AVB vbmeta (86331644)"); print("="*70)
with open(f"{Y181}/86331644","rb") as f: vb=f.read()
# AvbVBMetaImageHeader: big-endian
# magic[4], required_libavb_version_major(u32), minor(u32),
# authentication_data_block_size(u64), auxiliary_data_block_size(u64),
# algorithm_type(u32), hash_offset(u64), hash_size(u64),
# signature_offset(u64), signature_size(u64),
# public_key_offset(u64), public_key_size(u64),
# public_key_metadata_offset(u64), public_key_metadata_size(u64),
# descriptors_offset(u64), descriptors_size(u64),
# rollback_index(u64), flags(u32), rollback_index_location(u32),
# release_string[48], padding[80]
hdr = struct.unpack(">4sIIQQIQQQQQQQQQQQII48s80s", vb[:256])
(magic,maj,minr,auth_sz,aux_sz,algo,hash_off,hash_sz,sig_off,sig_sz,
 pk_off,pk_sz,pkm_off,pkm_sz,desc_off,desc_sz,rb_idx,flags,rb_loc,rel,pad)=hdr
print(f"magic={magic} libavb={maj}.{minr} algo={algo} flags={flags} rb_idx={rb_idx} rb_loc={rb_loc}")
print(f"auth_blk={auth_sz} aux_blk={aux_sz}")
print(f"hash off={hash_off} sz={hash_sz}; sig off={sig_off} sz={sig_sz}; pk off={pk_off} sz={pk_sz}; desc off={desc_off} sz={desc_sz}")
print(f"release={rel.rstrip(b'\x00').decode(errors='replace')}")

aux = vb[256+auth_sz : 256+auth_sz+aux_sz]
# pubkey of vbmeta itself
if pk_sz:
    pk = aux[pk_off:pk_off+pk_sz]
    # AvbRSAPublicKeyHeader: key_num_bits(u32 BE), n0inv(u32 BE), then n[bits/8], rr[bits/8]
    kbits, n0inv = struct.unpack(">II", pk[:8])
    print(f"\nVBMeta signing pubkey: {kbits}-bit RSA, n0inv=0x{n0inv:08x}")
    n = pk[8:8+kbits//8]
    print(f"  n SHA256: {hashlib.sha256(n).hexdigest()}")
    print(f"  n head:   {n[:16].hex()}")

# walk descriptors
print("\nDescriptors:")
descs = aux[desc_off:desc_off+desc_sz]
o = 0
chain_keys=[]
while o + 16 <= len(descs):
    tag, num_bytes_following = struct.unpack(">QQ", descs[o:o+16])
    body = descs[o+16:o+16+num_bytes_following]
    types={0:"PROPERTY",1:"HASHTREE",2:"HASH",3:"KERNEL_CMDLINE",4:"CHAIN_PARTITION"}
    t=types.get(tag,f"UNK({tag})")
    print(f"\n[+0x{o:04x}] tag={tag} ({t}) bytes={num_bytes_following}")
    if tag==0:  # PROPERTY: key_num_bytes(u64), value_num_bytes(u64), key, 0, value, 0
        kn, vn = struct.unpack(">QQ", body[:16])
        k=body[16:16+kn]; v=body[16+kn+1:16+kn+1+vn]
        print(f"  PROP {k!r} = {v!r}")
    elif tag==2:  # HASH
        # image_size(u64), hash_alg[32], partition_name_len(u32), salt_len(u32), digest_len(u32), flags(u32), reserved[60], name, salt, digest
        img_sz, halg, pn_len, salt_len, dig_len, hflags = struct.unpack(">Q32sIIII", body[:56])
        # 60 bytes reserved
        p = 56+60
        name = body[p:p+pn_len].decode(errors='replace'); p+=pn_len
        salt = body[p:p+salt_len]; p+=salt_len
        dig  = body[p:p+dig_len]
        print(f"  HASH partition={name!r} img_sz={img_sz} alg={halg.rstrip(b'\x00').decode()} flags={hflags}")
        print(f"    salt={salt.hex()}  digest={dig.hex()}")
    elif tag==1:  # HASHTREE
        # dm_verity_version(u32), image_size(u64), tree_offset(u64), tree_size(u64),
        # data_block_size(u32), hash_block_size(u32), fec_num_roots(u32), fec_offset(u64), fec_size(u64),
        # hash_alg[32], partition_name_len(u32), salt_len(u32), root_digest_len(u32), flags(u32), reserved[60]
        (dmv, img_sz, tree_off, tree_sz, dblk, hblk, fec_n, fec_off, fec_sz,
         halg, pn_len, salt_len, dig_len, hflags) = struct.unpack(">IQQQIIIQQ32sIIII", body[:104])
        p = 104+60
        name = body[p:p+pn_len].decode(errors='replace'); p+=pn_len
        salt = body[p:p+salt_len]; p+=salt_len
        dig  = body[p:p+dig_len]
        print(f"  HASHTREE partition={name!r} dm-verity v{dmv} img_sz={img_sz} tree_off={tree_off} tree_sz={tree_sz}")
        print(f"    data_blk={dblk} hash_blk={hblk} fec_n={fec_n} fec_off={fec_off} fec_sz={fec_sz} alg={halg.rstrip(b'\x00').decode()} flags={hflags}")
        print(f"    salt={salt.hex()}  root={dig.hex()}")
    elif tag==3:  # KERNEL_CMDLINE
        kflags, cl_len = struct.unpack(">II", body[:8])
        cl = body[8:8+cl_len].decode(errors='replace')
        print(f"  CMDLINE flags={kflags} {cl!r}")
    elif tag==4:  # CHAIN_PARTITION
        # rb_loc(u32), partition_name_len(u32), pubkey_len(u32), reserved[64], name, pk
        rl, pn_len, pkl = struct.unpack(">III", body[:12])
        p = 12+64
        name = body[p:p+pn_len].decode(errors='replace'); p+=pn_len
        pkb  = body[p:p+pkl]
        kbits, n0inv = struct.unpack(">II", pkb[:8])
        n = pkb[8:8+kbits//8]
        fp = hashlib.sha256(n).hexdigest()
        print(f"  CHAIN partition={name!r} rb_loc={rl} pk_bits={kbits} pk_sha256(n)={fp}")
        chain_keys.append((name, kbits, n, pkb))
    o += 16 + num_bytes_following
print(f"\nChain partitions total: {len(chain_keys)}")
for n,b,_,_ in chain_keys: print(f"  - {n} ({b}-bit)")

# ---------- 2. ACPI (86331630) ----------
print("\n"+"="*70); print("2. ACPI tables (86331630)"); print("="*70)
with open(f"{Y181}/86331630","rb") as f: acp=f.read()
# Walk known table signatures starting at offset 0; first 4 bytes "ACPI" header? Let's check
print(f"first16: {acp[:16].hex()} ascii={acp[:16]!r}")
# Try to find tables by signature: 4-char sig + length(u32 LE) + rev(u8) + checksum(u8) + OEM_ID[6] + OEM_TABLE_ID[8] + OEMRevision(u32) + CreatorID[4] + CreatorRev(u32) = 36B
KNOWN={b"FACP",b"APIC",b"DSDT",b"SSDT",b"HPET",b"MCFG",b"WAET",b"BGRT",b"BOOT",b"FPDT",b"FIDT",b"DBG2",b"DBGP",b"LPIT",b"NHLT",b"PRMT",b"TPM2",b"WSMT",b"ECDT",b"SLIC",b"ASF!",b"CSRT",b"DMAR",b"SRAT",b"MSDM",b"OEMA",b"OEMB",b"PCCT",b"RSDT",b"XSDT",b"GTDT",b"IORT",b"PPTT",b"WDAT"}
i=0; tables=[]
while i < len(acp)-36:
    sig=acp[i:i+4]
    if sig in KNOWN or (sig[:1]==b"S" and sig[1:2]==b"S" and sig[2:3]==b"D" and sig[3:4]==b"T"):
        ln=struct.unpack("<I",acp[i+4:i+8])[0]
        if 36 <= ln <= 0x200000 and i+ln <= len(acp):
            rev=acp[i+8]; oem=acp[i+10:i+16]; oemtbl=acp[i+16:i+24]; oemrev=struct.unpack("<I",acp[i+24:i+28])[0]
            cid=acp[i+28:i+32]
            tables.append((i,sig,ln,rev,oem,oemtbl,oemrev,cid))
            i += ln; continue
    i += 1
print(f"Tables found: {len(tables)}")
for off,sig,ln,rev,oem,oemtbl,oemrev,cid in tables:
    print(f"  @0x{off:06x} {sig.decode()} len={ln} rev={rev} OEM={oem!r} TID={oemtbl!r} OEMrev={oemrev} CID={cid!r}")

# Inventory _HID strings from DSDT/SSDT regions
hids=set()
for off,sig,ln,*_ in tables:
    if sig in (b"DSDT",b"SSDT"):
        blob=acp[off:off+ln]
        # naive: search for '_HID' followed by EISAID or string
        idx=0
        while True:
            j=blob.find(b"_HID",idx)
            if j<0: break
            ctx=blob[j:j+24]
            hids.add(ctx.hex()[:48])
            idx=j+4
print(f"_HID occurrences (raw nibbles, first 30): {len(hids)}")
# extract printable ID-like strings near _HID
import re
for off,sig,ln,*_ in tables:
    if sig in (b"DSDT",b"SSDT"):
        blob=acp[off:off+ln]
        # find ASCII tokens that look like ACPI HIDs
        for m in re.finditer(rb"[A-Z]{3,4}[0-9A-F]{3,4}", blob):
            s=m.group().decode()
            if 7<=len(s)<=8: hids.add(s)
hidlist=sorted(x for x in hids if isinstance(x,str) and len(x)<=8)
print(f"ACPI/PNP HID candidates: {len(hidlist)}")
for h in hidlist[:80]: print(f"  {h}")

# ---------- 3. SOC_UTILS (86331623) ----------
print("\n"+"="*70); print("3. SOC_UTILS (86331623)"); print("="*70)
with open(f"{Y181}/86331623","rb") as f: su=f.read()
print(f"first32={su[:32].hex()} ascii={su[:32]!r} size={len(su)}")
# 'ipk.' magic — look for inner header
# Usually GM IPK: 'ipk.' + version + size + payload (often LZMA / SquashFS)
# Search for known magics inside
for sig,name in [(b"\x5d\x00\x00",b"LZMA"),(b"\xfd7zXZ",b"XZ"),(b"hsqs",b"SquashFS"),(b"\x1f\x8b",b"gzip"),(b"BZh",b"bzip2"),(b"\x28\xb5\x2f\xfd",b"zstd"),(b"\x7fELF",b"ELF"),(b"ANDROID!",b"AndroidBoot"),(b"AVB0",b"AVB")]:
    idx=0; found=[]
    while True:
        j=su.find(sig,idx)
        if j<0: break
        found.append(j); idx=j+1
        if len(found)>=8: break
    if found: print(f"  {name.decode()} sig at: {[hex(x) for x in found]}")
# strings sample (printable >=8) early
def strings(b,minlen=8,limit=40):
    out=[]; cur=bytearray()
    for ch in b:
        if 32<=ch<127: cur.append(ch)
        else:
            if len(cur)>=minlen: out.append(cur.decode())
            cur=bytearray()
            if len(out)>=limit: break
    return out
print("Early strings:")
for s in strings(su[:8192],8,30): print(f"  {s}")

# ---------- 5. 4 RSA-1024 keys in /tmp/ghs_integrity.elf ----------
print("\n"+"="*70); print("5. RSA-1024 SubjectPublicKeyInfo blobs in ghs_integrity.elf"); print("="*70)
with open("/tmp/ghs_integrity.elf","rb") as f: ghs=f.read()
offsets=[14607467,14607489,14608153,14608175]
# SPKI for RSA-1024 typically 162 bytes (DER): SEQ(160) {SEQ AlgId, BIT STRING ... }
for off in offsets:
    # read up to 200 bytes; parse outer SEQUENCE
    raw=ghs[off:off+200]
    if raw[0]!=0x30:
        # try -1
        for delta in (-2,-1,1,2):
            if ghs[off+delta]==0x30:
                off+=delta; raw=ghs[off:off+200]; break
    # length parsing
    if raw[1] & 0x80:
        ln_bytes=raw[1]&0x7f; ln=int.from_bytes(raw[2:2+ln_bytes],"big"); total=2+ln_bytes+ln
    else:
        ln=raw[1]; total=2+ln
    der=ghs[off:off+total]
    fp=hashlib.sha256(der).hexdigest()
    print(f"\noffset={off} len={total} sha256={fp}")
    # try openssl decode
    p=subprocess.run(["openssl","pkey","-pubin","-inform","DER","-text","-noout"],input=der,capture_output=True)
    if p.returncode==0:
        print(p.stdout.decode())
    else:
        # try as raw RSAPublicKey
        p2=subprocess.run(["openssl","rsa","-pubin","-inform","DER","-RSAPublicKey_in","-text","-noout"],input=der,capture_output=True)
        print("openssl pkey err:", p.stderr.decode()[:200])
        if p2.returncode==0: print(p2.stdout.decode())
    # convert to PEM
    pem=subprocess.run(["openssl","pkey","-pubin","-inform","DER","-outform","PEM"],input=der,capture_output=True)
    if pem.returncode==0:
        with open(f"/tmp/ghs_pubkey_{off}.pem","wb") as f: f.write(pem.stdout)
        print(f"  PEM saved /tmp/ghs_pubkey_{off}.pem")

# ---------- 6. Property contexts ----------
print("\n"+"="*70); print("6. Property contexts"); print("="*70)
pc_y181=open(f"{EP}/vendor_extracted/etc/selinux/vendor_property_contexts").read()
pc_y177_path=f"{EP}/Y177_vendor_extracted/Y177_vendor/etc/selinux/vendor_property_contexts"
pc_y177=open(pc_y177_path).read() if os.path.exists(pc_y177_path) else ""
print(f"Y181 lines={len(pc_y181.splitlines())} Y177 lines={len(pc_y177.splitlines())}")

interest_kw=["safemode","debug","engineer","factory","test","bypass","frozen","spi_change","protokey","security_state","harman.wireless","cts.port","unlock","root","permissive","adb"]
specific=["gm_protokey_recovery_prop","vendor_gm_security_state_prop","persist.vendor.safemode","ro.vendor.safemode","debug.cts.port.off","persist.vendor.harman.wireless","vendor.gm.frozendump","vendor.spi_change_cpu"]
print("\nSpecific properties:")
for s in specific:
    hits=[ln for ln in pc_y181.splitlines() if s in ln]
    for h in hits: print(f"  {h.strip()}")
print("\nProperties matching debug/safemode/engineering/bypass/etc.:")
for ln in pc_y181.splitlines():
    if any(k in ln.lower() for k in interest_kw):
        print(f"  {ln.strip()}")

# Find properties accessible from shell/system contexts (look for u:object_r:..._prop:s0 typed with shell or system reachable)
# We just dump a count by sepcontext
from collections import Counter
ctxs=Counter()
for ln in pc_y181.splitlines():
    parts=ln.split()
    if len(parts)>=2 and parts[1].startswith("u:object_r:"):
        ctxs[parts[1]] += 1
print(f"\nUnique property contexts: {len(ctxs)}; top 15:")
for c,n in ctxs.most_common(15): print(f"  {n:4d} {c}")

# ---------- 7. SELinux precompiled_sepolicy ----------
print("\n"+"="*70); print("7. SELinux precompiled_sepolicy"); print("="*70)
sp_path=f"{EP}/vendor_extracted/etc/selinux/precompiled_sepolicy"
sp=open(sp_path,"rb").read()
print(f"size={len(sp)} magic={sp[:4].hex()}")
# scan for type names "su" and "permissive" keywords (binary policy contains type name table)
def find_word(blob,word):
    w=word.encode()
    out=[]; idx=0
    while True:
        j=blob.find(b"\x00"+w+b"\x00",idx)
        if j<0: break
        out.append(j); idx=j+1
    return out
for w in ["su","sudaemon","kernel","init","shell","adbd","permissive"]:
    h=find_word(sp,w)
    print(f"  type/word {w!r}: {len(h)} occurrences (first {h[:3]})")
# permissive bitmap is in policy header; without setools hard. Search for common dev domains:
for w in ["su","userdebug_or_eng","engineering","factory","debug_only"]:
    h=find_word(sp,w);
    if h: print(f"  notable: {w!r}: {len(h)} (off {h[0] if h else '-'})")
