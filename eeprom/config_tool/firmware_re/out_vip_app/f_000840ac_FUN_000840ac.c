// entry=000840ac name=FUN_000840ac size=88
// reasons: callee_of:0005ffcc


void FUN_000840ac(undefined4 param_1,undefined4 param_2)

{
  uint uVar1;
  int iVar2;
  undefined4 uVar3;
  
  uVar1 = FUN_00084060();
  if (((uVar1 & 1) != 0) && (iVar2 = FUN_000ecd84(0xc), iVar2 == 0)) {
    uVar3 = FUN_0008408e();
    FUN_000846e6(&DAT_00043b1c,uVar3);
    FUN_000846ba(param_2);
    FUN_000ecdac(0xc);
  }
  return;
}


