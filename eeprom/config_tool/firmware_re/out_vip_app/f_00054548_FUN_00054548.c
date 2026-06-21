// entry=00054548 name=FUN_00054548 size=76
// reasons: caller_of:000a6560


void FUN_00054548(undefined1 param_1,undefined1 param_2)

{
  FUN_000530d2(&PTR_s_BLE_LOCAL_INFOTAINMENT_TIMEOUT_0002d578,param_1,param_2);
  FUN_000a6560(param_1,param_2);
  if (DAT_febd1043 == '\x01') {
    FUN_0005c140();
    DAT_febd1043 = 0;
    return;
  }
  FUN_0005c64a(s__UBLOX__UBLOX_chip_already_progr_0000c122 + 0x1e,0,param_2);
  return;
}


