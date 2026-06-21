// entry=000afc6a name=FUN_000afc6a size=420
// reasons: caller_of:0008fa54


/* WARNING: Control flow encountered bad instruction data */

void FUN_000afc6a(void)

{
  int iVar1;
  undefined1 uStack_2a;
  undefined1 local_29;
  undefined1 uStack_28;
  undefined1 uStack_27;
  undefined1 uStack_26;
  undefined1 uStack_25;
  undefined1 uStack_24;
  undefined1 uStack_23;
  undefined1 uStack_22;
  undefined1 uStack_21;
  undefined1 uStack_20;
  undefined1 uStack_1f;
  undefined1 uStack_1e;
  undefined1 auStack_1d [21];
  
  FUN_000afa10();
  FUN_000afa14();
  iVar1 = FUN_0008ff0a();
  if (iVar1 == 1) {
    DAT_febe7206 = DAT_febe7206 | 1;
  }
  FUN_0008fb98(&uStack_2a);
  iVar1 = FUN_0008fed6();
  if (iVar1 == 1) {
    DAT_febe7206 = DAT_febe7206 | 2;
  }
  FUN_0008fb2c(&local_29);
  iVar1 = FUN_0008fe8a();
  if (iVar1 == 1) {
    DAT_febe7206 = DAT_febe7206 | 4;
  }
  FUN_0008fa8a(&uStack_28);
  iVar1 = FUN_0008fe3e();
  if (iVar1 == 1) {
    DAT_febe7206 = DAT_febe7206 | 8;
  }
  FUN_0008f9e8(&uStack_27);
  iVar1 = FUN_0008ff22();
  if (iVar1 == 1) {
    DAT_febe7206 = DAT_febe7206 | 0x10;
  }
  FUN_0008fbce(&uStack_26);
  iVar1 = FUN_0008fe56();
  if (iVar1 == 1) {
    DAT_febe7206 = DAT_febe7206 | 0x20;
  }
  FUN_0008fa1e(&uStack_25);
  iVar1 = FUN_0008fef0();
  if (iVar1 == 1) {
    DAT_febe7206 = DAT_febe7206 | 0x40;
  }
  FUN_0008fb62(&uStack_24);
  iVar1 = FUN_0008fe0a();
  if (iVar1 == 1) {
    DAT_febe7206 = DAT_febe7206 | 0x80;
  }
  FUN_0008f97c(&uStack_23);
  iVar1 = FUN_0008fe24();
  if (iVar1 == 1) {
    DAT_febe7207 = DAT_febe7207 | 1;
  }
  FUN_0008f9b2(&uStack_22);
  iVar1 = FUN_0008fea4();
  if (iVar1 == 1) {
    DAT_febe7207 = DAT_febe7207 | 2;
  }
  FUN_0008fac0(&uStack_21);
  iVar1 = FUN_0008fe70();
  if (iVar1 == 1) {
    DAT_febe7207 = DAT_febe7207 | 4;
  }
  FUN_0008fa54(&uStack_20);
  iVar1 = FUN_0008ff56();
  if (iVar1 == 1) {
    DAT_febe7207 = DAT_febe7207 | 8;
  }
  FUN_0008fc3a(&uStack_1f);
  iVar1 = FUN_0008febc();
  if (iVar1 == 1) {
    DAT_febe7207 = DAT_febe7207 | 0x10;
  }
  FUN_0008faf6(&uStack_1e);
  iVar1 = FUN_0008ff3c();
  if (iVar1 == 1) {
    DAT_febe7207 = DAT_febe7207 | 0x20;
  }
  FUN_0008fc04(auStack_1d);
  DAT_febe7205 = 0;
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}


