// entry=000673aa name=FUN_000673aa size=162
// reasons: callee_of:0005ffcc


void FUN_000673aa(void)

{
  bool bVar1;
  
  bVar1 = true;
  if (((DAT_febd1ae8 == '\0') && (DAT_febd1ae9 == '\0')) && (DAT_febd1aea == '\0')) {
    bVar1 = DAT_febd1aeb != '\0';
  }
  if (DAT_febd1ae8 != '\0') {
    FUN_00084104(0x1b,&DAT_00032fe8);
  }
  if (DAT_febd1ae9 != '\0') {
    FUN_00084104(0x1b,&DAT_00032f4c);
  }
  if (DAT_febd1aea != '\0') {
    FUN_00084104(0x1b,&DAT_00033024);
  }
  if (DAT_febd1aeb != '\0') {
    FUN_00084104(0x1b,&DAT_00032f88);
  }
  if (bVar1) {
    FUN_0006737a();
    return;
  }
  FUN_00084104(0x1b,&DAT_00032fc8);
  return;
}


