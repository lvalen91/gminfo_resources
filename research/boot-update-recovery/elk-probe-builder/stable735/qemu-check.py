import json, os, re, selectors, socket, subprocess, time
from pathlib import Path

root=Path.home()/'gm-elk-builder/stable735/artifacts'
# Verify QEMU consumes exactly the payloads packaged for a future ELK test.
import struct, hashlib
image=(root/'boot.img').read_bytes()
assert image[:8]==b'ANDROID!'
ks=struct.unpack_from('<I',image,8)[0];rs=struct.unpack_from('<I',image,16)[0]
page=struct.unpack_from('<I',image,36)[0]
assert page in [2048,4096,8192,16384]
k=image[page:page+ks];roff=page+((ks+page-1)//page)*page
assert k==(root/'bzImage').read_bytes()
assert image[roff:roff+rs]==(root/'initramfs.cpio.gz').read_bytes()
assert struct.unpack_from('<I',image,24)[0]==0
assert k[0x202:0x206]==b'HdrS' and k[0x1fe:0x200]==b'\x55\xaa'
assert struct.unpack_from('<H',k,0x206)[0]>=0x20c and k[0x234]!=0
print('packaged_payloads_verified',len(image),hashlib.sha256(image).hexdigest())
boot_cmdline=(image[64:576]+image[608:1632]).split(b'\0',1)[0].decode('ascii')
assert 'iomem=relaxed' in boot_cmdline
sock=root/'qmp.sock'
if sock.exists():sock.unlink()
fixture=root/'readonly-fixture.raw'
with fixture.open('wb') as f:f.truncate(20*1024*1024)
command=['qemu-system-x86_64','-machine','q35','-accel','tcg','-cpu','qemu64','-m','1024','-smp','2',
 '-kernel',str(root/'bzImage'),'-initrd',str(root/'initramfs.cpio.gz'),
 '-append',boot_cmdline+' console=ttyS0,115200 PROBE_TEST_CONSOLE=1',
 '-display','none','-vga','std','-serial','stdio','-monitor','none','-nic','none','-no-reboot',
 '-qmp',f'unix:{sock},server=on,wait=off',
 '-drive',f'file={fixture},format=raw,if=virtio,readonly=on']
p=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
sel=selectors.DefaultSelector();sel.register(p.stdout,selectors.EVENT_READ)
data=bytearray();start=time.monotonic();success=False;shell_sent=False;command_sent=False;exit_sent=False
try:
 while time.monotonic()-start<90:
  for key,_ in sel.select(0.2):
   chunk=os.read(key.fileobj.fileno(),65536)
   if chunk:
    data.extend(chunk)
    if len(data)>2097152:del data[:-2097152]
  if p.poll() is not None:break
  if not shell_sent and time.monotonic()-start>3 and b'ELK_LINUX_STABLE735_04 uptime=' in data:
   p.stdin.write(b'shell\n');p.stdin.flush();shell_sent=True
  if shell_sent and not command_sent and b'ram-probe#' in data:
   p.stdin.write(b"printf '<6>STABLE73504_KERNEL_CONSOLE_OK\\n' > /dev/kmsg; sleep 1; grep -q STABLE73504_KERNEL_CONSOLE_OK /dev/vcs1 && printf 'VTC_READBACK_%s\\n' OK; /usr/sbin/vip-link --selftest; /usr/sbin/elk-select --selftest; test -x /usr/sbin/elk-reboot && printf ELK_REBOOT_TOOL_OK; test -x /usr/sbin/vip-uart-probe && printf VIP_UART_TOOL_OK; for app in i2cdetect i2cget i2cset i2cdump i2ctransfer devmem lspci lsusb; do test -x /bin/$app || printf 'MISSING_%s\\n' APPLET; done; test -c /dev/ptmx && printf 'STABLE73504_PTY_%s\\n' OK; printf 'BUSYBOX_%s\\n' SHELL_OK; printf test | sha256sum; blockdev --getsize64 /dev/vda; ifconfig lo up; dropbearkey -t ed25519 -f /tmp/probe-host-key >/dev/null 2>&1; dropbear -F -E -s -p 127.0.0.1:2222 -P /tmp/dropbear.pid -r /tmp/probe-host-key & db=$!; sleep 1; kill -0 $db && printf 'SSH_%s\\n' SERVER_OK; kill $db; test -c /dev/mem && printf 'DEVMEM_%s\\n' PRESENT; test -s /lib/firmware/regulatory.db && test -s /lib/firmware/regulatory.db.p7s && printf 'REGDB_%s\\n' PRESENT\n");p.stdin.flush();command_sent=True
  if command_sent and not exit_sent and b'9f86d081884c7d659a2feaa0c55ad015' in data and b'20971520' in data and b'SSH_SERVER_OK' in data:
   p.stdin.write(b'exit\n');p.stdin.flush();exit_sent=True
  if time.monotonic()-start>15 and re.search(rb'framebuffer=([1-9][0-9]*)x([1-9][0-9]*) bpp=32',data) and b'USB NCM configuration ready' in data and re.search(rb'BLOCK vda size=40960\s+ro=1',data) and b'BUSYBOX_SHELL_OK' in data and b'9f86d081884c7d659a2feaa0c55ad015' in data and b'SHELL_EXIT' in data and b'SSH_SERVER_OK' in data:
   success=b'VTC_READBACK_OK' in data and b'STABLE73504_PTY_OK' in data and b'MISSING_APPLET' not in data and b'CRC/reset framing/corruption checks PASS' in data and b'VIP_UART_TOOL_OK' in data and b'CRC32C selftest PASS' in data and b'ELK_REBOOT_TOOL_OK' in data and b'DEVMEM_PRESENT' in data and b'REGDB_PRESENT' in data and not re.search(rb'(regulatory.db.*(?:failed|invalid)|failed to load regulatory.db)',data,re.I);break
 if p.poll() is not None:
  data.extend(p.stdout.read())
  print('qemu_exit_code',p.returncode)
 lines=data.decode(errors='replace').splitlines()
 for l in lines:
  if any(s in l for s in ['ELK_LINUX_STABLE735_04','USB ACM','BLOCK ','BLOCK_COUNT','BUSYBOX_SHELL_OK','SHELL_EXIT','Kernel panic','error while loading','Failed to execute','Run /init','bochs-drm','fb0:']):print(l[:400])
 if success:
  with socket.socket(socket.AF_UNIX) as q:
   q.settimeout(4);q.connect(str(sock));f=q.makefile('rwb',buffering=0)
   def receive():
    while True:
     j=json.loads(f.readline())
     if 'return' in j or 'error' in j:return j
   json.loads(f.readline());f.write(b'{"execute":"qmp_capabilities"}\n');receive()
   f.write((json.dumps({'execute':'screendump','arguments':{'filename':str(root/'display.ppm')}})+'\n').encode());print('screenshot',receive())
  with (root/'display.ppm').open('rb') as shot:
   assert shot.readline().strip()==b'P6'
   dimensions=shot.readline().strip().split()
  fb=re.findall(rb'framebuffer=([1-9][0-9]*)x([1-9][0-9]*) bpp=32',data)[-1]
  assert tuple(map(int,dimensions))==tuple(map(int,fb))
  print('framebuffer_screenshot_dimensions',tuple(map(int,dimensions)))
 print('VIP_transport_tools_verified',b'CRC/reset framing/corruption checks PASS' in data and b'VIP_UART_TOOL_OK' in data); print('PID1_and_framebuffer_verified',success); print('kernel_console_and_PTY',b'STABLE73504_KERNEL_CONSOLE_OK' in data,b'STABLE73504_PTY_OK' in data)
 print('shell_checks',{'prompt':b'ram-probe#' in data,'sha256':b'9f86d081884c7d659a2feaa0c55ad015' in data,'block_size':b'20971520' in data,'returned':b'SHELL_EXIT' in data,'ncm':b'USB NCM configuration ready' in data,'ssh_server':b'SSH_SERVER_OK' in data})
 if not success:
  print('required_markers', {m.decode():m in data for m in [b'VTC_READBACK_OK',b'STABLE73504_PTY_OK',b'CRC/reset framing/corruption checks PASS',b'VIP_UART_TOOL_OK',b'CRC32C selftest PASS',b'ELK_REBOOT_TOOL_OK',b'DEVMEM_PRESENT',b'REGDB_PRESENT',b'MISSING_APPLET']})
  print('regulatory_messages', [l for l in lines if 'regulatory.db' in l])
  print('\n'.join(lines[-12:]))
finally:
 p.terminate()
 try:p.wait(timeout=5)
 except subprocess.TimeoutExpired:p.kill();p.wait()
 sel.close()
 if sock.exists():sock.unlink()
if not success:raise SystemExit(1)
