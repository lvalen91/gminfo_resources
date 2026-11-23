#define _GNU_SOURCE
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES2/gl2.h>
#include <gbm.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
static void die(const char *what){fprintf(stderr,"FAIL: %s EGL=%x GL=%x\n",what,eglGetError(),glGetError());exit(1);}
static GLuint shader(GLenum type,const char *src){
 GLuint s=glCreateShader(type);glShaderSource(s,1,&src,NULL);glCompileShader(s);GLint ok=0;glGetShaderiv(s,GL_COMPILE_STATUS,&ok);
 if(!ok){char log[2048];glGetShaderInfoLog(s,sizeof log,NULL,log);fprintf(stderr,"%s\n",log);die("shader compilation");}return s;
}
int main(void){
 int fd=open("/dev/dri/renderD128",O_RDWR|O_CLOEXEC);if(fd<0){perror("render node");return 1;}
 struct gbm_device *gbm=gbm_create_device(fd);if(!gbm)die("GBM device");
 PFNEGLGETPLATFORMDISPLAYEXTPROC getdisplay=(void*)eglGetProcAddress("eglGetPlatformDisplayEXT");if(!getdisplay)die("platform display extension");
 EGLDisplay d=getdisplay(EGL_PLATFORM_GBM_KHR,gbm,NULL);EGLint major,minor;
 if(!eglInitialize(d,&major,&minor)||!eglBindAPI(EGL_OPENGL_ES_API))die("EGL initialization");
 const EGLint attrs[]={EGL_RENDERABLE_TYPE,EGL_OPENGL_ES2_BIT,EGL_SURFACE_TYPE,EGL_WINDOW_BIT,EGL_RED_SIZE,8,EGL_GREEN_SIZE,8,EGL_BLUE_SIZE,8,EGL_NONE};
 EGLConfig cfg;EGLint count;if(!eglChooseConfig(d,attrs,&cfg,1,&count)||count!=1)die("EGL config");
 const EGLint ca[]={EGL_CONTEXT_CLIENT_VERSION,2,EGL_NONE};EGLContext ctx=eglCreateContext(d,cfg,EGL_NO_CONTEXT,ca);
 if(ctx==EGL_NO_CONTEXT||!eglMakeCurrent(d,EGL_NO_SURFACE,EGL_NO_SURFACE,ctx))die("surfaceless context");
 const char *renderer=(const char*)glGetString(GL_RENDERER);if(!renderer)die("renderer");
 printf("EGL=%d.%d\nGL_VENDOR=%s\nGL_RENDERER=%s\nGL_VERSION=%s\n",major,minor,glGetString(GL_VENDOR),renderer,glGetString(GL_VERSION));
 if(strcasestr(renderer,"llvmpipe")||strcasestr(renderer,"softpipe")||strcasestr(renderer,"swrast"))die("software renderer rejected");
 GLuint tex,fbo;glGenTextures(1,&tex);glBindTexture(GL_TEXTURE_2D,tex);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,256,256,0,GL_RGBA,GL_UNSIGNED_BYTE,NULL);
 glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
 glGenFramebuffers(1,&fbo);glBindFramebuffer(GL_FRAMEBUFFER,fbo);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,tex,0);
 if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)die("FBO");
 GLuint vs=shader(GL_VERTEX_SHADER,"attribute vec2 p; void main(){gl_Position=vec4(p,0.0,1.0);}");
 GLuint fs=shader(GL_FRAGMENT_SHADER,"precision highp float; void main(){gl_FragColor=vec4(gl_FragCoord.x/256.0,gl_FragCoord.y/256.0,0.25,1.0);}");
 GLuint prog=glCreateProgram();glAttachShader(prog,vs);glAttachShader(prog,fs);glBindAttribLocation(prog,0,"p");glLinkProgram(prog);
 GLint ok;glGetProgramiv(prog,GL_LINK_STATUS,&ok);if(!ok)die("program link");glUseProgram(prog);
 const GLfloat vertices[]={-1,-1,3,-1,-1,3};GLuint vbo;glGenBuffers(1,&vbo);glBindBuffer(GL_ARRAY_BUFFER,vbo);glBufferData(GL_ARRAY_BUFFER,sizeof vertices,vertices,GL_STATIC_DRAW);
 glVertexAttribPointer(0,2,GL_FLOAT,GL_FALSE,0,NULL);glEnableVertexAttribArray(0);glViewport(0,0,256,256);glDisable(GL_DITHER);
 for(int n=0;n<256;n++){glDrawArrays(GL_TRIANGLES,0,3);if((n&31)==31)glFinish();}
 unsigned char pix[4];glReadPixels(64,192,1,1,GL_RGBA,GL_UNSIGNED_BYTE,pix);glFinish();
 printf("PIXEL_RGBA=%u,%u,%u,%u expected=64,192,64,255 tolerance=1\n",pix[0],pix[1],pix[2],pix[3]);
 if(abs((int)pix[0]-64)>1||abs((int)pix[1]-192)>1||abs((int)pix[2]-64)>1||pix[3]!=255||glGetError()!=GL_NO_ERROR)die("rendered pixel mismatch");
 puts("GPU_SHADER_RENDER_PASS (256 draws; render node; no display modeset)");
 glDeleteBuffers(1,&vbo);glDeleteProgram(prog);glDeleteShader(vs);glDeleteShader(fs);glDeleteFramebuffers(1,&fbo);glDeleteTextures(1,&tex);
 eglMakeCurrent(d,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);eglDestroyContext(d,ctx);eglTerminate(d);gbm_device_destroy(gbm);close(fd);return 0;
}
