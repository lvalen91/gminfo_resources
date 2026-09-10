// tisvcsv4_iface.h  (freestanding — no <windows.h>, no CRT)
// Minimal reconstructed declarations for GM TIS VCS v4 (tisvcsv4.dll), from the RE'd exports in
//   gm_dps/disassembly/pseudocode/tisvcsv4.dll.pseudocode.txt
// Each method's EXACT decorated (32-bit MSVC) export name is in a comment; the linker resolves
// them against the import lib generated from tisvcsv4.dll (see build_clang.bat). Build **x86**
// (tisvcsv4.dll is 32-bit __thiscall). clang target: i686-pc-windows-msvc (MS C++ ABI).
#pragma once

// eProtocol is nested in IVcsUI  (mangling: W4eProtocol@IVcsUI@@).
class IVcsUI {
public:
    enum eProtocol {
        eProto_Unknown = 0,
        eProto_GMLAN   = 1,
        eProto_HSCAN   = 2,
        eProto_UDS_CAN = 3,   // best guess for the VIP UDS/CAN path used by ECU 0x80; VERIFY
        eProto_DoIP    = 4
    };
    virtual ~IVcsUI() {}
};

// eRetCodeEve is nested in ISpsEvent  (mangling: W4eRetCodeEve@ISpsEvent@@).
class ISpsEvent {
public:
    enum eRetCodeEve { eEve_OK = 0 };
};

class CServiceCollection;   // opaque

// COM-style UDS "expert" interface. Methods are vtable-dispatched (NOT name-exported). The order
// below is a best-effort reconstruction and is the ONE thing to verify on the box (README §5):
//   llvm-objdump / the ISerUdsExp2 vftable in tisvcsv4 pseudocode (~line 97534).
struct ISerUdsExp2 {
    struct VTable {
        int (__thiscall *ReadDataByIdentifier)(void* self, unsigned short did);          // VERIFY
        int (__thiscall *Execute)(void* self);                                           // VERIFY
        int (__thiscall *GetResponse)(void* self, unsigned char* buf, int cap,
                                      unsigned char* nrcOut);                            // VERIFY
    };
    VTable* vptr;
};

// The CServiceCollection returned by BuildRequestedService exposes this interface directly
// (GM pattern: the collection IS-A CServiceInterface at offset 0). We reinterpret_cast the
// collection to CServiceInterface* and call GetInterface — no constructor is exported/needed.
class CServiceInterface {
public:
    // ?GetInterface@CServiceInterface@@QAE_NAAPAUISerUdsExp2@@@Z
    bool GetInterface(ISerUdsExp2*& out);
};

// CBuildService — all three below are name-exported and link cleanly.
class CBuildService {
public:
    CBuildService(IVcsUI& ui);                     // ??0CBuildService@@QAE@AAVIVcsUI@@@Z
    ~CBuildService();                              // ??1CBuildService@@QAE@XZ
    void SetInitToType4Mode();                     // ?SetInitToType4Mode@CBuildService@@QAEXXZ
    // ?BuildRequestedService@CBuildService@@QAEPAVCServiceCollection@@W4eProtocol@IVcsUI@@GAAW4eRetCodeEve@ISpsEvent@@@Z
    CServiceCollection* BuildRequestedService(IVcsUI::eProtocol proto,
                                              unsigned short serviceId,
                                              ISpsEvent::eRetCodeEve& rc);
private:
    void*   m_vtbl;
    void*   m_pad;
    IVcsUI* m_pUI;   // this+0xC (ctor stores the IVcsUI here)
};

static const unsigned short SID_ReadDataByIdentifier = 0x0022;  // UDS $22; VERIFY selector
