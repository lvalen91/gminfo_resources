// entry=000b7b14 name=FUN_000b7b14 size=16
// reasons: callee_of:000b7c8e


void FUN_000b7b14(byte param_1,undefined4 param_2,undefined4 param_3,int param_4)

{
  bool bVar1;
  int in_r11;
  int in_r17;
  int in_r18;
  int unaff_ep;
  
  if (9 < param_1) {
    return;
  }
  bVar1 = param_1 == 0;
  switch(param_1) {
  case 0:
    goto switchD_000b7b1c_caseD_6;
  case 1:
    break;
  case 2:
    break;
  case 3:
    break;
  case 5:
    in_r17 = param_4 - in_r17;
    __saturate(in_r17);
  case 6:
    goto switchD_000b7b1c_caseD_6;
  case 7:
    goto switchD_000b7b1c_caseD_7;
  case 8:
    goto switchD_000b7b1c_caseD_8;
  case 9:
    goto switchD_000b7b1c_caseD_9;
  }
  in_r17 = *(int *)(&DAT_00009808 + in_r18);
switchD_000b7b1c_caseD_6:
  bVar1 = (*(byte *)(unaff_ep + 6) & 2) == 0;
switchD_000b7b1c_caseD_7:
  if (!bVar1) {
    bVar1 = in_r11 == 0;
switchD_000b7b1c_caseD_8:
    if (!bVar1) {
      bVar1 = in_r17 == -1;
switchD_000b7b1c_caseD_9:
      if (!bVar1) {
                    /* WARNING: Subroutine does not return */
        thunk_FUN_000edf2c();
      }
    }
  }
                    /* WARNING: Subroutine does not return */
  thunk_FUN_000edf2c();
}


