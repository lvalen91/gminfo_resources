// entry=0008b836 name=FUN_0008b836 size=48
// reasons: ldstr:[SS_SWC] cal_user_initiated_local_infotainment_t


undefined4 FUN_0008b836(undefined1 param_1)

{
  DAT_febd366a = param_1;
  thunk_FUN_000ee012();
  if ((DAT_febd3b80 & 0x10) == 0) {
    DAT_febd3b80 = DAT_febd3b80 | 0x20;
  }
  else {
    DAT_febd3b80 = DAT_febd3b80 & 0xdf;
  }
  thunk_FUN_000ee032();
  return 0;
}


