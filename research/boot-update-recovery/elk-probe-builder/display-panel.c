/* Stock Y175 display-link initialization, RAM Linux only.
 * Source: GHS display_i2c + ti949_serdes and successful probe04 live sequence.
 * No brightness change in --init-link; existing panel brightness is retained.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <linux/i2c.h>
#include <linux/i2c-dev.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>
static void guard(int sig) {
 (void)sig;const char msg[]="PANEL: initialization timed out; state unknown\n";
 ssize_t written=write(2,msg,sizeof(msg)-1);(void)written;_exit(3);
}
static int filewrite(const char *p,const char *s) {
 int fd=open(p,O_WRONLY|O_CLOEXEC);if(fd<0)return -1;
 ssize_t n=write(fd,s,strlen(s));int e=errno;close(fd);errno=e;
 return n==(ssize_t)strlen(s)?0:-1;
}
static int fileequals(const char *p,const char *s) {
 char b[128];int fd=open(p,O_RDONLY|O_CLOEXEC);if(fd<0)return 0;
 ssize_t n=read(fd,b,sizeof b-1);close(fd);if(n<0)return 0;b[n]=0;
 b[strcspn(b,"\r\n")]=0;return !strcmp(b,s);
}
static int transfer(int fd,unsigned addr,unsigned char *b,unsigned len) {
 struct i2c_msg m={.addr=addr,.flags=0,.len=len,.buf=b};
 struct i2c_rdwr_ioctl_data t={.msgs=&m,.nmsgs=1};
 int rc=ioctl(fd,I2C_RDWR,&t);if(rc==1)return 0;
 if(rc>=0)errno=EIO;
 fprintf(stderr,"PANEL: address=%02x register=%02x: %s\n",addr,b[0],strerror(errno));return -1;
}
static int regwrite(int fd,unsigned addr,unsigned reg,unsigned value) {
 unsigned char b[]={reg,value};return transfer(fd,addr,b,2);
}
static int regread(int fd,unsigned addr,unsigned reg,unsigned char *value) {
 unsigned char r=reg;
 struct i2c_msg m[2]={{.addr=addr,.flags=0,.len=1,.buf=&r},{.addr=addr,.flags=I2C_M_RD,.len=1,.buf=value}};
 struct i2c_rdwr_ioctl_data t={.msgs=m,.nmsgs=2};int rc=ioctl(fd,I2C_RDWR,&t);
 if(rc==2)return 0;
 if(rc>=0)errno=EIO;
 fprintf(stderr,"PANEL: read address=%02x register=%02x: %s\n",addr,reg,strerror(errno));return -1;
}
static int initlink(void) {
 char path[PATH_MAX],device[64];int found=0;
 /* Match the physical controller, never assume enumeration order. */
 for(int i=0;i<32;i++) {
  char sys[128];snprintf(sys,sizeof sys,"/sys/class/i2c-adapter/i2c-%d/device",i);
  if(realpath(sys,path)&&strstr(path,"/0000:00:17.3/i2c_designware.7")){
   snprintf(device,sizeof device,"/dev/i2c-%d",i);found++;break;
  }
 }
 if(!found){fputs("PANEL: display I2C controller not found\n",stderr);return 1;}
 /* Guard Linux GPIO numbers against changed chip enumeration. */
 if(!fileequals("/sys/class/gpio/gpiochip434/label","INT3452:00") ||
    !fileequals("/sys/class/gpio/gpiochip434/ngpio","78")){
  fputs("PANEL: GPIO bank differs from verified hardware; refusing reset\n",stderr);return 1;
 }
 int fd=open(device,O_RDWR|O_CLOEXEC);if(fd<0){perror("PANEL bus");return 1;}
 if(ioctl(fd,I2C_TIMEOUT,100)<0){perror("PANEL timeout");close(fd);return 1;}
 if(filewrite("/sys/class/gpio/export","467") && errno!=EBUSY){perror("PANEL export");goto fail;}
 /* Writing 'low' selects output with the initial value atomically. */
 if(filewrite("/sys/class/gpio/gpio467/direction","low")){perror("PANEL GPIO low");goto fail;}
 usleep(10000);
 if(filewrite("/sys/class/gpio/gpio467/value","1")){perror("PANEL GPIO high");goto fail;}
 usleep(100000);
 unsigned char state,mode;
 if(regwrite(fd,0x0c,0x16,2)||regread(fd,0x0c,0x5a,&state))goto fail;
 if((state&0x84)==0x84 && regwrite(fd,0x0c,0x5b,(state&0x30)?4:3))goto fail;
 static const unsigned char ser[][2]={{7,0x96},{8,0x96},{0x71,0x50},{0x78,0x50},{3,0xda},{0x0d,0x0f},{0x0e,0x77},{0x72,0x24},{0x79,0x24}};
 static const unsigned char des[][2]={{0x1d,0x23},{0x1e,0x33},{0x21,0x11},{0x26,0x20},{0x27,0x20}};
 for(unsigned i=0;i<sizeof ser/sizeof ser[0];i++)if(regwrite(fd,0x0c,ser[i][0],ser[i][1]))goto fail;
 usleep(10000);
 for(unsigned i=0;i<sizeof des/sizeof des[0];i++)if(regwrite(fd,0x2c,des[i][0],des[i][1]))goto fail;
 /* Early PID1 may precede stable GPU/serializer clocks. Poll without
  * repeatedly resetting the link; preserve the stock readiness gate. */
 for(unsigned attempt=0;attempt<100;attempt++){
  if(regread(fd,0x0c,0x5a,&state))goto fail;
  if((state&0x84)==0x84)break;
  usleep(50000);
 }
 if((state&0x84)!=0x84){fprintf(stderr,"PANEL: link not ready after 5s, status=%02x\n",state);goto fail;}
 if(regwrite(fd,0x0c,0x5b,(state&0x30)?4:3))goto fail;
 if(regread(fd,0x0c,0x5b,&mode)||regwrite(fd,0x0c,0x5b,mode&~0x20))goto fail;
 if(regread(fd,0x2c,0x1c,&mode))goto fail;
 if(regwrite(fd,0x0c,0x1e,2)||regwrite(fd,0x0c,0x20,0x8f)||regwrite(fd,0x0c,0x1e,1))goto fail;
 if(mode&0x20){if(regwrite(fd,0x0c,0x5b,3))goto fail;}
 if(regwrite(fd,0x0c,0xc4,0)||regread(fd,0x0c,0xc7,&mode)||regwrite(fd,0x0c,0xc2,0xaa)||regwrite(fd,0x0c,0xc6,0x41))goto fail;
 if(regread(fd,0x0c,0x5a,&state))goto fail;
 printf("PANEL: stock link initialization complete on %s, status=%02x; fbcon owns video\n",device,state);
 close(fd);return (state&0x84)==0x84?0:1;
