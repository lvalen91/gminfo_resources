#!/usr/bin/env python3
"""Decrypt a GM/Bosch MDI2 Manager port-9052 log-pull stream.

Cipher: standard Blowfish-ECB (big-endian), 56-byte SESSION key.
The key is per-session; extract it live from the running Manager with a Frida
hook on bvtx_vci_rt.dll BF_set_key (RVA 0x1dce80) reading its 56-byte key arg
(see mdi2_macos/ps/frida_bf.py). Framing on port 9052 (device 192.168.171.2):
  8-byte control frame  : 00 53 50 00 00 XX 00 00   (skipped)
  message frame         : [u32be 0][u32be len][u32 counter][Blowfish-ECB body]
Decrypted body of the big frame = inner container ([le size/id/name] entries,
e.g. name "messages"=Varlog) followed by the raw log text.

Usage: mdi2_9052_decrypt.py <pcap> <key_hex_56B>   (needs tshark + pycryptodome)
"""
import sys, subprocess, struct, binascii
from Crypto.Cipher import Blowfish

def stream_bytes(pcap):
    out = subprocess.check_output(["tshark","-r",pcap,"-Y",
        "tcp.srcport==9052 && tcp.len>0","-T","fields","-e","tcp.seq","-e","data.data"],
        text=True)
    ch=[]
    for line in out.splitlines():
        p=line.split("\t")
        if len(p)>=2 and p[1].strip(): ch.append((int(p[0]),binascii.unhexlify(p[1])))
    ch.sort(); return b"".join(d for _,d in ch)

def frames(blob):
    i=0
    while i+8<=len(blob):
        if blob[i:i+4]==b"\x00\x53\x50\x00": i+=8; continue   # control frame
        z,ln=struct.unpack_from(">II",blob,i)
        if z!=0 or ln<4 or i+8+ln>len(blob): break
        payload=blob[i+8:i+8+ln]; yield payload[:4],payload[4:]; i+=8+ln

def main():
    pcap,keyhex=sys.argv[1],sys.argv[2]
    key=binascii.unhexlify(keyhex); assert len(key)==56
    blob=stream_bytes(pcap)
    frs=list(frames(blob))
    body=max((b for _,b in frs),key=len)
    body=body[:len(body)-len(body)%8]
    pt=Blowfish.new(key,Blowfish.MODE_ECB).decrypt(body)
    idx=pt.find(b"Aug ")  # crude: strip inner container header to first syslog line
    sys.stdout.buffer.write(pt if idx<0 else pt[idx:])

if __name__=="__main__": main()
