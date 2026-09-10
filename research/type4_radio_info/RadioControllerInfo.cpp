// RadioControllerInfo.cpp  (freestanding: no CRT, no <windows.h>, no STL)
// GM DPS Type4 app — "Read Radio Controller Info": reads the A11 Radio / CSM (ECU 0x80) DID set
// from dps_readx80.Txt and returns the formatted report. READ-ONLY (no $27, no writes/reset).
//
// Host contract (dpsvcs.dll): DPS LoadLibrary()s %USERPROFILE%\sps\type4\Type4App.dll,
// GetProcAddress("Launch"), calls  int Launch(void* pVcsUI, void* pCtx).  0 = success.
// Built x86 with clang (i686-pc-windows-msvc) + lld, freestanding — see build_clang.bat.

#include "tisvcsv4_iface.h"

// ---- freestanding runtime shims (clang may emit these; provide our own) ----
extern "C" void* memset(void* d, int c, __SIZE_TYPE__ n){ unsigned char* p=(unsigned char*)d; while(n--) *p++=(unsigned char)c; return d; }
extern "C" void* memcpy(void* d, const void* s, __SIZE_TYPE__ n){ unsigned char* a=(unsigned char*)d; const unsigned char* b=(const unsigned char*)s; while(n--) *a++=*b++; return d; }
extern "C" void* memmove(void* d, const void* s, __SIZE_TYPE__ n){ unsigned char* a=(unsigned char*)d; const unsigned char* b=(const unsigned char*)s; if(a<b){while(n--)*a++=*b++;}else{a+=n;b+=n;while(n--)*--a=*--b;} return d; }
// DLL entry with no CRT startup. lld default DLL entry is _DllMainCRTStartup.
extern "C" int __stdcall _DllMainCRTStartup(void*, unsigned, void*){ return 1; }
static void spin(unsigned loops){ volatile unsigned x=0; for(unsigned i=0;i<loops;i++) x+=i; } // crude delay (no Sleep w/o SDK)

// Must match <Action Id="..."> in 10018101.cfx
static const int kActionReadRadioInfo = 2200;

// ---- output buffer (fixed; no std::string) ----
static char g_out[16384];
static int  g_len = 0;
static void put(const char* s){ while(*s && g_len<(int)sizeof(g_out)-1) g_out[g_len++]=*s++; }
static void putc1(char c){ if(g_len<(int)sizeof(g_out)-1) g_out[g_len++]=c; }
static void nl(){ put("\r\n"); }
static void putU(unsigned v){ char t[12]; int i=0; if(!v){putc1('0');return;} while(v){t[i++]=(char)('0'+v%10);v/=10;} while(i)putc1(t[--i]); }
static void putHexByte(unsigned char b){ static const char* H="0123456789ABCDEF"; putc1(H[b>>4]); putc1(H[b&15]); }
static void putHexSp(const unsigned char* p,int n){ for(int i=0;i<n;i++){ putHexByte(p[i]); if(i+1<n) putc1(' '); } }
static void putHex4(unsigned short v){ putHexByte((unsigned char)(v>>8)); putHexByte((unsigned char)v); }
static void putPad(const char* s,int w){ int n=0; while(s[n])n++; put(s); for(int i=n;i<w;i++) putc1(' '); }

// ---- DID table (exact order DPS issued to ECU 0x80; dps_readx80.Txt) ----
enum Kind { ASCII, BCDDATE, U8, HEXDUMP, MODTABLE, SKIP_IF_NRC };
struct DidSpec { unsigned short did; const char* label; Kind kind; };
static const DidSpec kDids[] = {
    { 0xF190, "VIN",                     ASCII    },
    { 0xF1CB, "End Model Number",        HEXDUMP  },
    { 0xF1CC, "Base Model Number",       HEXDUMP  },
    { 0xF180, "Boot SW Module IDs",      MODTABLE },
    { 0xF181, "App SW Module IDs",       MODTABLE },
    { 0xF182, "Cal Module ID table",     MODTABLE },
    { 0xF197, "System Name/Engine",      SKIP_IF_NRC },
    { 0xF198, "Repair Shop Code / SN",   ASCII    },
    { 0xF199, "Programming Date",        BCDDATE  },
    { 0xF09A, "(F09A)",                  SKIP_IF_NRC },
    { 0xF1A0, "Manufacturers Enable Ctr",U8       },
    { 0xF0F0, "PSI",                     HEXDUMP  },
    { 0xF0F1, "PEC",                     HEXDUMP  },
    { 0xF0F2, "BIS",                     HEXDUMP  },
    { 0xF0F3, "ECUID",                   HEXDUMP  },
    { 0xE0B2, "(E0B2)",                  SKIP_IF_NRC },
    { 0xF0F4, "(F0F4)",                  SKIP_IF_NRC },
    { 0xF0F8, "(F0F8)",                  SKIP_IF_NRC },
    { 0xE0B5, "(E0B5)",                  SKIP_IF_NRC },
    { 0xF0B4, "Mfg Traceability Chars",  ASCII    },
    { 0xF0AB, "CVPPS",                   ASCII    },
    { 0xF0B3, "DUNS Identification",     ASCII    },
    { 0xF081, "MAC Configuration Data",  HEXDUMP  },
};

