#define _DEFAULT_SOURCE
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <poll.h>
#include <termios.h>
#include <time.h>
#include <signal.h>
/* Y175 IPCServer: CRC 0x1021/init ffff, big endian FCS; escape 7e,7d,11,13.
 * This transport observer deliberately emits no lifecycle/ELK success reply. */
static volatile sig_atomic_t stop;
static int fd=-1;
static uint8_t nr,ns,window=5;
static unsigned good,bad,seen[64],txtries;
static uint8_t pending[520];static size_t plen;static long lasttx;
static uint16_t crc(const uint8_t *p,size_t n){uint16_t c=0xffff;while(n--){c^=(uint16_t)*p++<<8;for(int i=0;i<8;i++)c=(c&0x8000)?(uint16_t)((c<<1)^0x1021):(uint16_t)(c<<1);}return c;}
static long ms(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec*1000+t.tv_nsec/1000000;}
static void sig(int n){(void)n;stop=1;}
static size_t encode(const uint8_t *p,size_t n,uint8_t *w){uint16_t c=crc(p,n);size_t k=0;w[k++]=0x7e;for(size_t i=0;i<n+2;i++){uint8_t b=i<n?p[i]:i==n?(uint8_t)(c>>8):(uint8_t)c;if(b==0x7e||b==0x7d||b==0x11||b==0x13){w[k++]=0x7d;b^=0x20;}w[k++]=b;}w[k++]=0x7e;while(k%16)w[k++]=0x7e;return k;}
static int sendframe(const uint8_t *p,size_t n){uint8_t w[1056];if(n>516)return -1;size_t len=encode(p,n,w),off=0;long deadline=ms()+500;while(off<len&&!stop&&ms()<deadline){ssize_t r=write(fd,w+off,len-off);if(r>0)off+=(size_t)r;else if(r<0&&errno!=EAGAIN&&errno!=EINTR){perror("UART write");return -1;}else{struct pollfd f={fd,POLLOUT,0};poll(&f,1,20);}}if(off!=len){fprintf(stderr,"UART write incomplete\n");return -1;}return 0;}
static void rr(int final){uint8_t b[6]={0,(uint8_t)((nr<<5)|(final?0x11:1)),0xff,0xff,0x1f,0};if(sendframe(b,6))stop=1;}
static void flow(void){if(plen)return;pending[0]=0;pending[1]=(uint8_t)((ns<<1)|0xe0);pending[2]=0;pending[3]=0x10;pending[4]=21;size_t n=5;for(unsigned c=0;c<=20;c++){pending[n++]=(uint8_t)c;pending[n++]=c?0:31;pending[n++]=1;pending[n++]=0;}plen=n;txtries=1;lasttx=ms();if(sendframe(pending,plen))stop=1;puts("TX channel0 protocol10 XON channels0..20");}
static void ack(uint8_t r){if(plen&&r==(ns+1)%window){ns=r;plen=0;puts("TX information frame acknowledged");}}
static void frame(uint8_t *b,size_t n){if(n<4||crc(b,n)){bad++;return;}good++;uint8_t ctrl=b[1];if((ctrl&3)==3){unsigned type=((ctrl>>5)<<2)|((ctrl>>2)&3);if(n!=5){puts("invalid U-frame size");return;}if(b[2]<2||b[2]>8){puts("unsupported window");return;}if(type==12){window=b[2];nr=ns=0;plen=0;printf("RX U-ACK window=%u\n",window);flow();}else if(type==19){window=b[2];nr=ns=0;plen=0;uint8_t a[]={0,0x63,5};if(sendframe(a,3))stop=1;puts("RX U-RESET; TX U-ACK");flow();}return;}
 ack(ctrl>>5);
 if((ctrl&3)==1){if((ctrl&0x0c)==0){if((ctrl&0x10)&&(b[0]&0x40))rr(1);}else if((ctrl&0x0c)==4&&plen){lasttx=0;}return;}
 if(ctrl&1) { return; }
 unsigned seq=(ctrl>>1)&7;if(seq!=nr){rr(0);return;}nr=(uint8_t)((nr+1)%window);rr(0);if(n<5)return;unsigned ch=b[2]&63;seen[ch]++;size_t payload=n-5;if(seen[ch]<=3)printf("RX I ch=%u payload_length=%zu\n",ch,payload);
 if(ch==0&&payload>=2){unsigned count=b[4];if(payload==2+count*4)printf("RX flow version=%02x entries=%u\n",b[3],count);}
 if(payload==1&&b[3]==0xe0)printf("ELK_REQUEST_OBSERVED channel=%u opcode=E0 (no application response sent)\n",ch);
}
int main(int argc,char **argv){if(argc==2&&!strcmp(argv[1],"--selftest")){uint8_t w[1056],f[20]={0,0x8f,5};uint16_t c=crc(f,3);f[3]=c>>8;f[4]=c;if(crc((const uint8_t*)"123456789",9)!=0x29b1||crc(f,5))return 1;size_t n=encode(f,3,w);if(n!=16||w[0]!=0x7e||w[1]!=0||w[2]!=0x8f||w[3]!=5)return 1;f[1]^=1;if(!crc(f,5))return 1;puts("CRC/reset framing/corruption checks PASS");return 0;}
 if(argc!=2||atoi(argv[1])<1||atoi(argv[1])>600){fprintf(stderr,"usage: vip-link seconds(1..600) | --selftest\n");return 2;}
 setvbuf(stdout,NULL,_IOLBF,0);signal(SIGTERM,sig);signal(SIGINT,sig);signal(SIGHUP,sig);
 fd=open("/dev/ttyS1",O_RDWR|O_NOCTTY|O_NONBLOCK);if(fd<0){perror("UART open");return 1;}struct termios old,t;if(tcgetattr(fd,&old)){perror("tcgetattr");close(fd);return 1;}t=old;cfmakeraw(&t);t.c_cflag|=CLOCAL|CREAD;t.c_cflag&=~(CRTSCTS|HUPCL);cfsetispeed(&t,B1000000);cfsetospeed(&t,B1000000);if(tcsetattr(fd,TCSANOW,&t)){perror("tcsetattr");close(fd);return 1;}
 uint8_t reset[]={0,0x8f,5};if(sendframe(reset,3))stop=1;long end=ms()+atoi(argv[1])*1000;uint8_t b[520];size_t used=0;int esc=0,discard=0;
 while(!stop&&ms()<end){struct pollfd p={fd,POLLIN,0};int r=poll(&p,1,20);if(r<0&&errno!=EINTR){perror("poll");break;}if(p.revents&(POLLERR|POLLHUP|POLLNVAL)){puts("UART closed/error");break;}if(p.revents&POLLIN){uint8_t buf[1024];ssize_t n=read(fd,buf,sizeof(buf));if(n<0&&errno!=EAGAIN&&errno!=EINTR){perror("read");break;}for(ssize_t i=0;i<n;i++){uint8_t v=buf[i];if(v==0x7e){if(used&&!discard&&!esc)frame(b,used);used=0;esc=discard=0;continue;}if(discard)continue;if(esc){v^=0x20;esc=0;}else if(v==0x7d){esc=1;continue;}if(used==sizeof(b)){discard=1;bad++;continue;}b[used++]=v;}}
 if(plen&&ms()-lasttx>=100){if(txtries>=5){puts("information-frame ACK timeout; stopping");break;}txtries++;lasttx=ms();if(sendframe(pending,plen))stop=1;}}
 tcsetattr(fd,TCSANOW,&old);close(fd);printf("frames_valid=%u frames_bad=%u\n",good,bad);for(unsigned i=0;i<64;i++)if(seen[i])printf("channel=%u frames=%u\n",i,seen[i]);return good?0:1;}
