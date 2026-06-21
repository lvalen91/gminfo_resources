// entry=00055600 name=FUN_00055600 size=68
// reasons: callee_of:0005ffcc


void FUN_00055600(undefined2 param_1)

{
  int iVar1;
  undefined1 auStack_90 [124];
  
  FUN_000e8d56(auStack_90,0x1f);
  iVar1 = FUN_000555d0(param_1);
                    /* WARNING: Could not recover jumptable at 0x0005563e. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (*(code *)(iVar1 * 4 + 0x7d0be))();
  return;
}