static void emitValue(Kind k, const unsigned char* d, int n){
    switch(k){
    case ASCII:   { int e=n; while(e>0 && (d[e-1]==0||d[e-1]==' ')) e--; for(int i=0;i<e;i++) putc1((char)d[i]); break; }
    case U8:      putU(n?d[0]:0); break;
    case BCDDATE: if(n>=4){ putHexByte(d[0]); putHexByte(d[1]); putc1('-'); putHexByte(d[2]); putc1('-'); putHexByte(d[3]); } else { putc1('$'); putHexSp(d,n);} break;
    case HEXDUMP: putc1('$'); putHexSp(d,n); break;
    case MODTABLE:{
        if(n<1){ putc1('$'); putHexSp(d,n); break; }
        int cnt=d[0]; const unsigned char* p=d+1; int rem=n-1;
        for(int i=0;i<cnt && rem>=7;i++,p+=7,rem-=7){
            unsigned id=((unsigned)p[1]<<24)|((unsigned)p[2]<<16)|((unsigned)p[3]<<8)|p[4];
            put("\r\n    "); putHexByte(p[0]); put("  "); putU(id); put("  "); putc1((char)p[5]); putc1((char)p[6]);
        }
        break; }
    default: putc1('$'); putHexSp(d,n); break;
    }
}

// Read one DID; loops on responsePending ($78). Returns bytes (>=0) or -(nrc).
static int readDid(ISerUdsExp2* uds, unsigned short did, unsigned char* out, int cap, unsigned char* nrc){
    for(int a=0;a<40;a++){
        uds->vptr->ReadDataByIdentifier(uds, did);   // VERIFY vtable
        uds->vptr->Execute(uds);                      // VERIFY vtable
        *nrc=0;
        int n=uds->vptr->GetResponse(uds, out, cap, nrc);   // VERIFY vtable
        if(n>=0) return n;
        if(*nrc==0x78){ spin(30000000); continue; }   // responsePending -> wait, retry
        return -(int)*nrc;
    }
    return -0x78;
}

extern "C" __declspec(dllexport)
int Launch(void* pVcsUI, void* /*pCtx*/){
    g_len=0;
    if(!pVcsUI){ put("Error: no VCS UI interface"); nl(); return 1; }

    IVcsUI& ui = *(IVcsUI*)pVcsUI;
    CBuildService svc(ui);
    svc.SetInitToType4Mode();

    IVcsUI::eProtocol proto = IVcsUI::eProto_UDS_CAN;   // VERIFY for this vehicle's radio link
    ISpsEvent::eRetCodeEve rc = ISpsEvent::eEve_OK;
    CServiceCollection* coll = svc.BuildRequestedService(proto, SID_ReadDataByIdentifier, rc);
    if(!coll || rc!=ISpsEvent::eEve_OK){ put("Error: BuildRequestedService failed"); nl(); return 2; }

    CServiceInterface* si = (CServiceInterface*)coll;   // collection IS-A CServiceInterface
    ISerUdsExp2* uds=0;
    if(!si->GetInterface(uds) || !uds){ put("Error: GetInterface(ISerUdsExp2) failed"); nl(); return 3; }

    put("================================================================"); nl();
    put("  A11 Radio / CSM (ECU $80) - Controller Info"); nl();
    put("================================================================"); nl();

    unsigned char buf[512], nrc;
    for(unsigned i=0;i<sizeof(kDids)/sizeof(kDids[0]);i++){
        const DidSpec& s=kDids[i];
        int n=readDid(uds,s.did,buf,sizeof buf,&nrc);
        if(n<0){
            if(s.kind==SKIP_IF_NRC) continue;
            put("  "); putPad(s.label,26); put(" $"); putHex4(s.did); put(" : (not available, NRC $"); putHexByte((unsigned char)(-n)); put(")"); nl();
            continue;
        }
        put("  "); putPad(s.label,26); put(" $"); putHex4(s.did); put(" : "); emitValue(s.kind,buf,n); nl();
    }
    put("================================================================"); nl();
    return 0;
}

extern "C" __declspec(dllexport)
int GetResult(char* dst, int cap){
    int n=g_len; if(n>cap-1) n=cap-1;
    if(dst && cap>0){ for(int i=0;i<n;i++) dst[i]=g_out[i]; dst[n]=0; }
    return n;
}

extern "C" __declspec(dllexport) int SetInternal(void*){ return 0; }
extern "C" __declspec(dllexport) int CMessage(int, void*){ return 0; }
