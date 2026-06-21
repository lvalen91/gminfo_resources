// entry=0005bd1a name=FUN_0005bd1a size=668
// reasons: ldstr:[SS_SWC] cal_veh_initiated_local_infotainment_ti


/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_0005bd1a(void)

{
  bool bVar1;
  undefined1 uVar2;
  char cVar3;
  undefined2 *puVar4;
  undefined4 uVar5;
  undefined4 uVar6;
  int iVar7;
  undefined2 uStack_24;
  undefined2 uStack_22;
  undefined2 uStack_20;
  undefined1 uStack_1e;
  
  bVar1 = false;
  DAT_febd0e2d = DAT_febd3733;
  DAT_febd0e2e = DAT_febd3732;
  DAT_febd0e2f = DAT_febd3731;
  FUN_0005b962();
  uVar6 = FUN_000e7866(_DAT_febd0d34);
  uVar6 = FUN_000e7ccc(uVar6,0x477fff00);
  _DAT_febd0d2c = FUN_000e7b58(0x3f800000,uVar6);
  cVar3 = DAT_febd3644;
  iVar7 = FUN_0007f82e(0xb0);
  if (iVar7 == 1) {
    if (cVar3 == '\x01') {
      bVar1 = true;
    }
    else {
      iVar7 = FUN_0007633a(0xc);
      bVar1 = iVar7 == 0;
      if (!bVar1) goto LAB_0005bdae;
    }
  }
  else {
LAB_0005bdae:
    if (DAT_febddd41 == '\0') {
      FUN_000e86a6(&uStack_24,0,7);
      DAT_febd0d39 = 0;
      goto LAB_0005bf20;
    }
  }
  cVar3 = DAT_febddd41;
  uVar2 = DAT_febd0d3b;
  if (DAT_febddd41 == '\x02') {
    uStack_24 = FUN_0005ba56(DAT_febd0d3b,0xfebd0dd8,0xfebd0d3c,0x15,bVar1);
    uStack_22 = FUN_0005ba56(uVar2,0xfebd0dfc,0xfebd0d80,0x15,bVar1);
    uStack_20 = FUN_0005ba56(uVar2,0xfebd0df0,0xfebd0d68,0xb,bVar1);
    uStack_1e = 1;
  }
  else {
    uVar6 = 0xfebd0dfc;
    uVar5 = 0xfebd0d80;
    if (bVar1) {
      uVar6 = 0xfebd0e14;
      uVar5 = 0xfebd0dac;
    }
    uVar2 = DAT_febddd40;
    if (_DAT_febd0d30 == 0) {
      uVar2 = DAT_febddd3f;
    }
    uStack_22 = _DAT_febd0d36;
    if (DAT_febd0e30 == '\0') {
      uStack_22 = FUN_0005ba56(DAT_febddd3e,uVar6,uVar5,0x15,bVar1);
    }
    uStack_24 = _DAT_febd0d36;
    if (DAT_febd0e32 == '\0') {
      uStack_24 = FUN_0005ba56(uVar2,0xfebd0dd8,0xfebd0d3c,0x15,bVar1);
    }
    uStack_20 = _DAT_febd0d36;
    if (DAT_febd0e31 == '\0') {
      uStack_20 = FUN_0005ba56(DAT_febddd3f,0xfebd0df0,0xfebd0d68,0xb,bVar1);
    }
    uStack_1e = 1;
    if (cVar3 == DAT_febddd42) {
      FUN_0005bb36(&uStack_24,0xfebddd30);
    }
    puVar4 = &uStack_24;
    FUN_0005bb7c(0xfebddd30,puVar4);
    FUN_0005bba4(puVar4);
  }
LAB_0005bf20:
  DAT_febddd42 = DAT_febddd41;
  DAT_febd3736 = DAT_febd0e2d != '\0';
  if ((bool)DAT_febd3736) {
    uStack_22 = _DAT_febd35f8;
  }
  DAT_febd3735 = DAT_febd0e2e != '\0';
  if ((bool)DAT_febd3735) {
    uStack_20 = _DAT_febd35f6;
  }
  DAT_febd3734 = DAT_febd0e2f != '\0';
  if ((bool)DAT_febd3734) {
    uStack_24 = _DAT_febd35f4;
  }
  _DAT_febd35f0 = uStack_20;
  _DAT_febd35f2 = uStack_22;
  _DAT_febd35ee = uStack_24;
  FUN_0005bcbc(&uStack_24);
  FUN_00089968(&uStack_24);
  return;
}


