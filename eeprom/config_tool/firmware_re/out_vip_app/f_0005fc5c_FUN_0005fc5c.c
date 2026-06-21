// entry=0005fc5c name=FUN_0005fc5c size=86
// reasons: callee_of:0005ffcc


void FUN_0005fc5c(char param_1)

{
  int iVar1;
  char cStack_d;
  
  cStack_d = '\0';
  FUN_0005722a(&cStack_d);
  if (cStack_d != '\0') {
    if (param_1 == '\0') {
      FUN_000571f6();
    }
    else {
      param_1 = -1;
    }
  }
  if (((DAT_febd0fee == '\0') || (DAT_febd0fef != param_1)) &&
     (iVar1 = FUN_0005c752(param_1), iVar1 == 0)) {
    DAT_febd0fee = '\x01';
    DAT_febd0fef = param_1;
  }
  return;
}


