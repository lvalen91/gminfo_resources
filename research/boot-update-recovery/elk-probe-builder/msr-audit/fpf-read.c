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
/* Read-only Apollo Lake MCA READ_FILE hardware fuse query, per coreboot cse.c. */
int main(void){
 uint8_t b[77]={0x0a,0x02,0,0};
 memcpy(b+4,"/fpf/intel/SocCfgLock",sizeof("/fpf/intel/SocCfgLock"));
 b[72]=1; b[76]=8; /* one byte, hardware fuse, MCA READ_FILE */
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
 if(n!=9 || reply[0]!=0x0a || reply[1]!=0x82 || reply[2]!=0 || reply[3]!=0 || reply[4]!=1 || reply[5] || reply[6] || reply[7]) {puts("Hardware fuse read NOT confirmed");return 1;}
 printf("SocCfgLock hardware fuse=%u\n",reply[8]);return 0;
}
