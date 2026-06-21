// entry=000b7c48 name=FUN_000b7c48 size=70
// reasons: callee_of:000b7c8e


void FUN_000b7c48(byte param_1,undefined1 param_2)

{
  undefined1 uVar1;
  
  if (param_1 < 2) {
    if (param_1 != 0) {
      DAT_febd3901 = param_2;
      return;
    }
    DAT_febd38f6 = param_2;
    return;
  }
  if (param_1 < 3) {
    DAT_febd39f0 = param_2;
    return;
  }
  uVar1 = param_2;
  if ((param_1 != 3) && (uVar1 = DAT_febd39f6, param_1 == 4)) {
    DAT_febd39ce = param_2;
    return;
  }
  DAT_febd39f6 = uVar1;
  return;
}


