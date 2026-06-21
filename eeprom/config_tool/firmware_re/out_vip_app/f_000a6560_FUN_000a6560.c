// entry=000a6560 name=FUN_000a6560 size=192
// reasons: ldstr:[SS_SWC] cal_startup_fault_timeout_sec (%d) read


undefined4 FUN_000a6560(uint param_1,byte param_2)

{
  byte bVar1;
  
  if (DAT_febd3e00 != '\x01') {
    return 0;
  }
  if (DAT_febe71cd != '\x01') {
    return 0;
  }
  if (DAT_febd4c20 != '\x01') {
    return 0;
  }
  FUN_000ecd84(0x10);
  if (((DAT_febd379a == ' ') && ((param_2 & 1) == 0)) && ((param_1 & 1) != 0)) {
    DAT_febd379a = '\x10';
  }
  bVar1 = param_2 & 8;
  if (((bVar1 != 0) && ((param_1 & 8) == 0)) && (DAT_febd379a != ' ')) {
    DAT_febd379a = '\x01';
    DAT_febd37ab = param_2;
  }
  FUN_000ecdac(0x10);
  if (DAT_febd386d == '\0') {
LAB_000a6600:
    if (bVar1 == 0) goto LAB_000a6616;
  }
  else {
    if (bVar1 == 0) {
      if (DAT_febd37e0 != '\0') goto LAB_000a6616;
LAB_000a65f6:
      DAT_febd386d = '\0';
      DAT_febd387e = 0;
      goto LAB_000a6600;
    }
    if (DAT_febd37e0 == '\x01') goto LAB_000a65f6;
  }
  bVar1 = DAT_febd37f0 * (DAT_febd37f0 == '\x01');
LAB_000a6616:
  FUN_0008c8c4(bVar1);
  return 0;
}


