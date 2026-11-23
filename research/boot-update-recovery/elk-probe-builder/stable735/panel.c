/* Stock Y175 display-link initialization, RAM Linux only.
 * Source: GHS display_i2c + ti949_serdes and successful probe04 live sequence.
 * No brightness change in --init-link; existing panel brightness is retained.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <dirent.h>
#include <linux/gpio.h>
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
/* Select the verified ACPI bank and line, never a global GPIO number. */
static int reset_line(void) {
 DIR *dir=opendir("/dev");if(!dir){perror("PANEL /dev");return -1;}
 struct dirent *e;int selected=-1,matches=0;
 while((e=readdir(dir))){
  if(strncmp(e->d_name,"gpiochip",8))continue;
  char path[PATH_MAX];snprintf(path,sizeof path,"/dev/%s",e->d_name);
  int fd=open(path,O_RDONLY|O_CLOEXEC);if(fd<0)continue;
  struct gpiochip_info info={0};
  if(!ioctl(fd,GPIO_GET_CHIPINFO_IOCTL,&info) && !strcmp(info.label,"INT3452:00") && info.lines==78){
   matches++;if(selected<0)selected=fd;else close(fd);
  }else close(fd);
 }
 closedir(dir);
 if(matches!=1){if(selected>=0)close(selected);fputs("PANEL: expected exactly one INT3452:00 bank with 78 lines\n",stderr);return -1;}
 struct gpio_v2_line_info info={.offset=33};
 if(ioctl(selected,GPIO_V2_GET_LINEINFO_IOCTL,&info)){
  perror("PANEL line information");close(selected);return -1;
 }
 int identity_ok=!strcmp(info.name,"GPIO_33");
 if(!info.name[0]){
  FILE *pins=fopen("/sys/kernel/debug/pinctrl/INT3452:00/pins","r");
  if(pins){char line[512];while(fgets(line,sizeof line,pins)){
   if(!strncmp(line,"pin 33 (GPIO_33) ",16)){identity_ok=1;break;}
  }fclose(pins);}
 }
 if(!identity_ok){fputs("PANEL: reset pin identity not verified\n",stderr);close(selected);return -1;}

 struct gpio_v2_line_request req={0};
 req.offsets[0]=33;req.num_lines=1;strcpy(req.consumer,"probe-panel-reset");
 req.config.flags=GPIO_V2_LINE_FLAG_OUTPUT;
 req.config.num_attrs=1;
 req.config.attrs[0].attr.id=GPIO_V2_LINE_ATTR_ID_OUTPUT_VALUES;
 req.config.attrs[0].attr.values=0;req.config.attrs[0].mask=1;
 if(ioctl(selected,GPIO_V2_GET_LINE_IOCTL,&req)){perror("PANEL request reset");close(selected);return -1;}
 close(selected);usleep(10000);
 struct gpio_v2_line_values high={.bits=1,.mask=1};
 if(ioctl(req.fd,GPIO_V2_LINE_SET_VALUES_IOCTL,&high)){perror("PANEL reset high");close(req.fd);return -1;}
 usleep(100000);return req.fd;
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
  char sys[128];snprintf(sys,sizeof sys,"/sys/bus/i2c/devices/i2c-%d",i);
  if(realpath(sys,path)&&strstr(path,"/0000:00:17.3/")){
   snprintf(device,sizeof device,"/dev/i2c-%d",i);found++;
  }
 }
 if(found!=1){fputs("PANEL: display I2C controller missing or ambiguous\n",stderr);return 1;}
 int fd=open(device,O_RDWR|O_CLOEXEC);if(fd<0){perror("PANEL bus");return 1;}
 if(ioctl(fd,I2C_TIMEOUT,100)<0){perror("PANEL timeout");close(fd);return 1;}
 int gpio_fd=reset_line();if(gpio_fd<0){close(fd);return 1;}
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
 close(fd);
 if((state&0x84)!=0x84){close(gpio_fd);return 1;}
 /* GPIO-v2 guarantees the requested level only while the request is held.
  * Stay resident so panel reset remains deasserted until this helper stops. */
 alarm(0);puts("PANEL: retaining GPIO-v2 reset-line ownership");
 for(;;)pause();
fail:close(gpio_fd);close(fd);return 1;
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
