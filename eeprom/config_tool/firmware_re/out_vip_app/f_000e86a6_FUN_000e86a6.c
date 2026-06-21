// entry=000e86a6 name=FUN_000e86a6 size=50
// reasons: callee_of:000aa0a8


/* WARNING: Control flow encountered bad instruction data */

undefined1 * FUN_000e86a6(undefined1 *param_1,undefined1 param_2,uint param_3)

{
  if ((-(int)param_1 & 3U) != 0) {
    if (param_3 <= (-(int)param_1 & 3U)) {
      if (param_3 != 0) {
        *param_1 = param_2;
      }
      return param_1;
    }
    *param_1 = param_2;
  }
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}


