// entry=000653e6 name=FUN_000653e6 size=458
// reasons: ldstr:[SS_SWC] cal_user_initiated_local_infotainment_t | str:[SS_SWC] cal_user_initiated_local_infotainment_t


undefined4 FUN_000653e6(void)

{
  char cVar1;
  uint uVar2;
  undefined4 uVar3;
  int iVar4;
  undefined8 uVar5;
  char cStack_31;
  byte bStack_30;
  undefined1 uStack_2f;
  undefined1 auStack_2e [34];
  
  FUN_000e8d86(&bStack_30,0x23);
  uVar5 = FUN_0008ee70(&bStack_30);
  uVar3 = (undefined4)((ulonglong)uVar5 >> 0x20);
  iVar4 = (int)uVar5;
  uVar2 = (uint)bStack_30;
  cVar1 = bStack_30 * '\x04';
  switch(uVar2) {
  case 0:
    iVar4 = -0x1430000;
  case 1:
    (&DAT_000036e5)[iVar4] = cVar1;
  case 2:
    return 0;
  case 3:
    iVar4 = -0x1430000;
  case 4:
    s__SS_SWC__cal_user_initiated_loca_000036e6[iVar4] = cVar1;
  case 5:
    return 0;
  case 6:
    iVar4 = -0x1430000;
  case 7:
    s__SS_SWC__cal_user_initiated_loca_000036e6[iVar4 + 1] = cVar1;
  case 8:
    return 0;
  case 9:
    iVar4 = -0x1430000;
  case 10:
    s__SS_SWC__cal_user_initiated_loca_000036e6[iVar4 + 2] = cVar1;
  case 0xb:
    return 0;
  case 0xc:
    iVar4 = -0x1430000;
  case 0xd:
    s__SS_SWC__cal_user_initiated_loca_000036e6[iVar4 + 3] = cVar1;
  case 0xe:
    return 0;
  case 0xf:
    iVar4 = -0x1430000;
  case 0x10:
    s__SS_SWC__cal_user_initiated_loca_000036e6[iVar4 + 4] = cVar1;
  case 0x11:
    return 0;
  case 0x12:
    iVar4 = -0x1430000;
  case 0x13:
    s__SS_SWC__cal_user_initiated_loca_000036e6[iVar4 + 5] = cVar1;
  case 0x14:
    return 0;
  case 0x15:
    iVar4 = -0x1430000;
  case 0x16:
    s__SS_SWC__cal_user_initiated_loca_000036e6[iVar4 + 6] = cVar1;
    return 0;
  }
  switch(uVar2) {
  case 0:
  case 1:
  case 2:
    return uVar3;
  case 3:
  case 4:
  case 5:
    return uVar3;
  case 6:
  case 7:
  case 8:
    return uVar3;
  case 9:
  case 10:
  case 0xb:
    return uVar3;
  case 0xc:
  case 0xd:
  case 0xe:
    return uVar3;
  case 0xf:
  case 0x10:
  case 0x11:
    return uVar3;
  case 0x12:
  case 0x13:
  case 0x14:
    return uVar3;
  case 0x15:
    return uVar3;
  }
  if ((uVar2 == 0x7d) || (uVar2 == 0x7e)) {
    FUN_000646a8(uVar2);
    goto LAB_0006555a;
  }
  if (uVar2 < 0x29) {
    if (((uVar2 != 0x21) && (uVar2 != 0x23)) && (uVar2 != 0x25)) {
LAB_0006554e:
      FUN_000840ac(8,&LAB_000320a0);
      goto LAB_0006555a;
    }
  }
  else if ((((uVar2 != 0x29) && (uVar2 != 0x31)) && (uVar2 != 0x33)) && (uVar2 != 0x35))
  goto LAB_0006554e;
  FUN_00064706(uVar2 - 0x20,auStack_2e,uStack_2f);
LAB_0006555a:
  FUN_000e1320(0x84,&cStack_31);
  if (cStack_31 == '\0') {
    FUN_00064796();
    FUN_00064a28();
    FUN_00064b58();
    FUN_00064dec();
    FUN_00064ffc();
  }
  if (DAT_febd1141 != DAT_febd1142) {
    FUN_0005c542(1,&DAT_febd1141,1);
    DAT_febd1142 = DAT_febd1141;
  }
  uVar3 = FUN_0005642a(&DAT_febe04dc);
  DAT_febe04dd = DAT_febe04dc >> 7;
  if (DAT_febe04dd != DAT_febe04de) {
    uVar3 = FUN_0005c542(2,&DAT_febe04dd,1);
    DAT_febe04de = DAT_febe04dd;
  }
  return uVar3;
}


