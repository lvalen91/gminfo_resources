// entry=000aad1e name=FUN_000aad1e size=28
// reasons: ldstr:[SS_SWC] cal_startup_delay_wait_timeout_msec (%d


void FUN_000aad1e(char param_1,undefined1 param_2)

{
  undefined1 uVar1;
  
  uVar1 = param_2;
  if ((param_1 != '\0') && (uVar1 = DAT_febd3812, param_1 == '\x01')) {
    DAT_febd3813 = param_2;
    return;
  }
  DAT_febd3812 = uVar1;
  return;
}


