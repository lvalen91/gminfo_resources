// entry=000c099c name=FUN_000c099c size=106
// reasons: ldstr:[SS_SWC] cal_local_valet_timeout_sec (%d) read o


undefined4 FUN_000c099c(byte param_1)

{
  bool bVar1;
  
  if (DAT_febd3e07 == '\x01') {
    bVar1 = param_1 != (DAT_febd39c4 + 1 & 3);
    if (bVar1) {
      DAT_febd39b1 = DAT_febd3e07;
      FUN_0008d4de(1);
    }
    else {
      DAT_febd39b1 = '\0';
      FUN_0008d4de(0);
    }
    DAT_febd39b2 = bVar1 + bVar1 * !bVar1;
    DAT_febd39c4 = param_1;
    FUN_0008d500(bVar1);
    return 0;
  }
  return 1;
}


