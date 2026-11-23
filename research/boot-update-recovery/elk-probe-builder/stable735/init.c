#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <dirent.h>
#include <limits.h>
#include <sys/stat.h>
#include <sys/mount.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/utsname.h>
#include <sys/reboot.h>
#include <sys/klog.h>
#include <poll.h>
#include <time.h>
#include <sys/wait.h>
#include <signal.h>
#include <termios.h>
#include <linux/fb.h>

static unsigned seconds, frames;
static char controller[256], fb_description[256] = "none";
static bool usb_bound;
static pid_t shell_pid;

static void directory(const char *p) { if (mkdir(p,0755) && errno!=EEXIST) perror(p); }
static int put(const char *p,const char *v) {
 int f=open(p,O_WRONLY|O_CLOEXEC); if(f<0)return -1;
 size_t n=strlen(v); ssize_t r=write(f,v,n); int e=errno; close(f); errno=e;
 return r==(ssize_t)n ? 0 : -1;
}
static bool first_entry(const char *path,char *out,size_t size) {
 DIR *d=opendir(path); if(!d)return false; struct dirent *e; bool found=false;
 while((e=readdir(d)))if(e->d_name[0]!='.') {snprintf(out,size,"%s",e->d_name);found=true;break;}
 closedir(d);return found;
}
static void usb_setup(void) {
 const char *g="/config/usb_gadget/probe";
 directory("/config");
 if(mount("configfs","/config","configfs",0,NULL) && errno!=EBUSY) {perror("configfs");return;}
 directory(g);
 if(put("/config/usb_gadget/probe/idVendor","0x1d6b") ||
    put("/config/usb_gadget/probe/idProduct","0x0104")) {perror("gadget identifiers");return;}
 put("/config/usb_gadget/probe/bcdUSB","0x0200");
 put("/config/usb_gadget/probe/bcdDevice","0x0002");
 directory("/config/usb_gadget/probe/strings/0x409");
 put("/config/usb_gadget/probe/strings/0x409/manufacturer","BenchProbe");
 put("/config/usb_gadget/probe/strings/0x409/product","ELK_LINUX_STABLE735_04");
 put("/config/usb_gadget/probe/strings/0x409/serialnumber","RAMSTABLE73502");
 directory("/config/usb_gadget/probe/configs/c.1");
 directory("/config/usb_gadget/probe/configs/c.1/strings/0x409");
 put("/config/usb_gadget/probe/configs/c.1/strings/0x409/configuration","RAM serial diagnostics");
 put("/config/usb_gadget/probe/configs/c.1/MaxPower","100");
 directory("/config/usb_gadget/probe/functions/acm.usb0");
 if(symlink("/config/usb_gadget/probe/functions/acm.usb0","/config/usb_gadget/probe/configs/c.1/acm.usb0") && errno!=EEXIST)perror("ACM link");
 else puts("USB ACM configuration ready");
 directory("/config/usb_gadget/probe/functions/ncm.usb0");
 if(symlink("/config/usb_gadget/probe/functions/ncm.usb0","/config/usb_gadget/probe/configs/c.1/ncm.usb0") && errno!=EEXIST)perror("NCM link");
 else puts("USB NCM configuration ready");
}
static void usb_bind(void) {
 DIR *d=opendir("/sys/class/usb_role");struct dirent *e;
 if(d){
  while((e=readdir(d))){
   if(e->d_name[0]!='.'){
    char p[PATH_MAX];snprintf(p,sizeof p,"/sys/class/usb_role/%s/role",e->d_name);put(p,"device");
   }
  }
  closedir(d);
 }
 if(!usb_bound && first_entry("/sys/class/udc",controller,sizeof controller)) {
  usb_bound=put("/config/usb_gadget/probe/UDC",controller)==0;
  printf("USB controller=%s bound=%u errno=%d\n",controller,usb_bound,errno);
 }
}
/* fbcon owns scanout: never paint into its framebuffer from PID1. */
static void framebuffer_status(void) {
 int fd=open("/dev/fb0",O_RDONLY|O_CLOEXEC);if(fd<0)return;
 struct fb_var_screeninfo v;struct fb_fix_screeninfo f;
 if(!ioctl(fd,FBIOGET_VSCREENINFO,&v)&&!ioctl(fd,FBIOGET_FSCREENINFO,&f))
  snprintf(fb_description,sizeof fb_description,"%ux%u bpp=%u stride=%u",v.xres,v.yres,v.bits_per_pixel,f.line_length);
 close(fd);
}
static pid_t panel_pid;
static void start_panel(void) {
 if(getenv("PROBE_TEST_CONSOLE")){puts("PANEL: virtual test, hardware initialization skipped");return;}
 panel_pid=fork();
 if(panel_pid==0){execl("/usr/sbin/panel-stock","panel-stock","--init-link",(char*)NULL);perror("panel helper");_exit(127);}
 if(panel_pid<0)perror("fork panel helper");
}
static void status(int fd) {
 struct utsname u;uname(&u);
 dprintf(fd,"ELK_LINUX_STABLE735_04 uptime=%u kernel=%s arch=%s USB=%s bound=%u framebuffer=%s draws=%u\r\n",seconds,u.release,u.machine,controller,usb_bound,fb_description,frames);
}
static void tables(int fd) {
 DIR *d=opendir("/sys/firmware/acpi/tables");struct dirent *e;
 dprintf(fd,"ACPI tables:");if(d){while((e=readdir(d)))if(e->d_name[0]!='.')dprintf(fd," %s",e->d_name);closedir(d);}dprintf(fd,"\r\n");
}
static void attribute(int fd,const char *base,const char *name) {
 char path[PATH_MAX],b[2048];snprintf(path,sizeof path,"%s/%s",base,name);
 int f=open(path,O_RDONLY|O_CLOEXEC);if(f<0)return;
 ssize_t n=read(f,b,sizeof b-1);close(f);if(n<=0)return;b[n]=0;
 for(ssize_t i=0;i<n;i++)if(b[i]=='\n'||b[i]=='\r')b[i]=' ';
 dprintf(fd," %s=%s",name,b);
}
static void inventory(int fd) {
 dprintf(fd,"INVENTORY_BEGIN\r\n");
 DIR *d=opendir("/sys/class/block");struct dirent *e;unsigned blocks=0;
 if(d){while((e=readdir(d))){if(e->d_name[0]!='.' && strncmp(e->d_name,"loop",4) && strncmp(e->d_name,"ram",3)){
  char p[PATH_MAX];snprintf(p,sizeof p,"/sys/class/block/%s",e->d_name);
  dprintf(fd,"BLOCK %s",e->d_name);attribute(fd,p,"size");attribute(fd,p,"ro");attribute(fd,p,"partition");attribute(fd,p,"start");attribute(fd,p,"device/type");dprintf(fd,"\r\n");blocks++;
 }}closedir(d);}dprintf(fd,"BLOCK_COUNT %u\r\n",blocks);
 d=opendir("/sys/bus/pci/devices");
 if(d){while((e=readdir(d))){if(e->d_name[0]!='.'){
  char p[PATH_MAX],link[PATH_MAX],target[PATH_MAX];snprintf(p,sizeof p,"/sys/bus/pci/devices/%s",e->d_name);
  dprintf(fd,"PCI %s",e->d_name);attribute(fd,p,"vendor");attribute(fd,p,"device");attribute(fd,p,"class");
  snprintf(link,sizeof link,"/sys/bus/pci/devices/%s/driver",e->d_name);ssize_t n=readlink(link,target,sizeof target-1);
  if(n>0){target[n]=0;char *name=strrchr(target,'/');dprintf(fd," driver=%s",name?name+1:target);}dprintf(fd,"\r\n");
 }}closedir(d);}
 d=opendir("/sys/class/drm");
 if(d){while((e=readdir(d))){if(e->d_name[0]!='.'){
  char p[PATH_MAX];snprintf(p,sizeof p,"/sys/class/drm/%s",e->d_name);dprintf(fd,"DRM %s",e->d_name);attribute(fd,p,"status");attribute(fd,p,"enabled");attribute(fd,p,"modes");dprintf(fd,"\r\n");
 }}closedir(d);}dprintf(fd,"INVENTORY_END\r\n");
}
static int send_all(int fd,const char *b,size_t n) {
 time_t end=time(NULL)+30;size_t off=0;
 while(off<n && time(NULL)<end){
  ssize_t r=write(fd,b+off,n-off>2048?2048:n-off);
  if(r>0){off+=(size_t)r;continue;}
  if(r<0 && errno!=EAGAIN && errno!=EINTR)return -1;
  struct pollfd p={.fd=fd,.events=POLLOUT};poll(&p,1,100);
 }return off==n?0:-1;
}
static void kernel_log(int fd) {
 int capacity=klogctl(10,NULL,0);if(capacity<1 || capacity>2097152)capacity=2097152;
 char *log=malloc((size_t)capacity);if(!log)return;int n=klogctl(3,log,capacity);
 if(n>0){dprintf(fd,"KMSG_BEGIN bytes=%d\r\n",n);send_all(fd,log,(size_t)n);dprintf(fd,"\r\nKMSG_END\r\n");}free(log);
}
static void start_shell(int fd) {
 dprintf(fd,"SHELL_START (exit returns to probe commands)\r\n");
 pid_t p=fork();
 if(p<0){dprintf(fd,"fork failed: %s\r\n",strerror(errno));return;}
 if(p==0){
  setsid();ioctl(fd,TIOCSCTTY,0);
  int flags=fcntl(fd,F_GETFL);if(flags>=0)fcntl(fd,F_SETFL,flags&~O_NONBLOCK);
  struct termios t;if(!tcgetattr(fd,&t)){
   t.c_lflag|=ICANON|ISIG|ECHO;t.c_iflag|=ICRNL;t.c_oflag|=OPOST|ONLCR;
   tcsetattr(fd,TCSANOW,&t);
  }
  dup2(fd,0);dup2(fd,1);dup2(fd,2);if(fd>2)close(fd);
  signal(SIGINT,SIG_DFL);signal(SIGQUIT,SIG_DFL);signal(SIGHUP,SIG_DFL);
  setenv("PATH","/bin:/sbin:/usr/bin:/usr/sbin",1);setenv("HOME","/root",1);setenv("TERM","vt100",1);setenv("PS1","ram-probe# ",1);setenv("HISTFILE","/dev/null",1);
  if(chdir("/tmp")){perror("shell working directory");}
  execl("/bin/busybox","busybox","sh","-i",(char*)NULL);perror("busybox shell");_exit(127);
 }
 shell_pid=p;
}
int main(void) {
 setbuf(stdout,NULL);setbuf(stderr,NULL);
 directory("/dev");directory("/proc");directory("/sys");directory("/tmp");
 mount("devtmpfs","/dev","devtmpfs",0,NULL);
 mount("proc","/proc","proc",MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL);
 mount("sysfs","/sys","sysfs",MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL);
 directory("/dev/pts");mount("devpts","/dev/pts","devpts",MS_NOSUID|MS_NOEXEC,"mode=0620");
 directory("/sys/kernel/debug");mount("debugfs","/sys/kernel/debug","debugfs",0,NULL);
 mount("tmpfs","/tmp","tmpfs",MS_NOSUID|MS_NODEV,"mode=1777");
 int console=open("/dev/console",O_RDWR|O_NOCTTY);
 if(console>=0){dup2(console,0);dup2(console,1);dup2(console,2);if(console>2)close(console);}
 puts("ELK_LINUX_STABLE735_04: RAM-only PID1, no storage mounts");
 usb_setup();start_panel();inventory(STDOUT_FILENO);int serial=-1;char input[128];size_t used=0;
 const char *console_path=getenv("PROBE_TEST_CONSOLE")?"/dev/ttyS0":"/dev/ttyGS0";
 for(seconds=0;;seconds++) {
  if(seconds%3==0)usb_bind();
  framebuffer_status();
  if(panel_pid>0){int st; if(waitpid(panel_pid,&st,WNOHANG)==panel_pid){printf("PANEL: helper status=%d\n",st);panel_pid=0;}}
  if(seconds==0)status(STDOUT_FILENO);
  if(serial<0){serial=open(console_path,O_RDWR|O_NONBLOCK|O_NOCTTY);if(serial>=0){struct termios t;if(!tcgetattr(serial,&t)){cfmakeraw(&t);tcsetattr(serial,TCSANOW,&t);}used=0;}}
  if(shell_pid>0){
   int child_status;pid_t result=waitpid(shell_pid,&child_status,WNOHANG);
   if(result==0){sleep(1);continue;}
   shell_pid=0;close(serial);serial=-1;used=0;
   puts("SHELL_EXIT");sleep(1);continue;
  }
  if(serial>=0){
   if(seconds%3==0)status(serial);
   char c;while(read(serial,&c,1)==1){
    if(c=='\r'||c=='\n'){
     input[used]=0;
     if(!strcmp(input,"status")){status(serial);tables(serial);}
     else if(!strcmp(input,"inventory"))inventory(serial);
     else if(!strcmp(input,"kmsg"))kernel_log(serial);
     else if(!strcmp(input,"shell"))start_shell(serial);
     else if(!strcmp(input,"reboot")){dprintf(serial,"reboot requested\r\n");sleep(1);reboot(RB_AUTOBOOT);}
     else if(used)dprintf(serial,"commands: status inventory kmsg shell reboot\r\n");
     used=0;
     if(shell_pid>0)break;
    }else if(used<sizeof input-1)input[used++]=c;else used=0;
   }
  }
  sleep(1);
 }
}
