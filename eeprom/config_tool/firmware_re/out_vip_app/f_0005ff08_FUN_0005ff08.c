// entry=0005ff08 name=FUN_0005ff08 size=196
// reasons: callee_of:0005ffcc


/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_0005ff08(void)

{
  int iVar1;
  uint uVar2;
  ushort uStack_e;
  
  uStack_e = 0;
  FUN_0006729a(&uStack_e);
  uVar2 = (uint)uStack_e;
  if ((_DAT_febd0fb8 < uVar2) && (iVar1 = FUN_0005e0e4(0x91), iVar1 != 0)) {
    if (_DAT_febd0fd8 < _DAT_febd0fc0) {
      _DAT_febd0fd8 = _DAT_febd0fd8 + 1;
    }
    _DAT_febd0fda = 0;
    _DAT_febd0fdc = 0;
    _DAT_febd0fde = 0;
  }
  else {
    if (_DAT_febd0fda < _DAT_febd0fc4) {
      _DAT_febd0fda = _DAT_febd0fda + 1;
    }
    _DAT_febd0fd8 = 0;
    if (((uVar2 < _DAT_febd0fbc) && (_DAT_febd0ff4 == 1)) &&
       (iVar1 = FUN_0005e0e4(0x92), iVar1 != 0)) {
      if (_DAT_febd0fdc < _DAT_febd0fc8) {
        _DAT_febd0fdc = _DAT_febd0fdc + 1;
      }
      _DAT_febd0fde = 0;
    }
    else {
      if (_DAT_febd0fde < _DAT_febd0fcc) {
        _DAT_febd0fde = _DAT_febd0fde + 1;
      }
      _DAT_febd0fdc = 0;
    }
  }
  iVar1 = FUN_0005fe7e();
  if (iVar1 == 1) {
    FUN_00067298();
  }
  return;
}


