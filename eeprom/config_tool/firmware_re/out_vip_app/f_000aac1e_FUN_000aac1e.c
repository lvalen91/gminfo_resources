// entry=000aac1e name=FUN_000aac1e size=30
// reasons: ldstr:[SS_SWC] cal_startup_delay_wait_timeout_msec (%d


undefined1 FUN_000aac1e(char param_1)

{
  undefined1 uVar1;
  
  uVar1 = DAT_febd3812;
  if ((param_1 != '\0') && (uVar1 = 0, param_1 == '\x01')) {
    return DAT_febd3813;
  }
  return uVar1;
}


