// entry=000b7bae name=FUN_000b7bae size=16
// reasons: callee_of:000b7c8e


void FUN_000b7bae(uint param_1,undefined4 param_2)

{
  int iVar1;
  int in_r12;
  uint in_r15;
  undefined4 *unaff_r22;
  uint unaff_r25;
  uint unaff_r27;
  uint *unaff_r28;
  uint *unaff_r29;
  undefined4 *unaff_ep;
  bool bVar2;
  
  param_1 = param_1 & 0xff;
  if (9 < param_1) {
    return;
  }
  iVar1 = param_1 * 4;
  bVar2 = param_1 == 0;
  switch(param_1) {
  case 0:
    do {
      bVar2 = unaff_ep[1] == 1;
switchD_000b7bb6_caseD_1:
      if (!bVar2) break;
      unaff_ep = (undefined4 *)*unaff_r22;
      *unaff_ep = 0xa5;
      *unaff_r29 = unaff_r25;
      *unaff_r29 = ~unaff_r25;
      *unaff_r29 = unaff_r25;
      unaff_r27 = unaff_r27 - 1 & 0xff;
    } while (unaff_r27 != 0);
    in_r12 = unaff_ep[1];
  case 2:
    unaff_r27 = (uint)(in_r12 == 1);
code_r0x000df644:
    thunk_FUN_000edf60();
code_r0x000df648:
    bVar2 = unaff_r27 == 0;
switchD_000b7bb6_caseD_5:
    if (!bVar2) {
      iVar1 = 0x99;
code_r0x000df650:
      param_2 = 1;
switchD_000b7bb6_caseD_7:
      FUN_000d56a2(iVar1,param_2);
    }
  case 8:
    in_r15 = 1000;
switchD_000b7bb6_caseD_9:
    for (; (*unaff_r28 != unaff_r25 && (in_r15 != 0)); in_r15 = in_r15 - 1 & 0xffff) {
    }
    if (*unaff_r28 != unaff_r25) {
      FUN_000d56a2(0x94,1);
    }
                    /* WARNING: Subroutine does not return */
    thunk_FUN_000edf2c();
  case 1:
    goto switchD_000b7bb6_caseD_1;
  case 3:
    goto code_r0x000df644;
  case 4:
    goto code_r0x000df648;
  case 5:
    goto switchD_000b7bb6_caseD_5;
  case 6:
    unaff_r25 = unaff_r25 & 0xff;
    goto code_r0x000df650;
  case 7:
    goto switchD_000b7bb6_caseD_7;
  case 9:
    goto switchD_000b7bb6_caseD_9;
  }
}


