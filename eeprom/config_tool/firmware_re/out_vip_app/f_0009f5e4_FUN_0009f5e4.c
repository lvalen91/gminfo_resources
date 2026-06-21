// entry=0009f5e4 name=FUN_0009f5e4 size=250
// reasons: callee_of:00086ae4


void FUN_0009f5e4(uint param_1,uint param_2,uint param_3)

{
  undefined4 *puVar1;
  uint uVar2;
  undefined1 *puVar3;
  uint uVar4;
  uint uVar5;
  undefined4 *puVar6;
  undefined1 *puVar7;
  
  uVar4 = 0;
  if (0xf < param_3) {
    uVar5 = uVar4;
    if (((param_2 & 3) == 0) && ((param_1 & 3) == 0)) {
      for (; uVar4 < (param_3 >> 2) - 3; uVar4 = uVar4 + 4) {
        puVar1 = (undefined4 *)(uVar4 * 4 + param_2);
        puVar6 = (undefined4 *)(uVar4 * 4 + param_1);
        *puVar6 = *puVar1;
        puVar6[1] = puVar1[1];
        puVar6[2] = puVar1[2];
        puVar6[3] = puVar1[3];
      }
      for (; uVar4 < param_3 >> 2; uVar4 = uVar4 + 1) {
        *(undefined4 *)(uVar4 * 4 + param_1) = *(undefined4 *)(uVar4 * 4 + param_2);
      }
      uVar4 = param_3 - (param_3 & 3);
    }
    else {
      do {
        puVar3 = (undefined1 *)(uVar5 + param_2);
        puVar7 = (undefined1 *)(uVar5 + param_1);
        uVar4 = uVar5 + 0x10;
        *puVar7 = *puVar3;
        puVar7[1] = puVar3[1];
        puVar7[2] = puVar3[2];
        puVar7[3] = puVar3[3];
        puVar7[4] = puVar3[4];
        puVar7[5] = puVar3[5];
        puVar7[6] = puVar3[6];
        puVar7[7] = puVar3[7];
        uVar2 = uVar5 + 0x1f;
        puVar7[8] = puVar3[8];
        puVar7[9] = puVar3[9];
        puVar7[10] = puVar3[10];
        puVar7[0xb] = puVar3[0xb];
        puVar7[0xc] = puVar3[0xc];
        puVar7[0xd] = puVar3[0xd];
        puVar7[0xe] = puVar3[0xe];
        puVar7[0xf] = puVar3[0xf];
        uVar5 = uVar4;
      } while (uVar2 < param_3);
    }
  }
  for (; uVar4 < param_3; uVar4 = uVar4 + 1) {
    *(undefined1 *)(uVar4 + param_1) = *(undefined1 *)(uVar4 + param_2);
  }
  return;
}


