#define _DEFAULT_SOURCE
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <termios.h>
#include <poll.h>
#include <time.h>
#include <string.h>
#include <errno.h>
struct port { int fd; struct termios old; unsigned bytes, good, bad, overflow; uint8_t frame[520]; size_t len; int escape, discard; };
static uint16_t crc(const uint8_t *b,size_t n) { uint16_t c=0xffff; while(n--) { c^=(uint16_t)*b++<<8; for(int i=0;i<8;i++) c=(c&0x8000)?(uint16_t)((c<<1)^0x1021):(uint16_t)(c<<1); } return c; }
static long ms(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t); return t.tv_sec*1000+t.tv_nsec/1000000; }
int main(int argc,char **argv) {
 if((argc!=2 && argc!=3) || atoi(argv[1])<1 || atoi(argv[1])>60 || (argc==3 && strcmp(argv[2],"--reset-uart1"))) {fprintf(stderr,"usage: vip-uart-probe seconds(1..60)\n");return 2;}
 struct port p[4]={0}; struct pollfd f[4];
 for(int i=0;i<4;i++) {char path[32]; snprintf(path,sizeof(path),"/dev/ttyS%d",i); p[i].fd=open(path,O_RDWR|O_NOCTTY|O_NONBLOCK); f[i]=(struct pollfd){.fd=-1,.events=POLLIN}; if(p[i].fd<0) {perror(path);continue;} if(tcgetattr(p[i].fd,&p[i].old)<0){perror("tcgetattr");close(p[i].fd);p[i].fd=-1;continue;} struct termios t=p[i].old;cfmakeraw(&t);t.c_cflag|=CLOCAL|CREAD;t.c_cflag&=~(CRTSCTS|HUPCL);cfsetispeed(&t,B1000000);cfsetospeed(&t,B1000000); if(tcsetattr(p[i].fd,TCSANOW,&t)<0){perror("tcsetattr");close(p[i].fd);p[i].fd=-1;continue;} f[i].fd=p[i].fd; }
 if(argc==3) {
  if(p[1].fd<0) {fprintf(stderr,"UART1 unavailable\n");return 1;}
  uint8_t msg[5]={0,0x8f,5,0,0},wire[16];memset(wire,0x7e,sizeof(wire));uint16_t c=crc(msg,3);msg[3]=c>>8;msg[4]=c;size_t n=1;
  for(size_t k=0;k<5;k++){uint8_t v=msg[k];if(v==0x7e || v==0x7d || v==0x11 || v==0x13){wire[n++]=0x7d;v^=0x20;}wire[n++]=v;}
  ssize_t sent=write(p[1].fd,wire,sizeof(wire));printf("UART1 HDLC reset bytes_sent=%zd\n",sent);
 }
 long end=ms()+atoi(argv[1])*1000;
 while(ms()<end) { int r=poll(f,4,100); if(r<0 && errno!=EINTR){perror("poll");break;} for(int i=0;i<4;i++) if(f[i].revents&POLLIN) {uint8_t b[1024];ssize_t n=read(f[i].fd,b,sizeof(b));if(n<=0)continue;p[i].bytes+=(unsigned)n;for(ssize_t j=0;j<n;j++){uint8_t v=b[j];if(v==0x7e){if(p[i].len && !p[i].discard){if(p[i].len>=4 && !crc(p[i].frame,p[i].len)){p[i].good++;if(p[i].good<=8)printf("ttyS%d valid length=%zu address=%02x control=%02x\n",i,p[i].len,p[i].frame[0],p[i].frame[1]);}else p[i].bad++;} p[i].len=0;p[i].escape=0;p[i].discard=0;continue;}if(p[i].discard)continue;if(p[i].escape){v^=0x20;p[i].escape=0;}else if(v==0x7d){p[i].escape=1;continue;} if(p[i].len==sizeof(p[i].frame)){p[i].discard=1;p[i].overflow++;continue;}p[i].frame[p[i].len++]=v;}}}
 for(int i=0;i<4;i++){if(p[i].fd>=0){tcsetattr(p[i].fd,TCSANOW,&p[i].old);close(p[i].fd);}printf("ttyS%d bytes=%u crc_valid=%u crc_bad=%u overflow=%u\n",i,p[i].bytes,p[i].good,p[i].bad,p[i].overflow);} return 0;
}
