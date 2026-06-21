// entry=0005ffcc name=FUN_0005ffcc size=1002
// reasons: ldstr:[SS_SWC] cal_master_offmode_active_timeout_min (


/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_0005ffcc(void)

{
  char cVar1;
  undefined4 uVar2;
  bool bVar3;
  int iVar4;
  char cStack_17;
  char cStack_16;
  byte bStack_15;
  undefined1 auStack_14 [5];
  char cStack_f;
  
  cStack_17 = '\0';
  cStack_16 = '\0';
  bStack_15 = 0;
  iVar4 = FUN_00095a8e(&cStack_17);
  if (iVar4 == 0) {
    if (DAT_febd3a06 == '\0') {
      if ((cStack_17 == '\x02') || (cStack_17 == '\x04')) {
LAB_00060024:
        FUN_000ada1c();
        uVar2 = 1;
LAB_00060042:
        DAT_febd3a06 = cStack_17;
        FUN_0008db7e(uVar2);
      }
    }
    else {
      if (DAT_febd3a06 == '\x01') {
        if ((cStack_17 == '\x02') || (cStack_17 == '\x04')) goto LAB_00060024;
      }
      else if ((DAT_febd3a06 != '\x02') && (DAT_febd3a06 != '\x04')) goto LAB_00060052;
      if (cStack_17 == '\0') {
        FUN_000ae378();
        uVar2 = 0;
        goto LAB_00060042;
      }
    }
  }
LAB_00060052:
  if ((cStack_17 == '\x02') || (cStack_17 == '\x04')) {
    FUN_000d5580(0xb,1);
    _DAT_febd0fd2 = _DAT_febd0fd2 + 1;
    if (_DAT_febd0fd2 < 0x32) {
      uVar2 = 0;
    }
    else {
      _DAT_febd0fd2 = 0x32;
      uVar2 = 1;
    }
  }
  else {
    _DAT_febd0fd2 = 0;
    FUN_000d5580(0xb,0);
    uVar2 = 0;
  }
  FUN_000d5580(1,uVar2);
  if (((cStack_17 == '\x02') || (cStack_17 == '\x04')) || (cStack_17 == '\x01')) {
    FUN_000d5580(0xc,1);
    _DAT_febd0fd4 = _DAT_febd0fd4 + 1;
    if (_DAT_febd0fd4 < 0x32) {
      FUN_000d5580(2,0);
      DAT_febd0ff0 = '\0';
    }
    else {
      _DAT_febd0fd4 = 0x32;
      FUN_000d5580(2,1);
      if (DAT_febd0ff0 == '\0') {
        FUN_000673aa();
        DAT_febd0ff0 = '\x01';
      }
    }
  }
  else {
    _DAT_febd0fd4 = 0;
    FUN_000d5580(0xc,0);
    FUN_000d5580(2,0);
  }
  if (cStack_17 == '\x02') {
    _DAT_febd0fd6 = _DAT_febd0fd6 + 1;
    if (_DAT_febd0fd6 < 0x32) {
      uVar2 = 0;
    }
    else {
      _DAT_febd0fd6 = 0x32;
      uVar2 = 1;
    }
  }
  else {
    _DAT_febd0fd6 = 0;
    uVar2 = 0;
  }
  FUN_000d5580(3,uVar2);
  FUN_000d5580(10,cStack_17 == '\0');
  if (DAT_febd3724 == '\0') {
    FUN_000d5580(0x11,1);
    _DAT_febd0fd0 = _DAT_febd0fd0 + 1;
    if (_DAT_febd0fd0 < 0x32) {
      uVar2 = 0;
    }
    else {
      _DAT_febd0fd0 = 0x32;
      uVar2 = 1;
    }
  }
  else {
    _DAT_febd0fd0 = 0;
    FUN_000d5580(0x11,0);
    uVar2 = 0;
  }
  FUN_000d5580(4,uVar2);
  if (DAT_febd3a16 == '\x03') {
    FUN_000d5580(5,1);
    iVar4 = FUN_00055600(0xbb,&bStack_15,1);
    _DAT_febd0fb4 = (uint)bStack_15;
    if ((iVar4 == 0) && (_DAT_febd0fb4 == 0)) {
      FUN_000d5580(8,1);
    }
    else {
      FUN_000d5580(8,0);
      if (iVar4 != 0) {
        FUN_00084104(1,&DAT_000317dc,iVar4);
      }
    }
  }
  else {
    FUN_000d5580(5,0);
  }
  FUN_00095a44(auStack_14);
  FUN_000d5580(0xf,cStack_f == '\x03');
  FUN_000d5580(0x10,DAT_febd3636 == '\x01');
  FUN_00095958(&cStack_16);
  bVar3 = cStack_16 == '\0';
  if (bVar3) {
    FUN_000d5580(6,0);
  }
  else {
    FUN_000d5580(6,1);
  }
  FUN_000d5580(7,bVar3);
  if (((((DAT_febd36a6 == '\x01') || (DAT_febd36a7 == '\x01')) ||
       ((DAT_febd36ab == '\x01' ||
        (((DAT_febd36ac == '\x01' || (DAT_febd36b5 == '\x01')) || (DAT_febd36b6 == '\x01')))))) ||
      ((DAT_febd36b7 == '\x01' || (DAT_febd36a8 == '\x01')))) ||
     ((DAT_febd36a9 == '\x01' ||
      (((DAT_febd36aa == '\x01' || (DAT_febd36ac == '\x01')) ||
       ((DAT_febd36ae == '\x01' ||
        ((((DAT_febd36af == '\x01' || (DAT_febd36b0 == '\x01')) || (DAT_febd36b1 == '\x01')) ||
         ((DAT_febd36b2 == '\x01' || (DAT_febd36b3 == '\x01')))))))))))) {
    bVar3 = true;
  }
  else {
    bVar3 = DAT_febd36b4 == '\x01';
  }
  FUN_000d5580(9,bVar3);
  cVar1 = DAT_febd371e;
  if (DAT_febd371e == '\0') {
    FUN_000d5580(0xd,1);
  }
  else {
    FUN_000d5580(0xd,0);
  }
  FUN_000d5580(0xe,cVar1 != '\x02');
  FUN_0005fc5c(cStack_16);
  if ((DAT_febd0fe0 == '\0') && (iVar4 = FUN_0005fe3c(), iVar4 == 0)) {
    if ((_DAT_febd0fc0 != 0) &&
       (((_DAT_febd0fc4 != 0 && (_DAT_febd0fc8 != 0)) && (_DAT_febd0fcc != 0)))) {
      DAT_febd0fe0 = '\x01';
      goto LAB_000603ae;
    }
    FUN_000840ac(1,&DAT_000317fc);
  }
  if (DAT_febd0fe0 != '\x01') {
    return;
  }
LAB_000603ae:
  FUN_0005ff08();
  return;
}


