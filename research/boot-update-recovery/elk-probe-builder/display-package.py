from pathlib import Path
import gzip, hashlib, shlex, stat, struct, subprocess

out=Path('/work/display-artifacts')
out.mkdir(exist_ok=True)
entries={name:(stat.S_IFDIR|0o755,b'') for name in ['dev','proc','sys','tmp','bin','etc','lib','lib/firmware','lib/firmware/i915']}
entries['init']=(stat.S_IFREG|0o755,Path('/work/display-init').read_bytes())
entries['bin/busybox']=(stat.S_IFREG|0o755,(out/'busybox').read_bytes())
for name in (out/'busybox.applets').read_text().splitlines():
    assert name and '/' not in name and name not in ['.','..']
    if name!='busybox':entries['bin/'+name]=(stat.S_IFLNK|0o777,b'busybox')
ssh_root=out/'ssh_root'
release=Path('/work/out-display/include/config/kernel.release').read_text().strip()
for p in sorted(ssh_root.rglob('*'),key=lambda p:(len(p.relative_to(ssh_root).parts),str(p))):
    name=p.relative_to(ssh_root).as_posix();mode=p.lstat().st_mode
    # Keep the RAM boot image small; graphics runtime can be loaded after boot.
    if name=='opt/graphics' or name.startswith('opt/graphics/') or name in ['usr/sbin/gpu-render-test','usr/sbin/vulkaninfo','usr/sbin/vainfo']:continue
    parts=name.split('/')
    if len(parts)>2 and parts[:2]==['lib','modules'] and parts[2][0].isdigit() and parts[2]!=release:continue
    if p.is_symlink():
        mode=stat.S_IFLNK|0o700
        body=str(p.readlink()).encode()
    elif p.is_dir():body=b''
    else:body=p.read_bytes()
    entries[name]=(mode,body)
fw=Path('/work/inputs/bxt_dmc_ver1_07.bin')
entries['lib/firmware/i915/'+fw.name]=(stat.S_IFREG|0o644,fw.read_bytes())
data=bytearray()
for ino,(name,(mode,body)) in enumerate([*entries.items(),('TRAILER!!!',(0,b''))],1):
    encoded=name.encode()+b'\0'
    values=[ino,mode,0,0,1,0,len(body),0,0,0,0,len(encoded),0]
    data.extend(b'070701'+''.join(f'{n:08x}' for n in values).encode()+encoded)
    data.extend(b'\0'*((-len(data))%4));data.extend(body);data.extend(b'\0'*((-len(data))%4))
data.extend(b'\0'*((-len(data))%512))
(out/'initramfs.cpio.gz').write_bytes(gzip.compress(data,compresslevel=6,mtime=0))
print('initramfs_entries',len(entries),'compressed_bytes',(out/'initramfs.cpio.gz').stat().st_size)
kernel=out/'bzImage'
if kernel.exists():
    b=kernel.read_bytes();assert b[0x202:0x206]==b'HdrS'
    print('kernel_bytes',len(b),'protocol',hex(struct.unpack_from('<H',b,0x206)[0]),'xloadflags',hex(struct.unpack_from('<H',b,0x236)[0]))
    args=shlex.split(Path('/work/inputs/mkbootimg_args.txt').read_text())
    for flag,path in [('--kernel',kernel),('--ramdisk',out/'initramfs.cpio.gz'),('--second',Path('/work/inputs/second'))]:
        args[args.index(flag)+1]=str(path)
    args[args.index('--cmdline')+1]='rdinit=/init console=tty0 loglevel=8 printk.time=1 log_buf_len=4M fbcon=font:SUN12x22 ignore_loglevel panic=0 consoleblank=0 no_console_suspend i915.modeset=1 i915.enable_guc=0 i915.enable_fbc=0 i915.enable_psr=0 iTCO_wdt.force_no_reboot=1 nowatchdog drm.edid_firmware=HDMI-A-1:edid/harman0960p.bin video=HDMI-A-1:e'
    subprocess.run(['/usr/bin/python3','/work/inputs/mkbootimg.py',*args,'--output',str(out/'boot.img')],check=True)
    image=(out/'boot.img').read_bytes();assert image[:8]==b'ANDROID!' and len(image)<0x8000000
    for p in [kernel,out/'initramfs.cpio.gz',out/'boot.img']:
        print(p.name,p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest())
