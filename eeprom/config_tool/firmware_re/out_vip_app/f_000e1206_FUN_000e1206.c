// entry=000e1206 name=FUN_000e1206 size=70
// reasons: caller_of:000e06be


void FUN_000e1206(void)

{
  uint uVar1;
  
  FUN_000e03f6();
  DAT_febdd6e1 = 0;
  DAT_febd9ae9 = 0;
  uVar1 = (uint)DAT_00047bd6;
  do {
    uVar1 = uVar1 - 1;
    *(undefined1 *)(uVar1 * 3 + -0x1426518) = 0;
  } while (uVar1 != 0);
  DAT_febd9ccf = 0;
  DAT_febd9cd1 = 0;
  DAT_febd9cd0 = 0;
  FUN_000e06be();
  return;
}


