#define _GNU_SOURCE
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <poll.h>
#include <sys/ioctl.h>
#include <linux/mei.h>
#include <signal.h>
/* GHS OTA runtime 20d04f(selector2), 20c3e8 raw CRC32C, 20cea5.
 * Selects next boot only. No reset and no storage device access. */
static uint32_t crc32c(const uint8_t *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(int i=0;i<8;i++)c=(c>>1)^((c&1)?0x82f63b78u:0);}return c;}
int main(int argc,char **argv){
 uint8_t b[133]={0x20,7,0,0,1,0x12,0x0e,8,0,0xd0,4,0xe1,2,0,0};uint32_t c=crc32c(b+5,10);for(int i=0;i<4;i++)b[15+i]=(uint8_t)(c>>(8*i));
 if(crc32c((const uint8_t*)"123456789",9)!=0x1cf96d7c)return 2;
 printf("ELK selector=2 frame_bytes=%zu raw_crc32c=%08x\n",sizeof(b),c);fflush(stdout);
 if(argc==2&&!strcmp(argv[1],"--selftest")){puts("CRC32C selftest PASS");return 0;}
 if(argc!=2||strcmp(argv[1],"--select")){fprintf(stderr,"usage: elk-select --selftest | --select\n");return 2;}
 alarm(15);
 int fd=open("/dev/mei0",O_RDWR|O_CLOEXEC);if(fd<0){perror("open mei0");return 1;}
 struct mei_connect_client_data cc={0};const uint8_t id[16]={0x15,0x67,0x6a,0x8e,0xbc,0x9a,0x43,0x40,0x88,0xef,0x9e,0x39,0xc6,0xf6,0x3e,0x0f};memcpy(&cc.in_client_uuid,id,16);
 if(ioctl(fd,IOCTL_MEI_CONNECT_CLIENT,&cc)){perror("MEI connect");close(fd);return 1;}
 printf("MEI connected max_message_length=%u protocol=%u\n",cc.out_client_properties.max_msg_length,cc.out_client_properties.protocol_version);fflush(stdout);
 if(cc.out_client_properties.max_msg_length<sizeof(b)){puts("MEI message limit too small");close(fd);return 1;}
 ssize_t n=write(fd,b,sizeof(b));if(n!=(ssize_t)sizeof(b)){perror("MEI command write");printf("bytes_written=%zd\n",n);close(fd);return 1;}
 struct pollfd p={fd,POLLIN,0};int r=poll(&p,1,8000);if(r<=0||!(p.revents&POLLIN)){printf("MEI reply wait failed result=%d events=%x\n",r,p.revents);close(fd);return 1;}
 uint8_t reply[256];n=read(fd,reply,sizeof(reply));close(fd);alarm(0);
 printf("MEI response_length=%zd",n);if(n>0&&n<=16){printf(" response=");for(ssize_t i=0;i<n;i++)printf("%02x",reply[i]);}puts("");
 if(n!=4||reply[0]!=0x20||reply[1]!=0x87||reply[2]!=0||reply[3]!=0){puts("ELK selection NOT confirmed; no reset performed");return 1;}
 puts("ELK selection accepted by CSE; reset not performed");return 0;
}
