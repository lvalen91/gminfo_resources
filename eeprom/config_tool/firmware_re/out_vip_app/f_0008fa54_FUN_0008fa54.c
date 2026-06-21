// entry=0008fa54 name=FUN_0008fa54 size=54
// reasons: ldstr:[SS_SWC] cal_user_initiated_local_infotainment_t


undefined4 FUN_0008fa54(undefined1 *param_1)

{
  thunk_FUN_000ee012();
  *param_1 = DAT_febd366a;
  if ((DAT_febd3b80 & 0x20) == 0) {
    DAT_febd3b80 = DAT_febd3b80 & 0xef;
  }
  else {
    DAT_febd3b80 = DAT_febd3b80 | 0x10;
  }
  thunk_FUN_000ee032();
  return 0;
}


