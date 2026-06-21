// entry=000ecd84 name=FUN_000ecd84 size=40
// reasons: callee_of:000a6560


uint FUN_000ecd84(undefined4 param_1)

{
  uint uVar1;
  undefined4 local_24 [6];
  
  uVar1 = FUN_000f5cb8();
  if (uVar1 != 0) {
    local_24[0] = param_1;
    thunk_FUN_000f2682(0xd8,uVar1,local_24);
  }
  return uVar1 & 0xff;
}


