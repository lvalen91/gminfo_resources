// entry=0009883c name=FUN_0009883c size=316
// reasons: caller_of:000aa0a8 | caller_of:000b7c8e


void FUN_0009883c(void)

{
  uint local_18 [2];
  
  FUN_0005c03c();
  FUN_0004f5b4();
  FUN_0006264a();
  FUN_0005c878();
  FUN_0004ec58();
  FUN_000656d4();
  FUN_0006269c();
  FUN_0008640a();
  FUN_00066b7a();
  FUN_0004c740();
  FUN_00055380();
  FUN_000573cc();
  FUN_00065bd4();
  do {
    do {
      FUN_000ecbbe(0xf00,0);
      FUN_000ecb88(2,local_18);
      FUN_000ecb5c(local_18[0] & 0xf00,0);
      if ((local_18[0] & 0x200) != 0) {
        switchD_00076bca::caseD_6b();
        FUN_0009c5fc();
        FUN_00099b24();
      }
      if ((local_18[0] & 0x800) != 0) {
        FUN_000b8732();
      }
      if ((local_18[0] & 0x200) != 0) {
        FUN_0009c9f2();
        FUN_0009cede();
        FUN_000aa0a8();
        FUN_0009cda6();
        FUN_000af112();
        FUN_000b7c8e();
        FUN_00099f64();
        FUN_0009ec2e();
        FUN_0005539e();
        FUN_00056cb4();
      }
      if ((local_18[0] & 0x400) != 0) {
        FUN_0009a1da();
      }
      if ((local_18[0] & 0x100) != 0) {
        FUN_0005b8e0();
        FUN_0005fbe0();
        FUN_00051e20();
      }
      if (((local_18[0] & 0x100) != 0) && (DAT_febd3a0e == '\x02')) {
        thunk_FUN_000ee012();
        DAT_febd3a0e = DAT_febd3a0d;
        thunk_FUN_000ee032();
      }
      if (((local_18[0] & 0xa00) != 0) && (DAT_febd3a16 == '\x06')) {
        thunk_FUN_000ee012();
        DAT_febd3a16 = DAT_febd3a0f;
        thunk_FUN_000ee032();
      }
    } while (((local_18[0] & 0x400) == 0) || (DAT_febd3a30 != '\x05'));
    thunk_FUN_000ee012();
    DAT_febd3a30 = DAT_febd3a2e;
    thunk_FUN_000ee032();
  } while( true );
}


