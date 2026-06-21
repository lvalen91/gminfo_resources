// entry=000aa03a name=FUN_000aa03a size=110
// reasons: callee_of:000aa0a8


/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_000aa03a(char param_1)

{
  bool bVar1;
  uint uVar2;
  uint uVar3;
  
  if (param_1 == '\x01') {
    uVar3 = (uint)_DAT_febd4c08;
    DAT_febd3793 = '\0';
    DAT_febd3796 = '\x01';
    DAT_febd3794 = DAT_febd3793;
    if (uVar3 != 0) {
      if (uVar3 < 0x3e9) {
        DAT_febd3796 = (char)(uVar3 / 500);
        DAT_febd3793 = '\0';
        DAT_febd3794 = DAT_febd3793;
        if (uVar3 % 500 != 0) {
          DAT_febd3796 = DAT_febd3796 + '\x01';
        }
      }
      else {
        uVar2 = uVar3 / 1000;
        DAT_febd3796 = '\x02';
        if (uVar3 % 1000 == 0) {
          bVar1 = 0xff < uVar2;
          if (!bVar1) {
            DAT_febd3793 = (char)uVar2 + -1;
            DAT_febd3794 = DAT_febd3793;
            DAT_febd3796 = 2;
            return;
          }
        }
        else {
          bVar1 = 0xfe < uVar2;
        }
        DAT_febd3793 = (char)uVar2 * !bVar1 - bVar1;
        DAT_febd3794 = DAT_febd3793;
      }
    }
  }
  return;
}