fail:close(fd);return 1;
}
int main(int argc,char **argv) {
 signal(SIGALRM,guard);alarm(15);setbuf(stdout,NULL);
 if(argc==2&&!strcmp(argv[1],"--init-link"))return initlink();
 if(argc==2&&!strcmp(argv[1],"--describe")){
  puts("--init-link: guarded stock GPIO/serializer link setup, no panel brightness write.\n--apply-stock-960p: address 0x12, 01 01; wait 300 ms; 20 ff ff.");return 0;
 }
 if(argc!=3||strcmp(argv[1],"--apply-stock-960p")||strncmp(argv[2],"/dev/i2c-",9)){
  fputs("usage: panel-stock --init-link | --describe | --apply-stock-960p /dev/i2c-N\n",stderr);return 2;
 }
 int fd=open(argv[2],O_RDWR|O_CLOEXEC);if(fd<0){perror("open panel bus");return 1;}
 unsigned char reset[]={1,1},brightness[]={0x20,0xff,0xff};
 if(transfer(fd,0x12,reset,2)){close(fd);return 1;}
 usleep(300000);int rc=transfer(fd,0x12,brightness,3);close(fd);
 if(rc)return 1;
 puts("Stock 960p panel sequence acknowledged; visual output still requires verification.");return 0;
}
