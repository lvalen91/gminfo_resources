// entry=00084104 name=FUN_00084104 size=88
// reasons: callee_of:0005ffcc


void FUN_00084104(undefined4 param_1,undefined4 param_2)

{
  uint uVar1;
  int iVar2;
  undefined4 uVar3;
  
  uVar1 = FUN_00084060();
  if (((uVar1 & 2) != 0) && (iVar2 = FUN_000ecd84(0xc), iVar2 == 0)) {
    uVar3 = FUN_0008408e();
    FUN_000846e6(&DAT_00043b28,uVar3);
    FUN_000846ba(param_2);
    FUN_000ecdac(0xc);
  }
  return;
}


