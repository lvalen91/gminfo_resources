//===== FUN_00f608ac @ 00f608ac size=37 =====

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_00f608ac(void)

{
  char *pcVar1;
  int unaff_EDI;
  int unaff_retaddr;
  
  if (unaff_EDI != 0) {
    pcVar1 = (char *)(unaff_retaddr + -1);
    _DAT_0060e028 = pcVar1;
    *pcVar1 = *pcVar1 + (char)pcVar1;
    *pcVar1 = *pcVar1 + (char)pcVar1;
    DAT_00616098 = unaff_EDI;
    FUN_00f61d44();
    return;
  }
  return;
}



//===== FUN_00f60900 @ 00f60900 size=42 =====

void __fastcall FUN_00f60900(undefined4 param_1)

{
  cRam00000001 = cRam00000001 + '\x02';
  cRamffffffff = cRamffffffff + -2;
  FUN_00f61302(param_1);
  FUN_00f608ac();
  return;
}



//===== FUN_00f6092a @ 00f6092a size=42 =====

void __fastcall FUN_00f6092a(undefined4 param_1)

{
  cRam00000001 = cRam00000001 + '\x02';
  cRamffffffff = cRamffffffff + -2;
  FUN_00f61317(param_1);
  FUN_00f608ac();
  return;
}



//===== thunk_FUN_00f60db0 @ 00f609be size=5 =====

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 thunk_FUN_00f60db0(void)

{
  return _DAT_00000080;
}



//===== FUN_00f60b40 @ 00f60b40 size=277 =====

int * __fastcall FUN_00f60b40(int param_1,uint param_2)

{
  uint uVar1;
  uint uVar2;
  undefined1 *puVar3;
  uint uVar4;
  int *piVar5;
  int *piVar6;
  undefined1 *puVar7;
  uint uVar8;
  undefined1 uVar9;
  uint unaff_ESI;
  int *unaff_EDI;
  int *piVar10;
  
  piVar6 = (int *)(param_1 + -1);
  *piVar6 = (int)((int)unaff_EDI + *piVar6 + -1);
  *piVar6 = (int)((int)unaff_EDI + *piVar6 + -1);
  piVar6 = (int *)((unaff_ESI & 0xff) * 0x1010101);
  if (param_2 < 8) {
    if (4 < param_2) {
      *unaff_EDI = (int)piVar6;
      *(int **)((int)unaff_EDI + (param_2 - 4)) = piVar6;
      return (int *)((int)unaff_EDI + -3);
    }
    if (2 < param_2) {
      *(short *)unaff_EDI = (short)piVar6;
      *(short *)((int)unaff_EDI + (param_2 - 2)) = (short)piVar6;
      return unaff_EDI + -1;
    }
    piVar6 = (int *)((int)unaff_EDI + -5);
    if (param_2 != 0) {
      uVar9 = (undefined1)(param_2 >> 8);
      *(undefined1 *)unaff_EDI = uVar9;
      piVar6 = (int *)((int)unaff_EDI + -3);
      *(undefined1 *)((int)unaff_EDI + (param_2 - 1)) = uVar9;
    }
    return piVar6;
  }
  if (param_2 < 0x28) {
    *(int **)((int)unaff_EDI + (param_2 - 8)) = piVar6;
    piVar5 = (int *)((int)unaff_EDI + -5);
    if (8 < param_2) {
      *unaff_EDI = (int)piVar6;
      piVar5 = (int *)((int)unaff_EDI + -7);
      if (0x10 < param_2) {
        unaff_EDI[2] = (int)piVar6;
        piVar5 = (int *)((int)unaff_EDI + -9);
        if (0x18 < param_2) {
          unaff_EDI[4] = (int)piVar6;
          piVar5 = (int *)((int)unaff_EDI + -0xb);
          if (0x20 < param_2) {
            piVar5 = unaff_EDI + -3;
            unaff_EDI[6] = (int)piVar6;
          }
        }
      }
    }
    return piVar5;
  }
  if (0x1ff < param_2) {
    *unaff_EDI = (int)piVar6;
    unaff_EDI[2] = (int)piVar6;
    unaff_EDI[4] = (int)piVar6;
    unaff_EDI[6] = (int)piVar6;
    puVar3 = (undefined1 *)((uint)(unaff_EDI + 8) & 0xffffffe0);
    for (puVar7 = (undefined1 *)
                  ((int)unaff_EDI + ((param_2 - 6) - (int)((uint)(unaff_EDI + 8) & 0xffffffe0)));
        puVar7 != (undefined1 *)0x0; puVar7 = puVar7 + -1) {
      *puVar3 = (char)piVar6;
      puVar3 = puVar3 + 1;
    }
    return piVar6;
  }
  *unaff_EDI = (int)piVar6;
  *(int **)((int)unaff_EDI + (param_2 - 0xb)) = piVar6;
  puVar3 = (undefined1 *)
           ((int)unaff_EDI + ((param_2 - 3) - (int)((uint)(unaff_EDI + 2) & 0xfffffff8)));
  uVar1 = (uint)puVar3 >> 5;
  uVar2 = ((uint)puVar3 >> 3) - 2 & 3;
  piVar5 = (int *)((uint)(unaff_EDI + 2) & 0xfffffff8);
  do {
    piVar10 = piVar5;
    uVar8 = uVar2;
    uVar4 = uVar1;
    *piVar10 = (int)piVar6;
    piVar10[2] = (int)piVar6;
    piVar10[4] = (int)piVar6;
    piVar10[6] = (int)piVar6;
    uVar1 = uVar4 - 6;
    uVar2 = uVar8 - 1;
    piVar5 = piVar10 + 8;
  } while (uVar4 - 6 != 0);
  piVar5 = (int *)0x0;
  if (uVar8 - 1 != 0) {
    piVar5 = (int *)(uVar4 - 7);
    piVar10[8] = (int)piVar6;
    if (uVar8 != 3) {
      piVar5 = (int *)(uVar4 - 8);
      piVar10[10] = (int)piVar6;
      if (uVar8 != 5) {
        piVar5 = (int *)(uVar4 - 9);
        piVar10[0xc] = (int)piVar6;
      }
    }
  }
  return piVar5;
}



//===== FUN_00f60c60 @ 00f60c60 size=257 =====

void __fastcall FUN_00f60c60(undefined4 param_1,uint param_2)

{
  int iVar1;
  int iVar2;
  int iVar3;
  uint uVar4;
  int *unaff_ESI;
  int *piVar5;
  int *piVar6;
  int *unaff_EDI;
  int *piVar7;
  int *piVar8;
  
  if ((int)param_2 < 0x61) {
    while (0x1f < (int)param_2) {
      iVar1 = unaff_ESI[2];
      iVar2 = unaff_ESI[4];
      iVar3 = unaff_ESI[6];
      *unaff_EDI = iVar1 + -1;
      unaff_EDI[2] = iVar1 + -1;
      unaff_EDI[4] = iVar2;
      unaff_EDI[6] = iVar3;
      unaff_ESI = unaff_ESI + 8;
      unaff_EDI = unaff_EDI + 8;
      param_2 = iVar2 - 0x20;
    }
    for (; 7 < (int)param_2; param_2 = param_2 - 8) {
      *unaff_EDI = *unaff_ESI + -1;
      unaff_ESI = unaff_ESI + 2;
      unaff_EDI = unaff_EDI + 2;
    }
    if ((param_2 & 4) != 0) {
      param_2 = param_2 - 4;
      *unaff_EDI = *unaff_ESI;
      unaff_ESI = unaff_ESI + 1;
      unaff_EDI = unaff_EDI + 1;
    }
    for (; param_2 != 0; param_2 = param_2 - 1) {
      *(char *)unaff_EDI = (char)*unaff_ESI;
      unaff_ESI = (int *)((int)unaff_ESI + 1);
      unaff_EDI = (int *)((int)unaff_EDI + 1);
    }
    return;
  }
  if (((600 < param_2) && ((int)param_2 < 0x960)) &&
     (uVar4 = param_2, (((uint)((int)unaff_ESI + -1) ^ (uint)unaff_EDI) - 1 & 0x3f) != 0))
  goto LAB_00f60d14;
  do {
    uVar4 = 0;
    piVar6 = unaff_ESI;
    piVar8 = unaff_EDI;
    while( true ) {
      unaff_EDI = piVar8 + 1;
      unaff_ESI = piVar6 + 1;
      *piVar8 = *piVar6;
      if ((int)uVar4 < 1) {
        piVar5 = unaff_ESI;
        piVar7 = unaff_EDI;
        if ((param_2 - 4 & 4) != 0) {
          piVar7 = piVar8 + 2;
          piVar5 = piVar6 + 2;
          *unaff_EDI = *unaff_ESI;
        }
        piVar6 = piVar5;
        piVar8 = piVar7;
        if ((param_2 - 5 & 2) != 0) {
          piVar8 = (int *)((int)piVar7 + 2);
          piVar6 = (int *)((int)piVar5 + 2);
          *(short *)piVar7 = (short)*piVar5;
        }
        if ((param_2 - 6 & 1) == 0) {
          return;
        }
        *(char *)piVar8 = (char)*piVar6;
        return;
      }
LAB_00f60d14:
      param_2 = uVar4;
      if ((int)param_2 < 0x259) break;
      uVar4 = param_2 - 600;
      param_2 = 0;
      piVar6 = unaff_ESI;
      piVar8 = unaff_EDI;
    }
  } while( true );
}



//===== FUN_00f60db0 @ 00f60db0 size=9 =====

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 FUN_00f60db0(void)

{
  return _DAT_00000080;
}



//===== FUN_00f60dbc @ 00f60dbc size=15 =====

undefined4 __fastcall FUN_00f60dbc(undefined4 param_1)

{
  int iVar1;
  
  iVar1 = thunk_FUN_00f60db0(param_1);
  return *(undefined4 *)(iVar1 + 0xff);
}



//===== FUN_00f6123f @ 00f6123f size=35 =====

/* WARNING: Control flow encountered bad instruction data */

undefined4 FUN_00f6123f(void)

{
  int unaff_EDI;
  
  if (unaff_EDI == 0) {
    return 0x10;
  }
  FUN_00f60dbc();
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



//===== FUN_00f612a2 @ 00f612a2 size=68 =====

/* WARNING: Unable to track spacebase fully for stack */

void __fastcall FUN_00f612a2(undefined4 param_1,undefined4 *param_2)

{
  int iVar1;
  
  param_2[-1] = 0xf612b5;
  iVar1 = FUN_00f6123f();
  if (iVar1 == 0x8a) {
    *(undefined4 *)((int)param_2 + -5) = 0xf612d2;
    FUN_00f62234();
  }
  else if (iVar1 == 0) {
    *param_2 = 0;
  }
  return;
}



//===== FUN_00f61302 @ 00f61302 size=21 =====

void FUN_00f61302(void)

{
  FUN_00f612a2();
  return;
}



//===== FUN_00f61317 @ 00f61317 size=35 =====

/* WARNING: Control flow encountered bad instruction data */

undefined4 FUN_00f61317(void)

{
  int unaff_EDI;
  
  if (unaff_EDI == 0) {
    return 0x10;
  }
  FUN_00f60dbc();
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



//===== FUN_00f61468 @ 00f61468 size=45 =====

int __fastcall FUN_00f61468(undefined4 param_1,undefined4 *param_2)

{
  int in_EAX;
  int iVar1;
  int iVar2;
  undefined4 unaff_ESI;
  undefined4 local_c [2];
  
  iVar1 = in_EAX + -3;
  if (param_2 == (undefined4 *)0x0) {
    iVar1 = in_EAX + -4;
    param_2 = local_c;
  }
  syscall();
  *param_2 = unaff_ESI;
  iVar2 = 0;
  if (iVar1 != 1) {
    iVar2 = iVar1 + -3;
    *param_2 = 0;
  }
  return iVar2;
}



//===== FUN_00f614c8 @ 00f614c8 size=15 =====

int FUN_00f614c8(void)

{
  int in_EAX;
  
  syscall();
  return in_EAX + -1;
}



//===== FUN_00f61768 @ 00f61768 size=35 =====

int __fastcall FUN_00f61768(undefined4 param_1,undefined4 *param_2)

{
  int in_EAX;
  int iVar1;
  undefined4 unaff_ESI;
  undefined4 local_c [2];
  
  iVar1 = in_EAX + -3;
  if (param_2 == (undefined4 *)0x0) {
    iVar1 = in_EAX + -4;
    param_2 = local_c;
  }
  syscall();
  *param_2 = unaff_ESI;
  return iVar1 + -1;
}



//===== FUN_00f61804 @ 00f61804 size=51 =====

void FUN_00f61804(void)

{
  int in_EAX;
  undefined1 *puVar1;
  int unaff_ESI;
  undefined1 auStack_c [8];
  
  puVar1 = (undefined1 *)(in_EAX + -2);
  if (puVar1 == (undefined1 *)0x0) {
    puVar1 = auStack_c;
  }
  syscall();
  *(int *)(puVar1 + -2) = unaff_ESI + -1;
  if ((int *)(puVar1 + -2) != (int *)0x0) {
    *(undefined4 *)(puVar1 + -3) = 0;
  }
  return;
}



//===== FUN_00f61838 @ 00f61838 size=18 =====

undefined8 __fastcall FUN_00f61838(undefined4 param_1,undefined4 param_2)

{
  int in_EAX;
  
  syscall();
  return CONCAT44(param_2,in_EAX + -1);
}



//===== FUN_00f6184c @ 00f6184c size=18 =====

undefined8 __fastcall FUN_00f6184c(undefined4 param_1,undefined4 param_2)

{
  int in_EAX;
  
  syscall();
  return CONCAT44(param_2,in_EAX + -1);
}



//===== FUN_00f6190c @ 00f6190c size=100 =====

int __fastcall FUN_00f6190c(undefined4 param_1,int param_2)

{
  undefined4 uVar1;
  int iVar2;
  int iStack_fb;
  
  uVar1 = 0xffffffff;
  if (param_2 != 0) {
    uVar1 = *(undefined4 *)(param_2 + 8);
  }
  iStack_fb._1_3_ = (undefined3)uVar1;
  iVar2 = -1;
  if (&stack0x00000000 != &DAT_00000103) {
    iVar2 = iStack_fb;
  }
  syscall();
  return iVar2 + -1;
}



//===== FUN_00f619dc @ 00f619dc size=32 =====

int __fastcall FUN_00f619dc(undefined4 param_1)

{
  int in_EAX;
  int iVar1;
  undefined4 *unaff_ESI;
  undefined4 local_c [2];
  
  iVar1 = in_EAX + -3;
  if (unaff_ESI == (undefined4 *)0x0) {
    iVar1 = in_EAX + -4;
    unaff_ESI = local_c;
  }
  syscall();
  *unaff_ESI = param_1;
  return iVar1 + -1;
}



//===== FUN_00f61d44 @ 00f61d44 size=58 =====

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_00f61d44(void)

{
  undefined1 local_9;
  int local_8;
  
  local_8 = 0;
  DAT_00236f93 = DAT_00236f93 + '&';
  FUN_00f96f93();
  _DAT_0060e060 = &local_9;
  do {
  } while (local_8 == 0);
  return;
}



//===== FUN_00f61e2c @ 00f61e2c size=14 =====

int __fastcall FUN_00f61e2c(undefined4 param_1)

{
  int iVar1;
  
  iVar1 = thunk_FUN_00f60db0(param_1);
  return iVar1 + 0x87;
}



//===== FUN_00f61e3a @ 00f61e3a size=18 =====

void FUN_00f61e3a(void)

{
  int iVar1;
  undefined4 unaff_EDI;
  
  iVar1 = FUN_00f61e2c();
  if ((undefined4 *)(iVar1 + -1) != (undefined4 *)0x0) {
    *(undefined4 *)(iVar1 + -1) = unaff_EDI;
  }
  return;
}



//===== FUN_00f61e60 @ 00f61e60 size=53 =====

undefined1 * FUN_00f61e60(void)

{
  undefined1 local_104 [3];
  
  syscall();
  return local_104;
}



//===== FUN_00f62234 @ 00f62234 size=41 =====

void FUN_00f62234(void)

{
  int in_EAX;
  undefined1 *puVar1;
  int unaff_ESI;
  undefined1 auStack_c [8];
  
  puVar1 = (undefined1 *)(in_EAX + -2);
  if (puVar1 == (undefined1 *)0x0) {
    puVar1 = auStack_c;
  }
  syscall();
  *(int *)(puVar1 + -2) = unaff_ESI + -1;
  return;
}



//===== FUN_00f62270 @ 00f62270 size=30 =====

int __fastcall FUN_00f62270(undefined4 param_1,int param_2)

{
  int in_EAX;
  undefined4 *unaff_ESI;
  
  syscall();
  if (unaff_ESI != (undefined4 *)0x0) {
    *unaff_ESI = param_1;
  }
  if (param_2 != 0) {
    *(int *)param_2 = param_2;
  }
  return in_EAX + -3;
}



//===== FUN_00f623e8 @ 00f623e8 size=75 =====

int FUN_00f623e8(void)

{
  char *pcVar1;
  char *pcVar2;
  char cVar3;
  char *pcVar4;
  int iVar5;
  int unaff_EDI;
  
  cVar3 = DAT_00601367._1_1_;
  pcVar2 = (char *)CONCAT13(UNK_0060136b,CONCAT21(DAT_00601367._2_2_,DAT_00601367._1_1_));
  *pcVar2 = *pcVar2 + DAT_00601367._1_1_;
  *pcVar2 = *pcVar2 + cVar3;
  pcVar1 = pcVar2 + unaff_EDI + -1;
  pcVar4 = pcVar2 + -2;
  *pcVar4 = *pcVar4 + (char)pcVar4;
  *pcVar4 = *pcVar4 + (char)pcVar4;
  if ((&WAVE_00a792e8.field_0xd18 < pcVar1) || (pcVar1 < pcVar2 + -4)) {
    iVar5 = -1;
    FUN_00f61e3a();
  }
  else {
    DAT_00601367._0_1_ = SUB41(pcVar1,0);
    DAT_00601367._1_1_ = (char)((uint)pcVar1 >> 8);
    DAT_00601367._2_2_ = (undefined2)((uint)pcVar1 >> 0x10);
    iVar5 = (int)pcVar1 - unaff_EDI;
  }
  return iVar5;
}



//===== FUN_00f62433 @ 00f62433 size=30 =====

int FUN_00f62433(void)

{
  int iVar1;
  
  FUN_00f60900();
  iVar1 = FUN_00f623e8();
  FUN_00f6092a();
  return iVar1 + -1;
}



//===== FUN_00f62baf @ 00f62baf size=261 =====

/* WARNING: Unable to track spacebase fully for stack */

void FUN_00f62baf(void)

{
  ushort uVar1;
  int iVar2;
  undefined1 *puVar3;
  int iVar4;
  undefined1 *puVar5;
  uint *unaff_EDI;
  byte bVar6;
  byte bVar7;
  undefined8 uVar8;
  
  if (unaff_EDI[4] - 2 < unaff_EDI[2]) {
    iVar4 = unaff_EDI[2] - (unaff_EDI[4] - 3);
    bVar6 = CARRY4(unaff_EDI[4],*unaff_EDI);
    *(undefined4 *)(iVar4 + -6) = 0xf62c88;
    uVar8 = FUN_00f9857d();
    puVar5 = (undefined1 *)((ulonglong)uVar8 >> 0x20);
    iVar2 = (int)uVar8 + -1;
    uVar1 = (ushort)iVar2;
    bVar7 = puVar5 < (undefined1 *)(iVar4 + -3);
    puVar3 = (undefined1 *)
             CONCAT22((short)((uint)iVar2 >> 0x10),
                      uVar1 + (ushort)bVar6 *
                              (((ushort)((ulonglong)uVar8 >> 0x20) & 3) - (uVar1 & 3)));
    if ((undefined1 *)(iVar4 + -3) < puVar5) {
      *(undefined4 *)(iVar4 + -7) = 0xf62c9a;
      FUN_00f986e0();
      puVar3 = (undefined1 *)(iVar4 + -2);
    }
    uVar1 = (ushort)(puVar3 + -1);
    unaff_EDI[4] = unaff_EDI[4] +
                   CONCAT22((short)((uint)(puVar3 + -1) >> 0x10),
                            uVar1 + (ushort)bVar7 * ((uVar1 & 3) - (uVar1 & 3))) + -1;
    *(undefined1 *)(*unaff_EDI + (unaff_EDI[4] - 1)) = 0;
  }
  return;
}



//===== FUN_00f65964 @ 00f65964 size=242 =====

/* WARNING: Unable to track spacebase fully for stack */

int FUN_00f65964(void)

{
  int iVar1;
  undefined1 *puVar2;
  int unaff_ESI;
  int *unaff_EDI;
  
  *(undefined4 *)(unaff_ESI + -4) = 0xf6597c;
  iVar1 = thunk_FUN_00f60db0();
  if (*(int *)(iVar1 + 0x177) == 1) {
    *(undefined4 *)(unaff_ESI + -4) = 0xf659a2;
    iVar1 = FUN_00f619dc();
    if (iVar1 != 0) {
      return iVar1;
    }
    *(undefined4 *)(unaff_ESI + -4) = 0xf659b1;
    thunk_FUN_00f60db0();
    *(undefined4 *)(unaff_ESI + -4) = 0xf659cd;
    iVar1 = FUN_00f61468();
    if (iVar1 != 0) {
      return iVar1;
    }
  }
  if ((unaff_EDI != (int *)0x0) && ((*unaff_EDI != 0 || (unaff_EDI[2] != 0)))) {
    *(undefined4 *)(unaff_ESI + -4) = 0xf659ea;
    thunk_FUN_00f60db0();
    puVar2 = (undefined1 *)(unaff_ESI + -2);
    *(undefined4 *)(unaff_ESI + -6) = 0xf65a0a;
    iVar1 = FUN_00f6190c();
    if ((iVar1 == 0xd4) || (iVar1 == 0xd5)) {
      puVar2 = (undefined1 *)(unaff_ESI + -3);
      *(undefined4 *)(unaff_ESI + -7) = 0xf65a2d;
      FUN_00f6190c();
    }
    *(undefined4 *)(puVar2 + -4) = 0xf65a39;
    FUN_00f608ac();
    *(undefined4 *)(puVar2 + -5) = 0xf65a43;
    FUN_00f614c8();
    *(undefined4 *)(puVar2 + -5) = 0xf65a4b;
    FUN_00f608ac();
  }
  return 0;
}



//===== FUN_00f65a8f @ 00f65a8f size=83 =====

undefined4 FUN_00f65a8f(void)

{
  FUN_00f65964();
  return 0;
}



//===== thunk_FUN_00f6e1a9 @ 00f6e190 size=2 =====

uint __fastcall thunk_FUN_00f6e1a9(uint param_1,int param_2)

{
  byte *unaff_ESI;
  int unaff_EDI;
  
  while (param_2 != 2) {
    param_1 = param_1 >> 8 ^ *(uint *)((((*unaff_ESI ^ param_1) & 0xff) - 1) * 4 + -1 + unaff_EDI);
    unaff_ESI = unaff_ESI + 1;
    param_2 = param_2 + -1;
  }
  return param_1;
}



//===== FUN_00f6e1a9 @ 00f6e1a9 size=39 =====

uint __fastcall FUN_00f6e1a9(uint param_1,int param_2)

{
  byte *unaff_ESI;
  int unaff_EDI;
  
  while (param_2 != 2) {
    param_1 = param_1 >> 8 ^ *(uint *)((((*unaff_ESI ^ param_1) & 0xff) - 1) * 4 + -1 + unaff_EDI);
    unaff_ESI = unaff_ESI + 1;
    param_2 = param_2 + -1;
  }
  return param_1;
}



//===== FUN_00f6e5c8 @ 00f6e5c8 size=49 =====

/* WARNING: Unable to track spacebase fully for stack */

void FUN_00f6e5c8(void)

{
  int iVar1;
  undefined1 *unaff_ESI;
  
  do {
    *(undefined4 *)(unaff_ESI + -6) = 0xf6e5ec;
    iVar1 = FUN_00f61768();
    unaff_ESI = unaff_ESI + -2;
  } while (iVar1 == 0xdd);
  return;
}



//===== FUN_00f86608 @ 00f86608 size=4 =====

void FUN_00f86608(void)

{
  return;
}



//===== FUN_00f86746 @ 00f86746 size=48 =====

void FUN_00f86746(void)

{
  ushort uVar1;
  undefined4 *unaff_ESI;
  int unaff_EDI;
  undefined4 *puVar2;
  
  uVar1 = *(ushort *)(unaff_EDI + 0x414);
  puVar2 = (undefined4 *)(unaff_EDI + 0x416 + (uVar1 & 0x3ff) * 0x10);
  *puVar2 = *unaff_ESI;
  puVar2[1] = unaff_ESI[1];
  *(ushort *)(unaff_EDI + 0x40f) = uVar1 + 1;
  return;
}



//===== FUN_00f86776 @ 00f86776 size=203 =====

/* WARNING: Unable to track spacebase fully for stack */

undefined4 FUN_00f86776(void)

{
  uint uVar1;
  uint uVar2;
  undefined4 uVar3;
  undefined1 *puVar4;
  undefined1 *puVar5;
  int unaff_EDI;
  
  puVar5 = *(undefined1 **)(unaff_EDI + 0x104420);
  do {
    if (puVar5 == (undefined1 *)0x0) goto LAB_00f86833;
    uVar1 = *(uint *)(unaff_EDI + 0x104418);
    uVar2 = *(uint *)(unaff_EDI + 0x10441c);
    if (uVar2 < uVar1) {
      puVar4 = (undefined1 *)(uVar1 - uVar2);
LAB_00f867ae:
      puVar4 = puVar4 + -1;
    }
    else {
      puVar4 = (undefined1 *)(0x100000 - uVar2);
      if (uVar1 == 0) goto LAB_00f867ae;
    }
    if (puVar4 < puVar5) {
      puVar5 = puVar4;
    }
    *(undefined4 *)(puVar5 + -4) = 0xf867e7;
    FUN_00f92ff0();
    *(int *)(unaff_EDI + 0x10441c) = (int)(puVar5 + *(int *)(unaff_EDI + 0x10441c) + 1);
    *(int *)(unaff_EDI + 0x104424) = (int)(puVar5 + *(int *)(unaff_EDI + 0x104424) + 2);
    *(int *)(unaff_EDI + 0x104420) = *(int *)(unaff_EDI + 0x104420) - (int)(puVar5 + 3);
    puVar5 = *(undefined1 **)(unaff_EDI + 0x104420);
  } while ((*(int *)(unaff_EDI + 0x10441c) == 0x100000) &&
          (*(undefined4 *)(unaff_EDI + 0x10441c) = 0, 1 < *(uint *)(unaff_EDI + 0x104418)));
  if (puVar5 == (undefined1 *)0x0) {
LAB_00f86833:
    uVar3 = 1;
  }
  else {
    uVar3 = 2;
  }
  return uVar3;
}



//===== FUN_00f86841 @ 00f86841 size=109 =====

void FUN_00f86841(void)

{
  int iVar1;
  int unaff_EDI;
  
  do {
    iVar1 = FUN_00f8ffb3();
    *(int *)(unaff_EDI + 0x104418) = *(int *)(unaff_EDI + 0x104418) + iVar1;
    if (*(int *)(unaff_EDI + 0x104418) != 0x100000) break;
    *(undefined4 *)(unaff_EDI + 0x104418) = 0;
  } while (*(int *)(unaff_EDI + 0x10441c) != 0);
  *(undefined4 *)(unaff_EDI + 0x410) = 2;
  return;
}



//===== FUN_00f868ae @ 00f868ae size=55 =====

undefined1 __fastcall FUN_00f868ae(undefined4 param_1,undefined4 param_2)

{
  undefined1 uVar1;
  int unaff_EDI;
  
  uVar1 = 0;
  if (*(char *)(unaff_EDI + 2) != '\0') {
    if ((char)((uint)param_2 >> 8) == '\x01') {
      FUN_00f88cec();
    }
    uVar1 = FUN_00f88ba5();
  }
  return uVar1;
}



//===== FUN_00f868e5 @ 00f868e5 size=357 =====

void FUN_00f868e5(void)

{
  undefined2 uVar1;
  undefined4 uVar2;
  char cVar3;
  byte bVar4;
  int iVar5;
  int iVar6;
  uint uVar7;
  int unaff_EDI;
  
  FUN_00f86608();
  iVar5 = FUN_00f88165();
  if (iVar5 != 1) {
    cVar3 = *(char *)(iVar5 + 1);
    while (cVar3 != '\0') {
      cVar3 = FUN_00f88dac();
      if (cVar3 == '\0') {
        return;
      }
      *(undefined4 *)(iVar5 + -0x10) = DAT_0040bb10;
      *(undefined4 *)(iVar5 + -0xc) = DAT_0040bb14;
      if (*(char *)(iVar5 + 0x30) == '\0') {
        uVar7 = FUN_00f88e89();
      }
      else {
        *(undefined1 *)(iVar5 + 0x30) = 0;
        FUN_00f88efb();
        uVar7 = *(uint *)(iVar5 + -2);
      }
      uVar7 = uVar7 & 0xffff;
      FUN_00f88efb();
      iVar5 = iVar5 + 1;
      while( true ) {
        if ((*(ushort *)(iVar5 + -4) & 2) == 0) {
          uVar2 = *(undefined4 *)(iVar5 + -0x10);
          *(ushort *)(unaff_EDI + 0x104433) = *(ushort *)(iVar5 + -4);
          *(undefined4 *)(unaff_EDI + 0x104426) = uVar2;
          uVar2 = *(undefined4 *)(iVar5 + -8);
          uVar1 = *(undefined2 *)(iVar5 + -2);
          *(undefined4 *)(unaff_EDI + 0x10442e) = uVar2;
          *(undefined2 *)(unaff_EDI + 0x104434) = uVar1;
          iVar5 = CONCAT22((short)((uint)iVar5 >> 0x10),(short)iVar5 + 1);
          *(uint *)(iVar5 + 0x2a) = uVar7;
          *(undefined4 *)(iVar5 + 0x2c) = 0;
          *(undefined4 *)(unaff_EDI + 0x104424) = 0;
          *(undefined4 *)(unaff_EDI + 0x104420) = uVar2;
          bVar4 = FUN_00f86776();
          iVar6 = (uint)bVar4 << 8;
          if ((*(int *)(unaff_EDI + 0x410) != 2) &&
             (iVar6 = *(int *)(unaff_EDI + 0x104418), iVar6 != *(int *)(unaff_EDI + 0x10441c))) {
            iVar6 = FUN_00f86841();
          }
        }
        else {
          iVar6 = FUN_00f86746();
        }
        cVar3 = (char)((uint)iVar6 >> 8);
        if ((*(ushort *)(iVar5 + -4) & 1) == 0) break;
        if (cVar3 == '\x02') {
          *(undefined1 *)(iVar5 + 0x30) = 1;
          return;
        }
        uVar7 = (uint)*(ushort *)(iVar5 + -2);
        FUN_00f88efb();
      }
      if (cVar3 == '\x02') {
        return;
      }
      cVar3 = FUN_00f868ae();
    }
  }
  return;
}



//===== FUN_00f88165 @ 00f88165 size=30 =====

int FUN_00f88165(void)

{
  int iVar1;
  int unaff_EDI;
  
  iVar1 = 0;
  if (*(ushort *)(unaff_EDI + 0x2a) < *(ushort *)(unaff_EDI + 0x28)) {
    iVar1 = (*(ushort *)(unaff_EDI + 0x2a) - 1) * 0x40 + unaff_EDI + 0x30;
  }
  return iVar1;
}



//===== FUN_00f88ba5 @ 00f88ba5 size=149 =====

undefined4 FUN_00f88ba5(void)

{
  int iVar1;
  int unaff_EDI;
  
  if (*(char *)(unaff_EDI + 2) != '\0') {
    if ((*(char *)(unaff_EDI + 0x30) != '\0') ||
       ((*(uint *)(unaff_EDI + 0x24) != 0xffffffff &&
        ((uint)*(ushort *)(unaff_EDI + 0x20) != *(uint *)(unaff_EDI + 0x24))))) {
      return 1;
    }
    iVar1 = FUN_00f8ff36(0xffffffff);
    if ((*(uint *)(iVar1 + -2) != 0) && (*(uint *)(iVar1 + -2) < 0x111)) {
      if (*(int *)(iVar1 + 3) == 4) {
        *(undefined4 *)(unaff_EDI + 0x24) = *(undefined4 *)(iVar1 + 10);
        *(ushort *)(unaff_EDI + 0x28) = *(ushort *)(unaff_EDI + 0x28) | 1;
        return 1;
      }
      if (*(int *)(iVar1 + 3) == 3) {
        *(undefined4 *)(unaff_EDI + 0x24) = 0xffffffff;
        *(ushort *)(unaff_EDI + 0x28) = *(ushort *)(unaff_EDI + 0x28) & 0xfffe;
      }
    }
  }
  return 0;
}



//===== FUN_00f88c3a @ 00f88c3a size=80 =====

void FUN_00f88c3a(void)

{
  int iVar1;
  int unaff_EDI;
  
  iVar1 = *(int *)(unaff_EDI + 0x38);
  if ((*(char *)(unaff_EDI + 2) != '\0') && (*(char *)(unaff_EDI + 0x31) == '\0')) {
    *(undefined1 *)(unaff_EDI + 0x31) = 1;
    if (*(char *)(iVar1 + 0x131) == '\0') {
      *(undefined1 *)(iVar1 + 0x18) = 1;
      FUN_00f92480();
      return;
    }
    if (*(char *)(iVar1 + 0x140) != '\0') {
      FUN_00f8ceb8();
      return;
    }
  }
  return;
}



//===== FUN_00f88c8a @ 00f88c8a size=98 =====

/* WARNING: Unable to track spacebase fully for stack */

void FUN_00f88c8a(void)

{
  int iVar1;
  int unaff_EDI;
  
  iVar1 = **(int **)(unaff_EDI + 0x38);
  *(undefined4 *)(iVar1 + -5) = 0xf88caa;
  FUN_00f93095();
  *(undefined4 *)(iVar1 + -0x12) = 1;
  *(undefined4 *)(iVar1 + -0x16) = 0xf88cdb;
  FUN_00f93030();
  *(undefined4 *)(iVar1 + -6) = 0xf88ce7;
  FUN_00f88c3a();
  return;
}



//===== FUN_00f88cec @ 00f88cec size=192 =====

int FUN_00f88cec(void)

{
  int iVar1;
  undefined2 *unaff_EDI;
  undefined2 uVar2;
  
  iVar1 = CONCAT22((short)((uint)*(undefined4 *)(unaff_EDI + 0x1c) >> 0x10),*unaff_EDI) + -1;
  iVar1 = CONCAT22((short)((uint)iVar1 >> 0x10),(ushort)iVar1 & unaff_EDI[0x11]);
  if (*(char *)(unaff_EDI + 1) != '\0') {
    uVar2 = 0;
    FUN_00f93030();
    iVar1 = FUN_00f93030(1,uVar2);
    iVar1 = iVar1 + -1;
    unaff_EDI[0x11] = unaff_EDI[0x11] + 1;
    if ((char)((uint)iVar1 >> 8) != '\0') {
      iVar1 = FUN_00f88c8a();
    }
  }
  return iVar1;
}



//===== FUN_00f88dac @ 00f88dac size=221 =====

/* WARNING: Unable to track spacebase fully for stack */

undefined1 FUN_00f88dac(void)

{
  int iVar1;
  undefined1 uVar2;
  byte unaff_BP;
  int unaff_EDI;
  
  iVar1 = **(int **)(unaff_EDI + 0x38);
  uVar2 = 0;
  if (*(char *)(unaff_EDI + 2) != '\0') {
    if ((*(char *)(unaff_EDI + 0x30) == '\0') &&
       ((*(uint *)(unaff_EDI + 0x24) == 0xffffffff ||
        ((uint)*(ushort *)(unaff_EDI + 0x20) == *(uint *)(unaff_EDI + 0x24))))) {
      *(undefined4 *)(iVar1 + -5) = 0xf88e12;
      FUN_00f92ff0();
      if (*(short *)(unaff_EDI + 0x20) == (ushort)((ushort)unaff_BP << 8)) {
        *(undefined4 *)(unaff_EDI + 0x24) = 0xffffffff;
        return 0;
      }
      *(undefined4 *)(iVar1 + -6) = 0xf88e36;
      FUN_00f93095();
      if ((*(ushort *)(unaff_EDI + 0x28) & 1) == 0) {
        *(ushort *)(unaff_EDI + 0x28) = *(ushort *)(unaff_EDI + 0x28) | 1;
        *(undefined4 *)(iVar1 + -0x13) = 1;
        *(undefined4 *)(iVar1 + -0x17) = 0xf88e74;
        FUN_00f93030();
      }
      *(uint *)(unaff_EDI + 0x24) = (uint)unaff_BP << 8;
    }
    uVar2 = 1;
  }
  return uVar2;
}



//===== FUN_00f88e89 @ 00f88e89 size=109 =====

undefined2 FUN_00f88e89(void)

{
  char extraout_AH;
  undefined2 unaff_BP;
  int unaff_EDI;
  
  if (*(char *)(unaff_EDI + 2) == '\0') {
    unaff_BP = 0;
  }
  else {
    FUN_00f92ff0();
    if (extraout_AH == '\0') {
      *(short *)(unaff_EDI + 0x20) = *(short *)(unaff_EDI + 0x20) + 1;
    }
  }
  return unaff_BP;
}



//===== FUN_00f88efb @ 00f88efb size=55 =====

undefined4 FUN_00f88efb(void)

{
  undefined4 uVar1;
  int unaff_EDI;
  
  if (*(char *)(unaff_EDI + 2) != '\0') {
    uVar1 = FUN_00f92ff0();
    return uVar1;
  }
  return *(undefined4 *)(*(int *)(unaff_EDI + 0x38) + -1);
}



//===== FUN_00f8a2e3 @ 00f8a2e3 size=84 =====

void FUN_00f8a2e3(void)

{
  FUN_00f92480();
  FUN_00f92480();
  return;
}



//===== FUN_00f8a399 @ 00f8a399 size=46 =====

void FUN_00f8a399(void)

{
  char *pcVar1;
  byte bVar2;
  int unaff_ESI;
  
  bVar2 = *(byte *)(unaff_ESI + 0x11);
  if (bVar2 < 0x10) {
    pcVar1 = (char *)(*(byte *)(unaff_ESI + 0x10) + 0x14880fe1);
    *pcVar1 = (*pcVar1 - bVar2) - (bVar2 < 0x10);
    *(byte *)(unaff_ESI + 0x11) = bVar2 + 1;
  }
  else {
    FUN_00f93106();
  }
  return;
}



//===== FUN_00f8a95d @ 00f8a95d size=128 =====

void FUN_00f8a95d(void)

{
  byte bVar1;
  byte bVar2;
  int iVar3;
  int unaff_EDI;
  
  bVar2 = *(byte *)(unaff_EDI + 8);
  if (((bVar2 & 1) != 0) || (*(char *)(unaff_EDI + 0x1e) != '\0')) goto LAB_00f8a9d6;
  if (*(char *)(unaff_EDI + 0x1c) == '\0') {
    if (*(char *)(unaff_EDI + 0x43) == '\0') {
      if (*(char *)(unaff_EDI + 0x69) == '\0') {
        if ((*(char *)(unaff_EDI + 0x31) != '\0') && ((*(byte *)(unaff_EDI + 10) & 0x10) == 0)) {
          bVar2 = bVar2 - 1;
          iVar3 = unaff_EDI + 0x20;
          goto LAB_00f8a9b7;
        }
        if (*(char *)(unaff_EDI + 0x57) == '\0') {
          return;
        }
        if ((*(byte *)(unaff_EDI + 10) & 0x20) != 0) {
          return;
        }
        iVar3 = unaff_EDI + 0x46;
      }
      else {
        iVar3 = unaff_EDI + 0x58;
      }
      bVar2 = bVar2 - 1 | 0x20;
    }
    else {
      bVar2 = bVar2 - 2;
      iVar3 = unaff_EDI + 0x32;
    }
  }
  else {
    bVar2 = bVar2 - 1;
    iVar3 = unaff_EDI + 0xb;
  }
LAB_00f8a9b7:
  bVar1 = *(byte *)(iVar3 + 0x10);
  *(undefined1 *)(unaff_EDI + 9) = *(undefined1 *)(iVar3 + (uint)bVar1);
  *(char *)(iVar3 + 0x11) = *(char *)(iVar3 + 0x11) + -1;
  *(byte *)(iVar3 + 0x10) = bVar1 + 1 & 0xf;
  *(byte *)(unaff_EDI + 8) = bVar2 - 1 | 1;
LAB_00f8a9d6:
  FUN_00f8a2e3();
  return;
}



//===== FUN_00f8aa73 @ 00f8aa73 size=117 =====

int __fastcall FUN_00f8aa73(int param_1,undefined1 param_2)

{
  undefined4 in_EAX;
  int iVar1;
  undefined1 uVar2;
  int unaff_EDI;
  
  uVar2 = (undefined1)(param_1 + 5);
  iVar1 = CONCAT22((short)((uint)in_EAX >> 0x10),CONCAT11(param_2,(char)in_EAX)) + -2;
  if (*(byte *)(unaff_EDI + 0x57) + 4 < 0x11) {
    FUN_00f8a399();
    FUN_00f8a399();
    iVar1 = FUN_00f8a399();
    if (CONCAT22((short)((uint)(param_1 + 5) >> 0x10),CONCAT11(uVar2,uVar2)) == -2) {
      iVar1 = FUN_00f8a399();
    }
  }
  return iVar1;
}



//===== FUN_00f8ce48 @ 00f8ce48 size=112 =====

int FUN_00f8ce48(void)

{
  int iVar1;
  
  iVar1 = FUN_00f9002b(0xfffffff);
  return iVar1 + -1;
}



//===== FUN_00f8ceb8 @ 00f8ceb8 size=73 =====

void __fastcall FUN_00f8ceb8(undefined4 param_1,uint param_2)

{
  int *piVar1;
  ushort uVar2;
  int iVar3;
  int unaff_ESI;
  
  if ((*(char *)(unaff_ESI + 0xd) == '\0') && (param_2 < *(uint *)(unaff_ESI + 8))) {
    iVar3 = param_2 * 4 + -1;
    uVar2 = (ushort)iVar3;
    iVar3 = (CONCAT22((short)((uint)iVar3 >> 0x10),
                      uVar2 + (ushort)((int)(param_2 << 1) < 0) * ((uVar2 & 3) - (uVar2 & 3))) + -1)
            * 4 + unaff_ESI + 0x10;
    if ((*(uint *)(iVar3 + 0xc) & 1) == 0) {
      *(uint *)(unaff_ESI + 0x210 + param_2 * 4) = *(uint *)(iVar3 + 8) & 0xff;
      piVar1 = (int *)(unaff_ESI + 0x250 + param_2 * 4);
      *piVar1 = *piVar1 + 1;
      FUN_00f8ce48();
    }
  }
  return;
}



//===== FUN_00f8fadf @ 00f8fadf size=54 =====

int FUN_00f8fadf(void)

{
  int iVar1;
  int iVar2;
  int unaff_EDI;
  
  iVar1 = (int)(CONCAT44(unaff_EDI + -1 >> 0x1f,unaff_EDI + -2) / (longlong)DAT_0071fa50);
  iVar2 = (unaff_EDI - ((iVar1 + -2) * DAT_0071fa50 + -1)) * 1000000;
  return (int)(CONCAT44(iVar2 + -1 >> 0x1f,iVar2 + -2) / (longlong)DAT_0071fa50) + -2 +
         (iVar1 + -1) * 1000000;
}



//===== FUN_00f8fb15 @ 00f8fb15 size=10 =====

uint FUN_00f8fb15(void)

{
  undefined8 uVar1;
  
  uVar1 = rdtsc();
  return (int)uVar1 - 2U | (uint)((ulonglong)uVar1 >> 0x20);
}



//===== FUN_00f8fb1f @ 00f8fb1f size=16 =====

void __fastcall FUN_00f8fb1f(undefined4 param_1)

{
  FUN_00f8fb15(param_1);
  FUN_00f8fadf();
  return;
}



//===== FUN_00f8ff36 @ 00f8ff36 size=48 =====

void __fastcall FUN_00f8ff36(undefined4 param_1,int param_2)

{
  char *pcVar1;
  int unaff_ESI;
  
  pcVar1 = (char *)(unaff_ESI * 0x20 + -1);
  *pcVar1 = *pcVar1 + (char)pcVar1;
  *pcVar1 = *pcVar1 + (char)pcVar1;
                    /* WARNING: Could not recover jumptable at 0x00f8ff64. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (**(code **)(**(int **)(&WAVE_0094f848.field_0x2508 + (unaff_ESI * 0x20 + param_2) * 8) + 0x8c0))
            ();
  return;
}



//===== FUN_00f8ffb3 @ 00f8ffb3 size=39 =====

int FUN_00f8ffb3(void)

{
  int iVar1;
  
  iVar1 = FUN_00f8ff36(0xffffffff);
  return iVar1 + -1;
}



//===== FUN_00f9002b @ 00f9002b size=180 =====

/* WARNING: Unable to track spacebase fully for stack */

void __fastcall FUN_00f9002b(int param_1,uint param_2)

{
  uint uVar1;
  int iVar2;
  int iVar3;
  int iVar4;
  int unaff_ESI;
  
  iVar2 = param_1 + 3;
  uVar1 = param_2;
  if (param_2 == 0xffff) {
    iVar2 = param_1 + 4;
    param_2 = 0x1f;
    uVar1 = 0;
  }
  while( true ) {
    if (param_2 < uVar1) {
      return;
    }
    iVar4 = WAVE_0094f848._9492_4_ * 0x30;
    iVar3 = iVar2 + 1;
    if ((param_2 == 0xffff) &&
       (iVar3 = iVar2, *(int *)(&WAVE_0094f848.field_0x740f + unaff_ESI * 0x100 + uVar1 * 8) == 2))
    break;
    *(int *)(iVar4 + 0x959768) =
         *(int *)(&WAVE_0094f848.field_0x740f + unaff_ESI * 0x100 + uVar1 * 8) + -3;
    *(undefined4 *)(iVar4 + 0x959770) = 1;
    *(int *)(iVar4 + 0x959774) = unaff_ESI;
    *(int *)(iVar4 + 0x959778) = iVar3 + 1;
    *(uint *)(iVar4 + 0x959780) = uVar1 - 3;
    *(int *)(iVar4 + 0x959788) = iVar3 + 1;
    *(int *)(iVar4 + 0x95978f) = *(int *)(iVar4 + 0x959787) + -1;
    iVar2 = iVar3 + 3;
    WAVE_0094f848._9488_4_ = WAVE_0094f848._9488_4_ + 1;
    WAVE_0094f848._9492_4_ = 0;
    uVar1 = uVar1 - 2;
  }
  return;
}



//===== FUN_00f901a4 @ 00f901a4 size=77 =====

void __fastcall FUN_00f901a4(undefined4 param_1,undefined4 param_2)

{
  int iVar1;
  undefined4 uVar2;
  undefined4 unaff_ESI;
  undefined4 unaff_EDI;
  
  uVar2 = WAVE_0094f848._9492_4_;
  iVar1 = WAVE_0094f848._9492_4_ * 0x30;
  *(undefined4 *)(&WAVE_0094f848.field_0x9eef + iVar1) = unaff_EDI;
  *(undefined4 *)(&WAVE_0094f848.field_0x9ef7 + iVar1) = 2;
  *(undefined4 *)(&WAVE_0094f848.field_0x9efe + iVar1) = unaff_ESI;
  *(undefined4 *)(&WAVE_0094f848.field_0x9f05 + iVar1) = param_2;
  *(undefined4 *)(&WAVE_0094f848.field_0x9f14 + iVar1) = 0x959768;
  WAVE_0094f848._9488_4_ = uVar2 + 1;
  if (0xff < (uint)WAVE_0094f848._9488_4_) {
    WAVE_0094f848._9488_4_ = 0;
  }
  return;
}



//===== FUN_00f90510 @ 00f90510 size=70 =====

uint * FUN_00f90510(void)

{
  uint uVar1;
  uint uVar2;
  uint *puVar3;
  uint *puVar4;
  uint unaff_EDI;
  
  puVar4 = (uint *)&WAVE_0094f848.field_0xcff0;
  uVar2 = DAT_0072c24b;
  while( true ) {
    do {
      uVar1 = uVar2;
      if (uVar1 == 1) {
        return (uint *)0x0;
      }
      uVar2 = uVar1 - 2 >> 1;
      puVar3 = puVar4 + uVar2 * 6;
    } while (unaff_EDI < *puVar3);
    if (unaff_EDI <= puVar3[2]) break;
    puVar4 = puVar3 + 6;
    uVar2 = (uVar1 - 10) - (uVar2 + 1);
  }
  return puVar3;
}



//===== FUN_00f90da4 @ 00f90da4 size=40 =====

uint FUN_00f90da4(void)

{
  uint uVar1;
  uint unaff_ESI;
  int *unaff_EDI;
  
  uVar1 = 5;
  if (unaff_EDI != (int *)0x0) {
    uVar1 = unaff_EDI[4] - 1;
    if ((uVar1 & 1) == 0) {
      uVar1 = unaff_EDI[4] + -5 + ((unaff_ESI & 0xfffff000) - *unaff_EDI);
    }
  }
  return uVar1;
}



//===== FUN_00f9101b @ 00f9101b size=237 =====

/* WARNING: Unable to track spacebase fully for stack */

uint __fastcall FUN_00f9101b(undefined4 param_1,int param_2)

{
  int iVar1;
  int iVar2;
  uint uVar3;
  uint uVar4;
  uint uVar5;
  uint *unaff_EDI;
  
  *(undefined4 *)(param_2 + -0x10) = 0;
  uVar5 = param_2 + 1;
  while (uVar5 != 0) {
    *(undefined4 *)((int)unaff_EDI + -5) = 0xf9104e;
    iVar1 = FUN_00f90510();
    *(int *)(uVar5 - 8) = iVar1 + -1;
    *(undefined4 *)((int)unaff_EDI + -6) = 0xf9105d;
    iVar1 = FUN_00f90da4();
    iVar2 = iVar1 + -1;
    if (*(int *)(uVar5 - 8) == 0) {
      uVar4 = ((int)unaff_EDI + 0xffeU & 0xfffff000) - ((int)unaff_EDI + -3);
    }
    else {
      iVar2 = iVar1 + -3;
      uVar4 = (*(int *)(*(int *)(uVar5 - 8) + 8) - ((int)unaff_EDI + -3)) + 1;
    }
    uVar3 = uVar5;
    if (uVar4 < uVar5) {
      uVar3 = uVar4;
    }
    *(uint *)(uVar5 - 8) = uVar3;
    if (((iVar2 - 4U & 1) == 0) && ((iVar2 - 5U & 2) == 0)) {
      *(undefined4 *)((int)unaff_EDI + -10) = 0xf910e0;
      FUN_00f93913();
    }
    else {
      *(undefined4 *)((int)unaff_EDI + -10) = 0xf910b1;
      FUN_00f96bd4();
    }
    uVar5 = uVar5 - *(int *)(uVar5 - 8);
    iVar1 = *(int *)(uVar5 - 8);
    *(int *)(uVar5 - 0x10) = *(int *)(uVar5 - 0x10) + iVar1 + -1;
    unaff_EDI = (uint *)((int)unaff_EDI + iVar1 + -8);
  }
  return *unaff_EDI >> 8 & 0xff;
}



//===== FUN_00f91387 @ 00f91387 size=257 =====

undefined1 __fastcall FUN_00f91387(undefined4 param_1,uint param_2)

{
  int iVar1;
  int iVar2;
  int iVar3;
  uint uVar4;
  uint uVar5;
  
  *(undefined4 *)(param_2 - 0x18) = 0xffffffff;
  *(undefined1 *)(param_2 - 1) = 0;
  uVar5 = param_2;
  while (uVar5 != 0) {
    iVar1 = FUN_00f90510();
    *(int *)(param_2 - 0x10) = iVar1 + -1;
    iVar1 = FUN_00f90da4();
    iVar2 = iVar1 + -1;
    if (*(int *)(param_2 - 0x10) == 0) {
      uVar5 = (param_2 + 0x1000 & 0xfffff000) - param_2;
    }
    else {
      iVar2 = iVar1 + -3;
      uVar5 = (*(int *)(*(int *)(param_2 - 0x10) + 8) - param_2) + 1;
    }
    uVar4 = param_2;
    if (uVar5 < param_2) {
      uVar4 = uVar5;
    }
    *(uint *)(param_2 - 0x10) = uVar4;
    if (((iVar2 - 4U & 1) == 0) && ((iVar2 - 5U & 4) == 0)) {
      iVar2 = (param_2 & 0xfff) + (iVar2 - 8U & 0xfffff000);
      iVar1 = 0;
      if (iVar2 != 0) {
        iVar1 = iVar2 + *(int *)(param_2 - 0x18);
      }
      FUN_00f93931();
    }
    else {
      iVar1 = 3;
      FUN_00f96bd4();
      *(undefined1 *)(param_2 - 1) = 1;
    }
    iVar2 = *(int *)(param_2 - 0x10);
    iVar3 = *(int *)(param_2 - 0x10) + -1;
    *(int *)(param_2 - 0x18) = *(int *)(param_2 - 0x18) + iVar3;
    param_2 = param_2 + iVar3;
    uVar5 = iVar1 - iVar2;
  }
  return *(undefined1 *)(param_2 - 1);
}



//===== FUN_00f921ae @ 00f921ae size=1 =====

void FUN_00f921ae(void)

{
  return;
}



//===== FUN_00f923ca @ 00f923ca size=112 =====

/* WARNING: Unable to track spacebase fully for stack */

void __fastcall FUN_00f923ca(undefined4 param_1,uint param_2)

{
  uint uVar1;
  uint *puVar2;
  uint *puVar3;
  uint uVar4;
  int iVar5;
  undefined1 *unaff_EDI;
  
  uVar1 = param_2 - 2;
  if (param_2 != 1 && uVar1 != 0) {
    if (2 < uVar1 && param_2 != 5) {
      return;
    }
    uVar1 = param_2 - 6;
    unaff_EDI = unaff_EDI + 1;
    param_2 = (uint)(byte)(&UNK_0041a3d3)[param_2];
  }
  uVar4 = 0;
  puVar3 = (uint *)unaff_EDI;
  while ((int)uVar4 < (int)*puVar3) {
    iVar5 = CONCAT22((short)(uVar4 >> 0x10),
                     (ushort)uVar4 +
                     (ushort)(*puVar3 < uVar4) * (((ushort)uVar1 & 3) - ((ushort)uVar4 & 3)));
    uVar1 = (int)puVar3 + (uVar1 - 1) * 0x10 + 7;
    puVar2 = (uint *)((int)puVar3 + 1);
    if ((*(uint *)(uVar1 + 0xc) & param_2) != 0) {
      param_2 = *(uint *)(uVar1 - 1);
      iVar5 = *(int *)(uVar1 + 6);
      puVar3[-1] = 0xf92427;
      uVar1 = FUN_00f901a4();
      puVar2 = puVar3;
    }
    puVar3 = puVar2;
    uVar4 = iVar5 + 1;
  }
  return;
}



//===== FUN_00f9243a @ 00f9243a size=40 =====

int FUN_00f9243a(void)

{
  int iVar1;
  uint unaff_EDI;
  
  if (unaff_EDI < 0x80) {
    iVar1 = FUN_00f923ca();
    return iVar1;
  }
  return unaff_EDI * 0x188 + 0xa24547;
}



//===== FUN_00f92479 @ 00f92479 size=7 =====

undefined2 FUN_00f92479(void)

{
  int unaff_EDI;
  
  return *(undefined2 *)(unaff_EDI + 2);
}



//===== FUN_00f92480 @ 00f92480 size=206 =====

/* WARNING: This function may have set the stack pointer */

void __fastcall FUN_00f92480(undefined4 param_1,uint param_2)

{
  byte *pbVar1;
  ushort uVar2;
  uint uVar3;
  int unaff_ESI;
  int unaff_EDI;
  
  pbVar1 = *(byte **)(unaff_ESI * 0x20 + *(int *)(unaff_EDI + 0x10) + 0x166);
  if (*pbVar1 == param_2) {
    return;
  }
  *pbVar1 = (byte)param_2;
  if (param_2 == 0) {
    uVar3 = (uint)*(ushort *)(pbVar1 + 4);
    pbVar1[4] = 0xff;
    pbVar1[5] = 0xff;
    if (uVar3 == 0xffff) {
      return;
    }
    *(int *)(&WAVE_00a18250.field_0xbdf3 + uVar3 * 4) =
         *(int *)(&WAVE_00a18250.field_0xbdf3 + uVar3 * 4) + -1;
    if (0 < *(int *)(uVar3 * 4)) {
      return;
    }
    if (*(int *)(uVar3 * 4) < 0) {
      *(undefined4 *)(&WAVE_00a18250.field_0xbdf2 + uVar3 * 4) = 0;
      WAVE_00a18250._48622_2_ = 0x253b;
      WAVE_00a18250._48624_2_ = 0xf9;
      FUN_00f921ae();
      return;
    }
  }
  else {
    WAVE_00a18250._48624_2_ = 0x24c7;
    WAVE_00a18250._48626_2_ = 0xf9;
    uVar2 = FUN_00f92479();
    *(ushort *)(pbVar1 + 4) = uVar2;
    if (uVar2 == 0xffff) {
      return;
    }
    *(int *)(&WAVE_00a18250.field_0xbdf3 + (uint)uVar2 * 4) =
         *(int *)(&WAVE_00a18250.field_0xbdf3 + (uint)uVar2 * 4) + 1;
    if (1 < *(int *)((uint)uVar2 * 4)) {
      return;
    }
  }
  WAVE_00a18250._48622_2_ = 0x2548;
  WAVE_00a18250._48624_2_ = 0xf9;
  FUN_00f9243a();
  return;
}



//===== FUN_00f92ff0 @ 00f92ff0 size=64 =====

int __fastcall FUN_00f92ff0(int param_1)

{
  int *piVar1;
  int unaff_ESI;
  int *unaff_EDI;
  
  param_1 = param_1 + -4;
  piVar1 = (int *)(unaff_ESI * 0x40 + *unaff_EDI + 0x20);
  if ((*piVar1 == 9) && ((piVar1[10] & 1U) != 0)) {
    if (piVar1[9] == 1) {
      param_1 = FUN_00f93913();
    }
    else {
      param_1 = FUN_00f9101b();
    }
  }
  return param_1;
}



//===== FUN_00f93030 @ 00f93030 size=76 =====

int __fastcall FUN_00f93030(int param_1)

{
  int *piVar1;
  int unaff_ESI;
  int *unaff_EDI;
  
  param_1 = param_1 + -4;
  piVar1 = (int *)(unaff_ESI * 0x40 + *unaff_EDI + 0x20);
  if ((*piVar1 == 9) && ((piVar1[10] & 2U) != 0)) {
    if (piVar1[9] == 1) {
      param_1 = FUN_00f93931();
    }
    else {
      param_1 = FUN_00f91387();
    }
  }
  return param_1;
}



//===== FUN_00f93095 @ 00f93095 size=28 =====

void FUN_00f93095(void)

{
  int unaff_ESI;
  int *unaff_EDI;
  
  if (*(int *)(unaff_ESI * 0x40 + *unaff_EDI + 0x1e) == 9) {
    FUN_00f93add();
    return;
  }
  return;
}



//===== FUN_00f93106 @ 00f93106 size=20 =====

void FUN_00f93106(void)

{
  FUN_00f93204();
  return;
}



//===== FUN_00f9311c @ 00f9311c size=143 =====

/* WARNING: Unable to track spacebase fully for stack */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 __fastcall FUN_00f9311c(undefined4 param_1,undefined4 param_2)

{
  ushort uVar1;
  int extraout_EDX;
  int iVar2;
  undefined4 *puVar3;
  undefined1 *unaff_ESI;
  byte bVar4;
  
  if (0x7f < (int)WAVE_00a433b8._38072_4_) {
    puVar3 = (undefined4 *)(unaff_ESI + -4);
    unaff_ESI = unaff_ESI + -4;
    *puVar3 = 0xf93148;
    FUN_00f93204();
  }
  bVar4 = 0;
  *(undefined4 *)(unaff_ESI + -6) = 0xf93175;
  FUN_00f61804();
  *(undefined4 *)(unaff_ESI + -6) = 0xf9317d;
  FUN_00f608ac();
  uVar1 = (ushort)(_DAT_00000067 + -1);
  iVar2 = extraout_EDX * 0x18;
  *(undefined1 **)(iVar2 + 0xa4c880) = unaff_ESI + -3;
  *(undefined4 *)(&WAVE_00a433b8.field_0x94d0 + iVar2) = param_2;
  _DAT_00000067 =
       CONCAT22((short)((uint)(_DAT_00000067 + -1) >> 0x10),
                uVar1 + (ushort)bVar4 * (((ushort)extraout_EDX & 3) - (uVar1 & 3))) + -3;
  return *(undefined4 *)(&WAVE_00a433b8.field_0x94c0 + iVar2);
}



//===== FUN_00f931ab @ 00f931ab size=34 =====

/* WARNING: Unable to track spacebase fully for stack */

void FUN_00f931ab(void)

{
  int unaff_ESI;
  
  *(undefined4 *)(unaff_ESI + -4) = 0xf931ba;
  FUN_00f60dbc();
  *(undefined4 *)(unaff_ESI + -5) = 0xf931c8;
  FUN_00f9311c();
  return;
}



//===== FUN_00f93204 @ 00f93204 size=335 =====

void FUN_00f93204(void)

{
  FUN_00f9a750();
  FUN_00f98130();
  FUN_00f9857d();
  FUN_00f9862c();
  FUN_00f9722a();
  FUN_00f96db8();
  do {
    FUN_00f65a8f();
  } while( true );
}



//===== FUN_00f934d4 @ 00f934d4 size=330 =====

/* WARNING: Unable to track spacebase fully for stack */

void FUN_00f934d4(void)

{
  int unaff_ESI;
  
  *(undefined4 *)(unaff_ESI + -4) = 0xf93566;
  FUN_00f9a750();
  *(undefined4 *)(unaff_ESI + -4) = 0xf935bb;
  FUN_00f98130();
  *(undefined4 *)(unaff_ESI + -5) = 0xf935da;
  FUN_00f9857d();
  *(undefined4 *)(unaff_ESI + -5) = 0xf935ed;
  FUN_00f9862c();
  *(undefined4 *)(unaff_ESI + -5) = 0xf93607;
  FUN_00f9722a();
  *(undefined4 *)(unaff_ESI + -5) = 0xf93619;
  FUN_00f96db8();
  return;
}



//===== FUN_00f938a1 @ 00f938a1 size=114 =====

/* WARNING: Unable to track spacebase fully for stack */

void __fastcall FUN_00f938a1(undefined4 *param_1,int param_2)

{
  undefined4 *puVar1;
  undefined4 uVar2;
  char cVar3;
  undefined4 unaff_EBX;
  undefined4 unaff_ESI;
  
  cVar3 = (char)((uint)unaff_EBX >> 8);
  *param_1 = 0xf938ba;
  puVar1 = (undefined4 *)FUN_00f93bb7();
  uVar2 = 5;
  if (cVar3 != '\0') {
    uVar2 = 6;
  }
  *puVar1 = uVar2;
  puVar1[6] = unaff_ESI;
  puVar1[8] = param_1 + 1;
  puVar1[9] = 0;
  if ((cVar3 == '\0') || (&DAT_00000010 < param_1 + 1)) {
    puVar1[2] = param_2;
  }
  else if (param_2 == 0) {
    *(undefined4 *)((int)param_1 + -1) = 0xf938f6;
    FUN_00f9a750();
  }
  else {
    *(undefined4 *)((int)param_1 + -2) = 0xf93904;
    FUN_00f60c60();
  }
  return;
}



//===== FUN_00f93913 @ 00f93913 size=30 =====

void __fastcall FUN_00f93913(char param_1)

{
  FUN_00f938a1();
  if (param_1 == '\0') {
    FUN_00f93ba1();
  }
  return;
}



//===== FUN_00f93931 @ 00f93931 size=74 =====

void __fastcall FUN_00f93931(undefined4 param_1,int param_2)

{
  char in_AL;
  char extraout_AH;
  int unaff_ESI;
  
  if (unaff_ESI == 0) {
    in_AL = (char)((uint)param_2 >> 8);
  }
  FUN_00f938a1();
  if ((extraout_AH == '\0') || ((in_AL != '\0' && (0x10 < param_2 + 1U)))) {
    FUN_00f93ba1();
  }
  return;
}



//===== FUN_00f93add @ 00f93add size=39 =====

void FUN_00f93add(void)

{
  undefined4 *puVar1;
  uint unaff_EDI;
  
  if ((unaff_EDI != 0) && (unaff_EDI != 1)) {
    puVar1 = (undefined4 *)FUN_00f93bb7();
    *puVar1 = 7;
    if (1 < unaff_EDI) {
      unaff_EDI = 2;
    }
    puVar1[2] = unaff_EDI;
  }
  return;
}



//===== FUN_00f93b40 @ 00f93b40 size=97 =====

/* WARNING: Unable to track spacebase fully for stack */

void FUN_00f93b40(void)

{
  int iVar1;
  undefined1 *unaff_ESI;
  int unaff_EDI;
  
  if ((unaff_EDI != 0) || (unaff_ESI != (undefined1 *)0x0)) {
    DAT_0060c008 = 1;
  }
  DAT_0060c004 = 0;
  do {
    *(undefined4 *)(unaff_ESI + -5) = 0xf93b81;
    iVar1 = FUN_00f62270();
    unaff_ESI = unaff_ESI + -1;
  } while (iVar1 == -1);
  DAT_0060c000 = 0;
  DAT_0060c004 = 0;
  DAT_0060c008 = 0;
  return;
}



//===== FUN_00f93ba1 @ 00f93ba1 size=22 =====

undefined4 FUN_00f93ba1(void)

{
  undefined4 uVar1;
  
  if (DAT_0060c000 != 0) {
    uVar1 = FUN_00f93b40();
    return uVar1;
  }
  return 0;
}



//===== FUN_00f93bb7 @ 00f93bb7 size=43 =====

undefined * FUN_00f93bb7(void)

{
  int iVar1;
  
  if (0x3e < DAT_0060c000) {
    FUN_00f93ba1();
    DAT_0060c000 = 0;
  }
  iVar1 = DAT_0060c000 - 1;
  DAT_0060c000 = DAT_0060c000 - 3;
  return &DAT_0060c040 + iVar1 * 0x28;
}



//===== FUN_00f96a34 @ 00f96a34 size=132 =====

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_00f96a34(void)

{
  ushort *puVar1;
  char *pcVar2;
  undefined4 uVar3;
  char cVar4;
  uint uVar5;
  bool bVar6;
  
  uVar5 = 0;
  while( true ) {
    uVar3 = WAVE_00a4c9e4._28840_4_;
    cVar4 = WAVE_00a4c9e4._28840_1_;
    *(char *)WAVE_00a4c9e4._28840_4_ = *(char *)WAVE_00a4c9e4._28840_4_ + cVar4;
    *(char *)uVar3 = *(char *)uVar3 + cVar4;
    bVar6 = uVar5 < (uint)uVar3;
    if ((int)uVar3 <= (int)uVar5) break;
    puVar1 = (ushort *)(&WAVE_00a4c9e4.field_0x70a0 + uVar3 * 4);
    *puVar1 = *puVar1 + (ushort)bVar6 * -(*puVar1 & 3);
    puVar1 = (ushort *)(&WAVE_00a4c9e4.field_0x70c4 + uVar3 * 4);
    *puVar1 = *puVar1 + (ushort)bVar6 * -(*puVar1 & 3);
    FUN_00f9862c();
    uVar5 = CONCAT22((short)(uVar5 >> 0x10),
                     (ushort)uVar5 + (ushort)bVar6 * (((short)uVar3 - 1U & 3) - ((ushort)uVar5 & 3))
                    ) + 1;
  }
  if (0 < (int)uVar3) {
    FUN_00f934d4();
  }
  pcVar2 = (char *)((int)ram0x0060b368 * 2);
  unique0x10000087 = pcVar2;
  *pcVar2 = *pcVar2 + (char)pcVar2;
  *pcVar2 = *pcVar2 + (char)pcVar2;
  if ("" < pcVar2 + -1) {
    ram0x0060b368 = "";
  }
  WAVE_00a4c9e4._28840_4_ = 0;
  return;
}



//===== FUN_00f96b16 @ 00f96b16 size=190 =====

/* WARNING: Unable to track spacebase fully for stack */
/* WARNING: This function may have set the stack pointer */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_00f96b16(void)

{
  int iVar1;
  char *pcVar2;
  undefined1 *puVar3;
  
  puVar3 = &WAVE_00a4c9e4.field_0x7094;
  if (WAVE_00a4c9e4._28820_4_ == 0) {
    WAVE_00a4c9e4._28815_4_ = 0xf96b57;
    FUN_00f61468();
    WAVE_00a4c9e4._28815_4_ = 0xf96b63;
    iVar1 = FUN_00f931ab();
    puVar3 = &WAVE_00a4c9e4.field_0x7093;
    pcVar2 = (char *)(iVar1 + -1);
    WAVE_00a4c9e4._28828_4_ = pcVar2;
    *pcVar2 = *pcVar2 + (char)pcVar2;
    *pcVar2 = *pcVar2 + (char)pcVar2;
  }
  *(undefined4 *)(puVar3 + -4) = 0xf96bad;
  FUN_00f6190c();
  *(undefined4 *)(puVar3 + -4) = 0xf96bc4;
  FUN_00f61838();
  WAVE_00a4c9e4._28836_4_ = 1;
  return;
}



//===== FUN_00f96bd4 @ 00f96bd4 size=325 =====

/* WARNING: Unable to track spacebase fully for stack */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_00f96bd4(void)

{
  undefined4 uVar1;
  char cVar2;
  ushort uVar3;
  undefined *puVar4;
  char *pcVar5;
  uint uVar6;
  uint extraout_ECX;
  uint uVar7;
  uint extraout_ECX_00;
  short sVar8;
  uint uVar9;
  undefined2 uVar10;
  undefined1 *puVar11;
  undefined1 *puVar12;
  undefined1 *unaff_ESI;
  undefined4 *puVar13;
  uint unaff_EDI;
  undefined *puVar14;
  
  *(undefined4 *)(unaff_ESI + -4) = 0xf96be7;
  puVar4 = (undefined *)FUN_00f8fb1f();
  uVar1 = WAVE_00a4c9e4._28812_4_;
  puVar13 = (undefined4 *)&WAVE_00a4c9e4.field_0x7084;
  if (WAVE_00a4c9e4._28840_4_ == 0) {
    cVar2 = WAVE_00a4c9e4._28812_1_;
    *(char *)WAVE_00a4c9e4._28812_4_ = *(char *)WAVE_00a4c9e4._28812_4_ + cVar2;
    *(char *)uVar1 = *(char *)uVar1 + cVar2;
    unaff_ESI = unaff_ESI + -1;
    if (&UNK_00e4e1bf + uVar1 < puVar4) {
      DAT_0060b367 = 500000;
    }
    pcVar5 = (char *)CONCAT13(UNK_0060b36b,DAT_0060b367._1_3_);
    cVar2 = (char)((uint)DAT_0060b367 >> 8);
    *pcVar5 = *pcVar5 + cVar2;
    *pcVar5 = *pcVar5 + cVar2;
    uVar7 = extraout_ECX - 1;
    pcVar5 = puVar4 + (int)pcVar5 * 4 + -1;
    WAVE_00a4c9e4._28796_4_ = pcVar5;
    *pcVar5 = *pcVar5 + (char)pcVar5;
    *pcVar5 = *pcVar5 + (char)pcVar5;
  }
  else {
    puVar4 = puVar4 + -1;
    uVar7 = extraout_ECX;
    if ((uint)WAVE_00a4c9e4._28804_4_ <= puVar4) {
      *(undefined4 *)(unaff_ESI + -4) = 0xf96c40;
      FUN_00f96a34();
      uVar7 = extraout_ECX_00;
    }
  }
  uVar9 = 0;
  do {
    uVar6 = WAVE_00a4c9e4._28840_4_;
    cVar2 = WAVE_00a4c9e4._28840_1_;
    *(char *)WAVE_00a4c9e4._28840_4_ = *(char *)WAVE_00a4c9e4._28840_4_ + cVar2;
    *(char *)uVar6 = *(char *)uVar6 + cVar2;
    puVar11 = unaff_ESI;
    if ((int)uVar6 <= (int)uVar9) {
LAB_00f96c8a:
      puVar12 = puVar11;
      if ((uVar9 == uVar6) && ((int)uVar6 < 10)) {
        uVar3 = (ushort)(uVar6 - 1);
        *(uint *)(&WAVE_00a4c9e4.field_0x70fc + uVar9 * 8) = unaff_EDI;
        *(undefined4 *)(&WAVE_00a4c9e4.field_0x70ac + uVar9 * 4) = 1;
        puVar12 = puVar11 + -1;
        pcVar5 = (char *)(CONCAT22((short)(uVar6 - 1 >> 0x10),
                                   uVar3 + (ushort)(uVar6 < 10) *
                                           (((ushort)uVar9 & 3) - (uVar3 & 3))) + -1);
        *(int *)(&WAVE_00a4c9e4.field_0x70d4 + uVar9 * 4) = 1 << ((byte)(puVar11 + -1) & 0x1f);
        WAVE_00a4c9e4._28840_4_ = pcVar5;
        *pcVar5 = *pcVar5 + (char)pcVar5;
        *pcVar5 = *pcVar5 + (char)pcVar5;
      }
      puVar14 = puVar4 + _DAT_003d4685;
      _DAT_0081cd99 = puVar4;
      *puVar13 = puVar14;
      uVar1 = WAVE_00a4c9e4._28796_4_;
      cVar2 = WAVE_00a4c9e4._28796_1_;
      *(char *)WAVE_00a4c9e4._28796_4_ = *(char *)WAVE_00a4c9e4._28796_4_ + cVar2;
      *(char *)uVar1 = *(char *)uVar1 + cVar2;
      if ((undefined *)(uVar1 + -1) < puVar14) {
        *puVar13 = (undefined *)(uVar1 + -1);
      }
      if (WAVE_00a4c9e4._28836_4_ == 0) {
        *(undefined4 *)(puVar12 + -7) = 0xf96d10;
        FUN_00f96b16();
      }
      return;
    }
    puVar13 = (undefined4 *)&WAVE_00a4c9e4.field_0x70fc;
    uVar10 = (undefined2)(uVar9 >> 0x10);
    sVar8 = (ushort)uVar9 + (ushort)(uVar9 < uVar6) * (((ushort)uVar7 & 3) - ((ushort)uVar9 & 3));
    uVar7 = *(uint *)(&WAVE_00a4c9e4.field_0x70fc + uVar7 * 8) ^ unaff_EDI;
    if ((uVar7 & 0xfffff000) == 0) {
      uVar6 = uVar6 - 5;
      uVar9 = CONCAT22(uVar10,sVar8);
      DAT_033a2610 = DAT_033a2610 + 1;
      puVar11 = unaff_ESI + -1;
      DAT_033a2638 = DAT_033a2638 | 1 << ((byte)(unaff_ESI + -1) & 0x1f);
      goto LAB_00f96c8a;
    }
    uVar9 = CONCAT22(uVar10,sVar8) + 1;
  } while( true );
}



//===== FUN_00f96d3f @ 00f96d3f size=53 =====

void FUN_00f96d3f(void)

{
  undefined4 uVar1;
  char cVar2;
  undefined4 unaff_EDI;
  
  uVar1 = WAVE_00a4c9e4._29012_4_;
  DAT_0060b3c8 = 0xffffffff;
  DAT_0060b388 = 0xfffffffe;
  DAT_0060b3a8 = 0xfffffffd;
  cVar2 = WAVE_00a4c9e4._29012_1_;
  DAT_0060b378 = unaff_EDI;
  *(char *)WAVE_00a4c9e4._29012_4_ = *(char *)WAVE_00a4c9e4._29012_4_ + cVar2;
  *(char *)uVar1 = *(char *)uVar1 + cVar2;
  if (uVar1 != 1) {
    FUN_00f6184c();
    return;
  }
  return;
}



//===== FUN_00f96d74 @ 00f96d74 size=68 =====

undefined * __fastcall FUN_00f96d74(undefined4 param_1,undefined4 param_2)

{
  undefined *puVar1;
  undefined2 unaff_SI;
  undefined4 unaff_EDI;
  
  puVar1 = (undefined *)0x1;
  if (DAT_0060e090 == 0) {
    puVar1 = &UNK_0060e095;
    DAT_0060e096 = unaff_EDI;
    DAT_0060e09f = unaff_SI;
    DAT_0060e0a2 = param_2;
    if (DAT_0060e088 == 0) {
      puVar1 = (undefined *)FUN_00f96d3f();
    }
    DAT_0060e088 = DAT_0060e088 + 1;
  }
  return puVar1 + -1;
}



//===== FUN_00f96db8 @ 00f96db8 size=25 =====

void FUN_00f96db8(void)

{
  rdtsc();
  FUN_00f96d74();
  return;
}



//===== FUN_00f96f93 @ 00f96f93 size=99 =====

/* WARNING: Unable to track spacebase fully for stack */
/* WARNING: Removing unreachable block (ram,0x00f96fea) */

void FUN_00f96f93(void)

{
  code *pcVar1;
  undefined4 uVar2;
  char cVar3;
  undefined1 *puVar4;
  undefined1 *puVar5;
  undefined1 *puVar6;
  undefined1 *puVar7;
  
  uVar2 = WAVE_00a4c9e4._29020_4_;
  puVar6 = &stack0xfffffffc;
  cVar3 = WAVE_00a4c9e4._29020_1_;
  *(char *)WAVE_00a4c9e4._29020_4_ = *(char *)WAVE_00a4c9e4._29020_4_ + cVar3;
  *(char *)uVar2 = *(char *)uVar2 + cVar3;
  WAVE_00a4c9e4._29020_4_ = WAVE_00a4c9e4._29020_4_ + 1;
  if (uVar2 == 0) {
    do {
      puVar4 = (undefined1 *)0x0;
      puVar7 = puVar6 + 1;
      while( true ) {
        puVar6 = puVar7 + -1;
        pcVar1 = *(code **)(*(int *)(puVar7 + (int)puVar4 * 8 + -0x19) + (int)puVar4 * 8);
        if (pcVar1 == (code *)0x0) break;
        puVar5 = puVar4 + -4;
        *(undefined4 *)(puVar4 + -4) = 0xf96fcb;
        (*pcVar1)();
        puVar4 = puVar5 + 1;
        puVar7 = puVar6;
      }
    } while( true );
  }
  return;
}



//===== FUN_00f970dc @ 00f970dc size=124 =====

undefined1 FUN_00f970dc(void)

{
  undefined1 uVar1;
  int iVar2;
  uint unaff_EBX;
  
  rdtsc();
  FUN_00f98585();
  if ((unaff_EBX < 0x400) && (iVar2 = FUN_00f9afbe(), unaff_EBX <= iVar2 - 1U)) {
    uVar1 = FUN_00f9af3f();
    return uVar1;
  }
  return 0;
}



//===== FUN_00f97158 @ 00f97158 size=210 =====

/* WARNING: Unable to track spacebase fully for stack */

undefined4 __fastcall FUN_00f97158(short param_1,undefined4 param_2)

{
  char *pcVar1;
  char cVar2;
  undefined4 uVar3;
  ushort uVar4;
  ushort uVar6;
  int unaff_EDI;
  byte bVar7;
  int iVar5;
  
  *(undefined4 *)(unaff_EDI + -4) = 0xf97187;
  FUN_00f9a750();
  pcVar1 = DAT_0060b3d0;
  cVar2 = (char)DAT_0060b3d0;
  *DAT_0060b3d0 = *DAT_0060b3d0 + cVar2;
  *pcVar1 = *pcVar1 + cVar2;
  if (*pcVar1 == '\0') {
    uVar3 = 0xb6;
  }
  else {
    uVar6 = param_1 - 0x1fe;
    *(undefined4 *)(unaff_EDI + -6) = 0xf971b6;
    FUN_00f9857d();
    bVar7 = 0;
    if (WAVE_00a4c9e4._30235_4_ != 0) {
      bVar7 = 0;
      uVar6 = 0;
      *(undefined4 *)(unaff_EDI + -6) = 0xf971d4;
      FUN_00f9862c();
    }
    uVar4 = (ushort)(unaff_EDI + -2);
    iVar5 = CONCAT22((short)((uint)(unaff_EDI + -2) >> 0x10),
                     uVar4 + (ushort)bVar7 * ((uVar6 & 3) - (uVar4 & 3)));
    *(undefined4 *)(iVar5 + -4) = 0xf971e3;
    cVar2 = FUN_00f970dc();
    pcVar1 = DAT_0060b3d0;
    if (cVar2 == '\0') {
      cVar2 = (char)DAT_0060b3d0;
      *DAT_0060b3d0 = *DAT_0060b3d0 + cVar2;
      *pcVar1 = *pcVar1 + cVar2;
      *(undefined4 *)(iVar5 + -4) = 0xf9720b;
      FUN_00f9862c();
      uVar3 = 1;
    }
    else {
      if ((char)((uint)param_2 >> 8) != '\0') {
        *(undefined4 *)(iVar5 + -4) = 0xf9721f;
        FUN_00f9b052();
      }
      uVar3 = 0;
    }
  }
  return uVar3;
}



//===== FUN_00f9722a @ 00f9722a size=194 =====

void FUN_00f9722a(void)

{
  FUN_00f97158();
  return;
}



//===== FUN_00f97984 @ 00f97984 size=397 =====

undefined4 * FUN_00f97984(void)

{
  byte *pbVar1;
  byte bVar2;
  byte bVar3;
  undefined4 uVar4;
  char cVar5;
  byte bVar6;
  int in_EAX;
  undefined4 *puVar7;
  char *pcVar8;
  uint uVar9;
  int *piVar10;
  byte bVar11;
  int *piVar12;
  int iVar14;
  int iVar15;
  int iVar16;
  int iVar17;
  int *unaff_EDI;
  bool bVar18;
  int *piVar13;
  
  uVar4 = WAVE_00a58590._32576_4_;
  iVar16 = 0xa60400;
  puVar7 = (undefined4 *)(in_EAX + -1);
  if ((((uint)WAVE_00a58590._32568_4_ <= unaff_EDI) &&
      (puVar7 = (undefined4 *)(in_EAX + -3), unaff_EDI < (uint)WAVE_00a58590._32576_4_)) &&
     (puVar7 = (undefined4 *)(in_EAX + -4), ((uint)unaff_EDI & 0xf) == 0)) {
    iVar15 = unaff_EDI[-2];
    puVar7 = (undefined4 *)0x0;
    if (iVar15 != 1) {
      pcVar8 = (char *)(iVar15 + -2);
      cVar5 = (char)pcVar8;
      *pcVar8 = *pcVar8 + cVar5;
      *(char *)(iVar15 + 0xfc18546) = *(char *)(iVar15 + 0xfc18546) + cVar5;
      *pcVar8 = *pcVar8 + cVar5;
      puVar7 = (undefined4 *)(iVar15 + -4);
      if ((uint)((int)unaff_EDI + iVar15 + -3) <= (uint)uVar4) {
        if (iVar15 - 5U < 0x110) {
          uVar9 = iVar15 - 6U >> 4;
          piVar12 = *(int **)(&WAVE_00a58590.field_0x7e88 + uVar9 * 8);
          puVar7 = (undefined4 *)(uVar9 - 2);
          if (piVar12 != unaff_EDI) {
            if (piVar12 == (int *)0x0) {
              *unaff_EDI = *(int *)(&WAVE_00a58590.field_0x7e6f + uVar9 * 8);
              puVar7 = (undefined4 *)(&WAVE_00a58590.field_0x7e6d + uVar9 * 8);
              *puVar7 = unaff_EDI;
            }
            else {
              iVar16 = *piVar12;
              *unaff_EDI = iVar16 + -1;
              puVar7 = (undefined4 *)(iVar16 + -2);
              *piVar12 = (int)unaff_EDI;
            }
          }
        }
        else {
          piVar12 = (int *)WAVE_00a58590._32392_4_;
          if (unaff_EDI < (uint)WAVE_00a58590._32392_4_) {
            do {
              piVar13 = (int *)piVar12[2];
              if (piVar13 <= unaff_EDI) break;
              bVar18 = piVar13 < piVar12;
              piVar12 = piVar13;
            } while (bVar18);
          }
          else {
            do {
              piVar13 = piVar12;
              piVar12 = (int *)*piVar13;
              if (piVar12 <= piVar13) break;
            } while (piVar12 <= unaff_EDI);
          }
          piVar12 = (int *)((int)piVar13 + -1);
          iVar15 = *(int *)((int)piVar13 + -9);
          if ((unaff_EDI < piVar12) ||
             (iVar15 = iVar15 + -1, (int *)((int)piVar12 + iVar15) <= unaff_EDI)) {
            piVar10 = (int *)0x0;
            iVar17 = -1;
            iVar14 = (int)piVar13 + -2;
            if (((int *)((int)piVar12 + iVar15) == unaff_EDI) &&
               (iVar14 = (int)piVar13 + -3, iVar15 != 0)) {
              iVar17 = -2;
              iVar16 = 0xf;
              piVar12 = piVar13 + -1;
              if (cRam75e3854d < '\0') {
                piVar12 = *(int **)((int)piVar13 + 0x1becb);
              }
              piVar10 = (int *)(iVar15 + -2);
              iVar14 = piVar12[2];
            }
            piVar12 = (int *)(iVar14 + -2);
            piVar13 = (int *)0x0;
            if ((char *)((int)piVar10 + piVar10[-2]) != (char *)0x0) {
              iVar17 = iVar17 + -1;
              iVar16 = 0xf;
              bVar6 = (byte)piVar10;
              *(byte *)piVar10 = (char)*piVar10 + bVar6;
              pbVar1 = (byte *)((int)piVar10 + 0x75d3854d);
              bVar2 = *pbVar1;
              *pbVar1 = *pbVar1 + bVar6;
              bVar11 = (byte)(iVar14 + -3);
              bVar3 = bVar11 - *(byte *)((int)piVar10 + -0x75);
              piVar12 = (int *)CONCAT31((int3)((uint)(iVar14 + -3) >> 8),
                                        (bVar3 - CARRY1(bVar2,bVar6)) +
                                        *(char *)((int)piVar10 + -0x77) +
                                        (bVar11 < *(byte *)((int)piVar10 + -0x75) ||
                                        bVar3 < CARRY1(bVar2,bVar6)));
              unaff_EDI = (int *)((int)unaff_EDI + -1);
              *(byte *)(piVar12 + -0x12) = *(byte *)(piVar12 + -0x12) | bVar6;
              *piVar10 = (int)(*piVar10 + (int)piVar10);
              *(byte *)piVar10 = (char)*piVar10 + bVar6;
              piVar10[2] = (int)unaff_EDI;
              *unaff_EDI = (int)piVar10;
              piVar13 = piVar10;
            }
            unaff_EDI[-2] = (int)piVar10 + -1;
            if ((iVar17 == 0) &&
               (piVar12 = (int *)((int)piVar12 + 1), (char *)((int)piVar10 + -1) == (char *)0x0)) {
              *piVar12 = (int)unaff_EDI;
              unaff_EDI[2] = (int)piVar12;
              piVar13[2] = (int)unaff_EDI;
              *unaff_EDI = (int)piVar13;
            }
          }
          puVar7 = (undefined4 *)(*(int *)((int)piVar12 + -1) + -1);
          *(undefined4 **)(iVar16 + 0x18) = puVar7;
        }
      }
    }
  }
  return puVar7;
}



//===== FUN_00f97b11 @ 00f97b11 size=516 =====

/* WARNING: Unable to track spacebase fully for stack */
/* WARNING: Removing unreachable block (ram,0x00f97c9e) */

undefined1 * FUN_00f97b11(void)

{
  int *piVar1;
  undefined4 uVar2;
  int iVar3;
  int iVar4;
  uint uVar5;
  undefined1 *puVar6;
  uint uVar7;
  uint *puVar8;
  int iVar9;
  int iVar10;
  uint uVar11;
  undefined1 *puVar12;
  undefined1 *puVar13;
  undefined1 *puVar14;
  undefined1 *puVar15;
  undefined1 *puVar16;
  int iVar17;
  int unaff_ESI;
  uint unaff_EDI;
  
  iVar3 = WAVE_00a58590._32376_4_ + -1;
  if (iVar3 == 0) {
    iVar3 = 0x1000;
    WAVE_00a58590._32376_4_ = 0x1000;
  }
  uVar11 = ~(iVar3 - 4U) & unaff_EDI + iVar3 + 0x6e;
  if ((-1 < (int)uVar11) && (unaff_EDI <= uVar11)) {
    *(undefined4 *)(unaff_ESI + -4) = 0xf97b59;
    iVar3 = FUN_00f62433();
    iVar3 = iVar3 + -1;
    if (iVar3 != -1) {
LAB_00f97b83:
      uVar2 = WAVE_00a58590._32607_4_;
      iVar4 = iVar3 + -2;
      uVar7 = iVar3 - 1U & 0xf;
      iVar10 = 0;
      if (uVar7 != 0) {
        iVar4 = iVar3 + -3;
        iVar10 = 0x10 - uVar7;
      }
      iVar4 = iVar4 + uVar11;
      puVar8 = (uint *)(WAVE_00a58590._32607_4_ + -1);
      uVar7 = *(uint *)(WAVE_00a58590._32607_4_ + 7);
      uVar5 = iVar4 - 1;
      if (uVar7 == uVar5) {
        puVar13 = (undefined1 *)(*(int *)(WAVE_00a58590._32607_4_ + 0x17) + -1);
        iVar4 = uVar5 - (*(int *)(WAVE_00a58590._32607_4_ + 0x17) + -1);
        iVar3 = 0xa603fd;
        *(int *)(WAVE_00a58590._32607_4_ + 7) = iVar4;
        iVar10 = uVar11 + iVar4 + -1;
        uVar7 = uVar5;
      }
      else {
        iVar3 = 0xa603fe;
        if (*puVar8 == uVar5) {
          *puVar8 = iVar4 - 2;
          iVar3 = 0xa603fd;
          puVar8 = (uint *)((*(int *)(uVar2 + 0xe) - (iVar4 + -3 + iVar10)) + -1);
          puVar13 = (undefined1 *)(*(int *)(uVar2 + 0xe) + 0xf);
          iVar10 = (int)puVar8 + (uVar11 - (iVar10 + 0xf));
        }
        else {
          iVar9 = iVar4 + iVar10;
          uVar7 = iVar4 - 4;
          iVar10 = uVar11 - (iVar10 + 0x10);
          puVar15 = (undefined1 *)(iVar9 + 0xe);
          puVar8 = (uint *)(WAVE_00a58590._32607_4_ + -2);
          if ((CONCAT13(WAVE_00a58590._32569_1_,WAVE_00a58590._32566_3_) != 0) ||
             (puVar8 = (uint *)(WAVE_00a58590._32607_4_ + -3), WAVE_00a58590._32574_4_ != 0)) {
            WAVE_00a58590._32615_1_ = WAVE_00a58590._32615_1_ + '\x01';
            puVar14 = (undefined1 *)(iVar9 + 0xd);
            iVar17 = iVar3;
            if (puVar8 == (uint *)&WAVE_00a58590.field_0x7f36) {
              iVar17 = 0xa603fd;
              puVar14 = (undefined1 *)(iVar9 + 0x3c);
              *(undefined4 *)(iVar9 + 0xc) = WAVE_00a58590._32565_4_;
              uVar7 = iVar4 - 6;
              iVar10 = iVar10 + -0x30;
            }
            *(undefined4 *)(puVar14 + 0xf) = 0;
            *(undefined4 *)(puVar14 + 0x17) = 0;
            *(undefined1 **)(puVar14 + 0x1f) = puVar14 + -3;
            iVar3 = iVar17 + -2;
            *(undefined1 **)(iVar17 + 0xee) = puVar14 + -1;
            puVar8 = (uint *)(puVar14 + -4);
            puVar15 = puVar14 + 0x2f;
            uVar7 = uVar7 - 2;
            iVar10 = iVar10 + -0x30;
          }
          puVar8[2] = uVar7;
          puVar13 = puVar15 + -2;
          *puVar8 = uVar7 - 1;
        }
      }
      iVar4 = (int)puVar8 + -1;
      if (*puVar8 < *(uint *)(iVar3 + 200)) {
        iVar4 = (int)puVar8 + -2;
        *(uint *)(iVar3 + 200) = *puVar8;
      }
      iVar9 = iVar4 + -1;
      if (*(uint *)(iVar3 + 0xd0) < uVar7) {
        iVar9 = iVar4 + -2;
        *(uint *)(iVar3 + 0xd0) = uVar7;
      }
      uVar11 = iVar10 + 0xfU & 0xfffffff0;
      iVar4 = iVar9 + -1;
      puVar16 = puVar13 + -1;
      puVar15 = *(undefined1 **)(iVar9 + 0xf);
      if ((puVar15 == (undefined1 *)0x0) || (iVar4 = iVar9 + -2, puVar13 + -1 < puVar15)) {
        *(undefined1 **)(iVar4 + 0x10) = puVar13 + -2;
        puVar16 = puVar13 + -3;
        puVar15 = puVar13 + -3;
      }
      piVar1 = (int *)(iVar4 + 0x18);
      if (*piVar1 == 1) {
LAB_00f97cd4:
        puVar6 = puVar16 + (uVar11 - 1);
        *(undefined1 **)(iVar4 + 0x17) = puVar6;
      }
      else {
        iVar4 = iVar4 + -1;
        puVar6 = (undefined1 *)(*piVar1 - 2);
        if (puVar6 < puVar16 + uVar11) goto LAB_00f97cd4;
      }
      if (puVar15 < *(undefined1 **)(iVar3 + 0xd8)) {
        *(undefined1 **)(iVar3 + 0xd8) = puVar15;
      }
      if (*(undefined1 **)(iVar3 + 0xe0) < puVar6) {
        *(undefined1 **)(iVar3 + 0xe0) = puVar6;
      }
      puVar12 = puVar16 + -1;
      *(uint *)(puVar16 + -9) = uVar11;
      *(undefined4 *)(puVar16 + -5) = 0xf97d09;
      FUN_00f97984();
      goto LAB_00f97d09;
    }
    if (unaff_ESI != 0) {
      uVar11 = unaff_EDI + 0x10 & 0xfffffff0;
      *(undefined4 *)(unaff_ESI + -4) = 0xf97b75;
      iVar3 = FUN_00f62433();
      iVar3 = iVar3 + -1;
      if (iVar3 != -1) goto LAB_00f97b83;
    }
  }
  puVar12 = (undefined1 *)0x0;
LAB_00f97d09:
  return puVar12 + 3;
}



//===== FUN_00f97d15 @ 00f97d15 size=612 =====

/* WARNING: Unable to track spacebase fully for stack */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 * __fastcall FUN_00f97d15(int param_1)

{
  uint uVar1;
  int *piVar2;
  int iVar3;
  int iVar4;
  uint uVar5;
  int iVar6;
  int *piVar15;
  int *piVar16;
  undefined1 *puVar17;
  undefined1 *puVar18;
  int iVar19;
  int iVar20;
  undefined4 *puVar21;
  uint unaff_EDI;
  bool bVar22;
  undefined4 *puVar7;
  undefined1 *puVar8;
  int iVar9;
  int iVar10;
  undefined1 *puVar11;
  undefined4 *puVar12;
  int iVar13;
  int iVar14;
  
  uVar5 = unaff_EDI + 0x17 & 0xfffffff0;
  if (uVar5 < unaff_EDI) {
    return (undefined4 *)0x0;
  }
  iVar3 = param_1 + 3;
  iVar19 = 0xa60400;
  if (uVar5 < 0x20) {
    uVar5 = 0x20;
  }
  else if (0x10f < uVar5) goto LAB_00f97d6d;
  iVar3 = param_1 + 2;
  uVar1 = uVar5 - 1 >> 4;
  puVar21 = *(undefined4 **)(&WAVE_00a58590.field_0x7e88 + uVar1 * 8);
  if (puVar21 != (undefined4 *)0x0) {
    *(undefined4 *)(&WAVE_00a58590.field_0x7e70 + uVar1 * 8) = *puVar21;
    return puVar21;
  }
LAB_00f97d6d:
  piVar2 = (int *)(WAVE_00a58590._32392_4_ + -1);
  piVar15 = piVar2;
  if (iVar3 != 2) goto LAB_00f97dc0;
  WAVE_00a58590._32368_1_ = 2;
  WAVE_00a58590._32371_1_ = 1;
  WAVE_00a58590._32369_1_ = 0x10;
  WAVE_00a58590._32370_1_ = 0x11;
  WAVE_00a58590._32608_4_ = 0xa604c8;
  WAVE_00a58590._32392_4_ = 0xa604b6;
  WAVE_00a58590._32549_4_ = 0xa604b5;
  WAVE_00a58590._32556_4_ = 0xa604b4;
  WAVE_00a58590._32539_4_ = 0;
  do {
    do {
      piVar2 = *(int **)(iVar19 + 0x18);
      piVar15 = piVar2;
LAB_00f97dc0:
      do {
        iVar3 = iVar19;
        iVar6 = (int)piVar15 + -1;
        puVar7 = (undefined4 *)((int)piVar15 + -1);
        puVar8 = (undefined1 *)((int)piVar15 + -1);
        iVar9 = (int)piVar15 + -1;
        iVar10 = (int)piVar15 + -1;
        puVar11 = (undefined1 *)((int)piVar15 + -1);
        puVar12 = (undefined4 *)((int)piVar15 + -1);
        iVar13 = (int)piVar15 + -1;
        iVar14 = (int)piVar15 + -1;
        iVar19 = iVar3 + -1;
        piVar15 = *(int **)((int)piVar15 + -1);
        uVar1 = piVar15[-2];
        piVar2 = (int *)((int)piVar2 + -1);
        if (uVar5 <= uVar1) {
          iVar4 = uVar1 - uVar5;
          iVar20 = iVar3 + -2;
          iVar19 = *piVar15;
          *(int *)(iVar3 + 0x16) = iVar6;
          if ((iVar4 - 1U < 0x110) && (iVar19 == 1)) {
            *puVar7 = 0;
            _DAT_00000008 = puVar8;
            return (undefined4 *)((int)piVar15 + -2);
          }
          bVar22 = (int)piVar15 + uVar1 != *(int *)(iVar3 + 0xde);
          if (bVar22) {
            puVar21 = (undefined4 *)((int)piVar15 + iVar4 + -4);
          }
          else {
            puVar21 = (undefined4 *)((int)piVar15 + -1);
            piVar15 = (int *)((int)piVar15 + (uVar5 - 1));
          }
          puVar21[-2] = uVar5;
          piVar15[-2] = iVar4 + -5;
          piVar2 = piVar15;
          if (!bVar22) {
            piVar2 = (int *)((int)piVar15 + -1);
            *(int *)iVar9 = (int)piVar15 + -1;
            *(int *)((int)piVar15 + 7) = iVar10;
            *(int *)(iVar19 + 6) = (int)piVar15 + -1;
            iVar20 = iVar3 + -4;
            *(int *)((int)piVar15 + -1) = iVar19 + -2;
          }
          if (iVar19 + -2 == 0) {
            return puVar21;
          }
          uVar1 = uVar5 - 1 >> 4;
          iVar19 = (uVar1 - 1) / uVar5 - 1;
          if (0x22f < uVar1) {
            iVar19 = (int)(0xff / (ulonglong)uVar5);
          }
          iVar3 = uVar1 - 1;
          piVar16 = (int *)((int)piVar2 + -2);
          for (iVar19 = iVar19 + -4; iVar19 != 1; iVar19 = iVar19 + -5) {
            iVar4 = *(int *)(iVar20 + 0x20 + (iVar3 + -1) * 8);
            piVar16[-2] = uVar5;
            iVar20 = iVar20 + -1;
            *piVar16 = iVar4;
            puVar21 = (undefined4 *)((int)puVar21 + -2);
            *(int **)(iVar4 + (iVar3 + -2) * 8) = piVar16;
            piVar16 = (int *)((int)piVar16 + uVar5);
            iVar3 = (iVar3 + -3) - uVar5;
          }
          piVar16[-2] = iVar3 - 1U;
          if (iVar3 - 1U < 0x110) {
            _DAT_00000004 = puVar11;
            *puVar12 = 0xfffffffc;
            uVar5 = iVar3 - 3U >> 4;
            *(undefined4 *)((int)piVar16 + -1) = *(undefined4 *)(iVar20 + 0x20 + uVar5 * 8);
            *(undefined1 **)(iVar20 + 0x20 + (uVar5 - 1) * 8) = (undefined1 *)((int)piVar16 + -2);
            return puVar21;
          }
          *(undefined1 **)iVar13 = (undefined1 *)((int)piVar16 + -1);
          *(undefined4 *)((int)piVar16 + -1) = 0xfffffffc;
          *(int *)((int)piVar16 + 7) = iVar14;
          _DAT_00000004 = (undefined1 *)((int)piVar16 + -1);
          return puVar21;
        }
      } while (piVar15 != piVar2);
      piVar15[-1] = 0xf97f15;
      iVar4 = FUN_00f97b11();
    } while (iVar4 != 1);
    puVar17 = (undefined1 *)((int)piVar15 + -1);
    if ((undefined1 *)(iVar3 + 0xb6) == (undefined1 *)((int)piVar15 + -1)) {
      iVar19 = iVar3 + -2;
      puVar17 = *(undefined1 **)((int)piVar15 + -1);
    }
    do {
      iVar19 = iVar19 + -1;
      iVar4 = *(int *)(puVar17 + -1);
      puVar18 = (undefined1 *)(iVar4 + -1);
      if ((undefined1 *)(iVar4 + -1) <= puVar17 + -1) break;
      puVar18 = (undefined1 *)(iVar4 + -2);
      puVar17 = (undefined1 *)(iVar4 + -2);
    } while ((undefined1 *)(iVar3 + 0xb6) != (undefined1 *)(iVar4 + -2));
    *(undefined4 *)(puVar18 + -4) = 0xf97f63;
    iVar3 = FUN_00f97b11();
    if (iVar3 == 2) {
      return (undefined4 *)0x1;
    }
  } while( true );
}



//===== FUN_00f97f79 @ 00f97f79 size=30 =====

int FUN_00f97f79(void)

{
  int iVar1;
  
  FUN_00f60900();
  iVar1 = FUN_00f97d15();
  FUN_00f6092a();
  return iVar1 + -1;
}



//===== FUN_00f980c0 @ 00f980c0 size=39 =====

char * FUN_00f980c0(void)

{
  char *pcVar1;
  char *pcVar3;
  int unaff_ESI;
  char *unaff_EDI;
  char *pcVar2;
  
  pcVar3 = unaff_EDI + unaff_ESI;
  pcVar1 = unaff_EDI + -2;
  if (pcVar3 < unaff_EDI) {
    pcVar3 = (char *)0xffffffff;
    pcVar1 = unaff_EDI + -3;
  }
  do {
    pcVar2 = pcVar1;
    pcVar1 = pcVar2 + -1;
    if (pcVar3 <= pcVar1) break;
  } while (*pcVar1 != '\0');
  return pcVar2 + (-2 - (int)unaff_EDI);
}



//===== FUN_00f98130 @ 00f98130 size=60 =====

void __fastcall FUN_00f98130(undefined4 param_1,int param_2)

{
  char *unaff_ESI;
  char *unaff_EDI;
  
  while( true ) {
    if (param_2 == 0) {
      return;
    }
    *unaff_EDI = *unaff_ESI + -2;
    unaff_ESI = unaff_ESI + 1;
    if (*unaff_EDI == '\0') break;
    param_2 = param_2 + -1;
    unaff_EDI = unaff_EDI + 1;
  }
  do {
    *unaff_EDI = '\0';
    unaff_EDI = unaff_EDI + 1;
    param_2 = param_2 + -1;
  } while (param_2 != 0);
  return;
}



//===== FUN_00f98198 @ 00f98198 size=23 =====

char * FUN_00f98198(void)

{
  char *pcVar1;
  char *unaff_EDI;
  
  pcVar1 = unaff_EDI;
  do {
    pcVar1 = pcVar1 + -1;
  } while (*pcVar1 != '\0');
  return pcVar1 + (-3 - (int)unaff_EDI);
}



//===== FUN_00f984eb @ 00f984eb size=146 =====

/* WARNING: Unable to track spacebase fully for stack */

int __fastcall FUN_00f984eb(int param_1)

{
  int in_EAX;
  int iVar1;
  int iVar2;
  undefined1 *puVar3;
  undefined4 unaff_EBX;
  undefined1 *puVar4;
  int unaff_ESI;
  int unaff_EDI;
  
  puVar4 = (undefined1 *)(unaff_EDI + -4);
  *(undefined4 *)(unaff_EDI + -4) = unaff_EBX;
  *(undefined4 *)(in_EAX + -7) = 0;
  *(int *)(in_EAX + -0x1b) = unaff_EDI;
  *(int *)(in_EAX + -0x13) = unaff_ESI;
  if (unaff_ESI == 0) {
    if (param_1 != 1) {
      puVar4 = (undefined1 *)(unaff_EDI + -5);
    }
  }
  else {
    puVar4 = (undefined1 *)(unaff_EDI + -4);
    if (param_1 != -1) {
      puVar4 = (undefined1 *)(unaff_EDI + -5);
    }
  }
  *(undefined4 *)(puVar4 + -4) = 0xf98549;
  iVar1 = FUN_00f9974e();
  puVar3 = *(undefined1 **)(in_EAX + -0x1b);
  iVar2 = iVar1 + -2;
  if (*(int *)(in_EAX + -0x13) == 0) {
    puVar3 = puVar4 + unaff_ESI + -1;
    iVar2 = iVar1 + -4;
    if (unaff_ESI == 0) goto LAB_00f98565;
  }
  *puVar3 = 0;
LAB_00f98565:
  if (*(int *)(in_EAX + -7) != 0) {
    *(undefined4 *)(puVar4 + -4) = 0xf98576;
    iVar2 = (*(code *)(in_EAX + -4))();
  }
  return iVar2;
}



//===== FUN_00f9857d @ 00f9857d size=8 =====

void FUN_00f9857d(void)

{
  FUN_00f984eb();
  return;
}



//===== FUN_00f98585 @ 00f98585 size=165 =====

void FUN_00f98585(void)

{
  FUN_00f9857d();
  return;
}



//===== FUN_00f9862c @ 00f9862c size=177 =====

void FUN_00f9862c(void)

{
  FUN_00f99e5d();
  return;
}



//===== FUN_00f986e0 @ 00f986e0 size=245 =====

/* WARNING: Unable to track spacebase fully for stack */
/* WARNING: Removing unreachable block (ram,0x00f9871a) */
/* WARNING: Removing unreachable block (ram,0x00f9873f) */
/* WARNING: Removing unreachable block (ram,0x00f98752) */
/* WARNING: Removing unreachable block (ram,0x00f9875d) */
/* WARNING: Removing unreachable block (ram,0x00f98764) */
/* WARNING: Removing unreachable block (ram,0x00f9876a) */
/* WARNING: Removing unreachable block (ram,0x00f98775) */
/* WARNING: Removing unreachable block (ram,0x00f9878c) */
/* WARNING: Removing unreachable block (ram,0x00f98748) */
/* WARNING: Removing unreachable block (ram,0x00f98750) */
/* WARNING: Removing unreachable block (ram,0x00f987ab) */
/* WARNING: Removing unreachable block (ram,0x00f9879d) */
/* WARNING: Removing unreachable block (ram,0x00f987b7) */
/* WARNING: Removing unreachable block (ram,0x00f987c0) */
/* WARNING: Removing unreachable block (ram,0x00f98728) */
/* WARNING: Removing unreachable block (ram,0x00f98732) */
/* WARNING: Removing unreachable block (ram,0x00f987c3) */

undefined4 FUN_00f986e0(void)

{
  undefined4 unaff_EBX;
  int unaff_EDI;
  
  *(undefined4 *)(unaff_EDI + -4) = unaff_EBX;
  *(undefined4 *)(unaff_EDI + -8) = 0xf98711;
  FUN_00f61e3a();
  return 0xffffffff;
}



//===== FUN_00f98894 @ 00f98894 size=350 =====

/* WARNING: Unable to track spacebase fully for stack */

undefined1 * FUN_00f98894(void)

{
  int iVar1;
  uint uVar2;
  int iVar3;
  int iVar4;
  undefined1 *puVar5;
  undefined1 *puVar6;
  undefined1 *puVar7;
  int *unaff_ESI;
  int unaff_EDI;
  
  uVar2 = (uint)DAT_0060b418;
  if (((unaff_ESI < &WAVE_00a58590.field_0x7f70) ||
      (&WAVE_00a58590.field_0x7f54 + uVar2 * 0x18 <= unaff_ESI)) ||
     ((*(byte *)((int)unaff_ESI + 0x17) & 0x40) == 0)) {
    *(undefined4 *)(unaff_EDI + -4) = 0xf988d5;
    FUN_00f61e3a();
    puVar6 = (undefined1 *)0xffffffff;
    goto LAB_00f989e8;
  }
  unaff_ESI[4] = 0;
  puVar7 = (undefined1 *)((uint)(&WAVE_00a58590.field_0x7f54 + uVar2 * 0x18) >> 8 & 0xff);
  *(byte *)((int)unaff_ESI + 0x15) = *(byte *)((int)unaff_ESI + 0x15) | 0x40;
  if ((*(byte *)((int)unaff_ESI + 0x17) & 3) == 2) {
LAB_00f988f6:
    puVar6 = puVar7 + 1;
    *(undefined4 *)(puVar7 + -3) = 0xf98912;
    iVar3 = FUN_00f9a9e8();
    if (iVar3 + -1 < 1) {
      *(byte *)((int)unaff_ESI + 0x17) = *(byte *)((int)unaff_ESI + 0x17) | 8;
LAB_00f989aa:
      puVar6 = (undefined1 *)0xffffffff;
    }
  }
  else {
    iVar3 = unaff_ESI[2] + -1;
    if (iVar3 == 0) {
      *(undefined4 *)(puVar7 + -4) = 0xf98937;
      FUN_00f99e64();
      *(undefined4 *)(puVar7 + -4) = 0xf9893f;
      iVar3 = FUN_00f97f79();
      unaff_ESI[2] = iVar3 + -1;
      if (iVar3 == 2) {
        *(byte *)((int)unaff_ESI + 0x17) = *(byte *)((int)unaff_ESI + 0x17) & 0xfc;
        *(byte *)((int)unaff_ESI + 0x17) = *(byte *)((int)unaff_ESI + 0x17) | 2;
        goto LAB_00f988f6;
      }
      iVar3 = iVar3 + -3;
      *unaff_ESI = iVar3;
      *(byte *)((int)unaff_ESI + 0x17) = *(byte *)((int)unaff_ESI + 0x17) | 0x10;
    }
    if ((*(byte *)((int)unaff_ESI + 0x17) & 3) == 1) {
      iVar3 = *unaff_ESI;
      iVar1 = unaff_ESI[2];
      *(undefined4 *)(puVar7 + -6) = 0xf98974;
      iVar4 = FUN_00f99e64();
      if ((iVar4 - (iVar3 - iVar1)) + -1 < 1) {
        *(undefined4 *)(puVar7 + -7) = 0xf98985;
        iVar3 = FUN_00f98b98();
        if (iVar3 != 0) goto LAB_00f989aa;
      }
      puVar5 = (undefined1 *)(*unaff_ESI + -2);
      *unaff_ESI = *unaff_ESI;
      puVar6 = puVar7 + -2;
      *puVar5 = (char)((uint)puVar5 >> 8);
      if (puVar7 == (undefined1 *)0x2) {
        uRamfffffffc = 0xf989a5;
        iVar3 = FUN_00f98b98();
        puVar6 = (undefined1 *)0x0;
        if (iVar3 != 0) goto LAB_00f989aa;
      }
    }
    else {
      if (*unaff_ESI == iVar3 + -1) {
LAB_00f989c8:
        puVar5 = (undefined1 *)(*unaff_ESI + -2);
        *unaff_ESI = *unaff_ESI;
        puVar6 = puVar7 + 1;
        *puVar5 = (char)((uint)puVar5 >> 8);
      }
      else {
        *(undefined4 *)(puVar7 + -4) = 0xf989bd;
        iVar3 = FUN_00f98b98();
        if (iVar3 == 0) goto LAB_00f989c8;
        puVar6 = (undefined1 *)0xffffffff;
      }
      *(undefined4 *)(puVar6 + -4) = 0xf989dd;
      iVar3 = FUN_00f99e64();
      unaff_ESI[4] = iVar3 + -2;
    }
  }
  *(byte *)((int)unaff_ESI + 0x17) = *(byte *)((int)unaff_ESI + 0x17) & 0xdf;
LAB_00f989e8:
  return puVar6 + 5;
}



//===== FUN_00f989f4 @ 00f989f4 size=52 =====

int FUN_00f989f4(void)

{
  uint uVar1;
  int unaff_EDI;
  
  uVar1 = (uint)(CONCAT44(unaff_EDI + -0xa60502 >> 0x1f,unaff_EDI + -0xa60503) / 0x18);
  if (DAT_0060b418 < uVar1) {
    uVar1 = (uint)DAT_0060b418;
  }
  return (uVar1 - 1) * 8 + 0xa606df;
}



//===== FUN_00f98a5a @ 00f98a5a size=28 =====

int __fastcall FUN_00f98a5a(undefined4 param_1)

{
  int iVar1;
  int iVar2;
  
  iVar1 = FUN_00f989f4(param_1);
  iVar2 = 0;
  if ((iVar1 != 1) && (iVar2 = iVar1 + -3, *(int *)(iVar1 + -2) != 0)) {
    iVar2 = thunk_FUN_00f9a958();
  }
  return iVar2;
}



//===== FUN_00f98a76 @ 00f98a76 size=82 =====

undefined4 __fastcall FUN_00f98a76(undefined4 param_1)

{
  int iVar1;
  undefined4 uVar2;
  int unaff_EDI;
  
  iVar1 = (int)(CONCAT44(unaff_EDI + -0xa60502 >> 0x1f,unaff_EDI + -0xa60503) / 0x18);
  if (((uint)DAT_0060b418 < iVar1 - 1U) || ((&UNK_0060b427)[iVar1] == '\0')) {
    uVar2 = 0;
  }
  else {
    iVar1 = FUN_00f989f4(param_1);
    if ((iVar1 != 1) && (*(int *)(iVar1 + -2) != 0)) {
      thunk_FUN_00f9a958();
    }
    uVar2 = 1;
  }
  return uVar2;
}



//===== FUN_00f98ac8 @ 00f98ac8 size=28 =====

int __fastcall FUN_00f98ac8(undefined4 param_1)

{
  int iVar1;
  int iVar2;
  
  iVar1 = FUN_00f989f4(param_1);
  iVar2 = 0;
  if ((iVar1 != 1) && (iVar2 = iVar1 + -3, *(int *)(iVar1 + -2) != 0)) {
    iVar2 = thunk_FUN_00f9a98b();
  }
  return iVar2;
}



//===== FUN_00f98b98 @ 00f98b98 size=221 =====

uint * FUN_00f98b98(void)

{
  uint *puVar1;
  char cVar2;
  int iVar3;
  uint uVar4;
  uint *puVar5;
  uint *puVar6;
  uint *puVar7;
  
  puVar1 = (uint *)&WAVE_00a58590.field_0x7f70;
  puVar6 = (uint *)(&WAVE_00a58590.field_0x7f58 + (uint)DAT_0060b418 * 0x18);
  do {
    puVar5 = puVar1;
    cVar2 = FUN_00f98a76();
    puVar7 = puVar6;
    if (cVar2 != '\0') {
      if ((*(byte *)((int)puVar5 + 0x17) & 0x40) != 0) {
        uVar4 = puVar5[2];
        puVar7 = (uint *)((int)puVar6 + -1);
        if (uVar4 < *puVar5) {
          puVar7 = (uint *)((int)puVar6 + -2);
          do {
            iVar3 = FUN_00f9a9e8();
            if (iVar3 < 0) {
              *(byte *)((int)puVar5 + 0x17) = *(byte *)((int)puVar5 + 0x17) | 8;
              break;
            }
          } while (0 < (int)&stack0xffffffec);
          uVar4 = puVar5[2];
          *(byte *)((int)puVar5 + 0x15) = *(byte *)((int)puVar5 + 0x15) | 0x40;
          *puVar5 = uVar4;
        }
        puVar5[4] = 0;
        if ((*(byte *)((int)puVar5 + 0x17) & 0x80) == 0) {
          if ((uVar4 != 0) && ((*(byte *)((int)puVar5 + 0x17) & 3) == 0)) {
            uVar4 = FUN_00f99e64();
            puVar5[4] = uVar4;
          }
        }
        else {
          *(byte *)((int)puVar5 + 0x17) = *(byte *)((int)puVar5 + 0x17) | 0x20;
        }
      }
      FUN_00f98ac8();
    }
    puVar1 = puVar5 + 6;
    puVar6 = puVar7;
    if (puVar5 + 6 == puVar7) {
      return puVar5;
    }
  } while( true );
}



//===== thunk_FUN_00f99360 @ 00f9933c size=2 =====

char * thunk_FUN_00f99360(void)

{
  char *unaff_ESI;
  int unaff_EDI;
  
  for (; unaff_EDI != 0; unaff_EDI = (unaff_EDI - 1U) / 10 - 1) {
    unaff_ESI = unaff_ESI + -1;
    *unaff_ESI = (char)((ulonglong)(unaff_EDI - 1) % 10) + '0';
  }
  return unaff_ESI;
}



//===== FUN_00f99360 @ 00f99360 size=44 =====

char * FUN_00f99360(void)

{
  char *unaff_ESI;
  int unaff_EDI;
  
  for (; unaff_EDI != 0; unaff_EDI = (unaff_EDI - 1U) / 10 - 1) {
    unaff_ESI = unaff_ESI + -1;
    *unaff_ESI = (char)((ulonglong)(unaff_EDI - 1) % 10) + '0';
  }
  return unaff_ESI;
}



//===== FUN_00f9936a @ 00f9936a size=53 =====

/* WARNING: Unable to track spacebase fully for stack */

void __fastcall FUN_00f9936a(undefined4 param_1,int param_2)

{
  undefined1 *puVar1;
  undefined4 *puVar2;
  code *pcVar3;
  code *unaff_ESI;
  int unaff_EDI;
  
  puVar1 = (undefined1 *)(param_2 + -2);
  pcVar3 = *(code **)(unaff_EDI + 8);
  while (0 < (int)unaff_ESI) {
    puVar2 = (undefined4 *)(puVar1 + -5);
    puVar1 = puVar1 + -5;
    *puVar2 = 0xf9938d;
    (*pcVar3)();
    unaff_ESI = pcVar3;
    pcVar3 = pcVar3 + -1;
  }
  return;
}



//===== FUN_00f9939f @ 00f9939f size=10 =====

void FUN_00f9939f(void)

{
  FUN_00f9936a();
  return;
}



//===== FUN_00f993a9 @ 00f993a9 size=736 =====

/* WARNING: Unable to track spacebase fully for stack */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 FUN_00f993a9(void)

{
  ushort *puVar1;
  char cVar2;
  ushort uVar3;
  undefined1 *puVar4;
  undefined4 uVar5;
  undefined1 extraout_CL;
  int extraout_ECX;
  int extraout_ECX_00;
  uint uVar6;
  undefined1 *puVar7;
  undefined1 *puVar8;
  undefined1 *puVar9;
  undefined1 *puVar10;
  undefined4 *puVar11;
  undefined1 *puVar12;
  undefined1 *puVar13;
  undefined1 *puVar14;
  undefined1 *puVar15;
  undefined1 *puVar16;
  int iVar17;
  undefined1 *unaff_ESI;
  code *pcVar18;
  code *unaff_EDI;
  int iVar19;
  byte bVar20;
  bool bVar21;
  undefined8 uVar22;
  int3 iStack_27;
  undefined1 uStack_24;
  
  uVar6 = _DAT_00000004;
  if (unaff_ESI == (undefined1 *)0x0) {
    unaff_ESI = &DAT_00424468;
  }
  if (cRam00000021 == '\0') {
    if (cRam00000020 == '\0') {
      *(undefined4 *)(unaff_ESI + -4) = 0xf994ab;
      iVar19 = FUN_00f98198();
      *(undefined4 *)(iVar19 + -0x24) = 0;
      puVar4 = unaff_ESI + iVar19 + -2;
      *(undefined1 **)(iVar19 + -0x18) = puVar4;
      if (unaff_EDI[0x1f] == (code)0x0) {
LAB_00f994de:
        cVar2 = unaff_ESI[-1];
        puVar4 = (undefined1 *)CONCAT31((int3)((uint)puVar4 >> 8),cVar2);
        if (((cVar2 == '-') || (cVar2 == '+')) ||
           (puVar7 = unaff_ESI + -1, iVar17 = iVar19, cVar2 == ' ')) {
          iVar17 = iVar19 + -1;
          *(undefined4 *)(iVar19 + -9) = 1;
          puVar7 = unaff_ESI + -1;
        }
      }
      else {
        if (unaff_EDI[0x29] != (code)0x6f) {
          *(undefined4 *)(iVar19 + -0xc) = 2;
          goto LAB_00f994de;
        }
        unaff_ESI[-2] = 0x30;
        puVar7 = unaff_ESI + -2;
        iVar17 = iVar19 + 1;
      }
      if (uVar6 != 0xffff8300) {
        unaff_EDI[0x1c] = (code)0x0;
      }
      puVar4 = puVar4 + -1;
      pcVar18 = unaff_EDI + 0x18;
      *(ushort *)pcVar18 =
           *(ushort *)pcVar18 +
           (ushort)(uVar6 < 0xffff8300) * (((ushort)puVar4 & 3) - (*(ushort *)pcVar18 & 3));
      puVar16 = puVar4 + iVar17;
      if ((int)(puVar4 + iVar17) < (int)puVar4) {
        puVar16 = puVar4;
      }
      iVar19 = *(uint *)(puVar16 + -0xc) + *(uint *)(puVar16 + -8) + -1;
      uVar3 = (ushort)iVar19;
      puVar4 = (undefined1 *)
               CONCAT22((short)((uint)iVar19 >> 0x10),
                        uVar3 + (ushort)CARRY4(*(uint *)(puVar16 + -0xc),*(uint *)(puVar16 + -8)) *
                                ((uVar3 & 3) - (uVar3 & 3)));
      bVar20 = CARRY4((uint)puVar16,(uint)puVar4);
      puVar16 = puVar16 + (int)puVar4;
      goto LAB_00f99532;
    }
    iStack_27 = (int3)((char)unaff_EDI[0x22] >> 7);
    if (CONCAT13(uStack_24,iStack_27) == 0) {
      bVar20 = _DAT_00000004 < 0xffff8300;
      puVar7 = unaff_ESI;
      if (_DAT_00000004 == 0xffff8300) {
        *(undefined4 *)(unaff_ESI + -4) = 0xf99493;
        puVar16 = (undefined1 *)FUN_00f98198();
      }
      else {
        *(undefined4 *)(unaff_ESI + -4) = 0xf9948c;
        puVar16 = (undefined1 *)FUN_00f980c0();
      }
    }
    else {
      puVar16 = (undefined1 *)0x0;
      puVar4 = _SUB_00000000;
      while( true ) {
        puVar7 = unaff_ESI + -1;
        if (puVar4 <= puVar16) break;
        *(undefined4 *)(unaff_ESI + -5) = 0xf99442;
        uVar22 = FUN_00f9a44c();
        iVar19 = (int)uVar22;
        if (iVar19 < 1) {
          puVar7 = unaff_ESI + -1;
          if (iVar19 < 0) {
            return 0xffffffff;
          }
          break;
        }
        puVar7 = unaff_ESI + -2;
        unaff_ESI = unaff_ESI + -2;
        if ((undefined1 *)(extraout_ECX + -1) < puVar16 + (int)((ulonglong)uVar22 >> 0x20)) break;
        uVar3 = (ushort)(iVar19 + -3);
        puVar4 = (undefined1 *)
                 CONCAT22((short)((uint)(iVar19 + -3) >> 0x10),
                          uVar3 + (ushort)(puVar16 + (int)((ulonglong)uVar22 >> 0x20) <
                                          (undefined1 *)(extraout_ECX + -1)) *
                                  ((uVar3 & 3) - (uVar3 & 3)));
        puVar16 = puVar16 + (int)puVar4;
      }
      bVar20 = puVar16 != (undefined1 *)0xffffffff;
      if (puVar16 == (undefined1 *)0xffffffff) {
        return 0xffffffff;
      }
    }
  }
  else {
    puVar16 = (undefined1 *)0x1;
    bVar20 = 0;
    puVar7 = unaff_ESI + 1;
    if (_DAT_ffffffdd != 0) {
      *(undefined4 *)(unaff_ESI + -3) = 0xf99410;
      FUN_00f9a468();
      _DAT_ffffffdd = 0;
      puVar7 = (undefined1 *)0xffffffba;
    }
  }
  unaff_EDI = unaff_EDI + -1;
  puVar4 = puVar7 + (int)puVar16 + -1;
  *(undefined1 **)(puVar16 + -0x18) = puVar4;
LAB_00f99532:
  puVar1 = (ushort *)(puVar16 + -0x10);
  *puVar1 = *puVar1 + (ushort)bVar20 * (((ushort)(puVar4 + -1) & 3) - (*puVar1 & 3));
  puVar9 = puVar7 + -1;
  if (puVar4 + -1 < puVar16) {
    *(undefined1 **)(puVar16 + -0x10) = puVar16;
    puVar9 = puVar7;
  }
  *(int *)(puVar16 + -0x20) = *(int *)(unaff_EDI + 8) + -1;
  uVar5 = *(undefined4 *)(puVar16 + -0x10);
  pcVar18 = *(code **)(unaff_EDI + 0x10);
  if (pcVar18 != (code *)0x0) {
    *(undefined4 *)(puVar16 + -4) = 0;
    if (unaff_EDI[0x1d] == (code)0x0) {
      if (unaff_EDI[0x1c] == (code)0x0) {
        pcVar18 = (code *)((uint)pcVar18 & 0xffff);
        *(undefined4 *)(puVar9 + -4) = 0xf99586;
        FUN_00f9939f();
      }
    }
    else {
      *(code **)(puVar16 + -4) = pcVar18;
    }
    if (*(int *)(puVar16 + -8) != 0) {
      unaff_EDI = *(code **)(puVar16 + -0x20);
      puVar16 = puVar16 + -1;
      puVar8 = puVar9 + -4;
      *(undefined4 *)(puVar9 + -4) = 0xf9959b;
      (*unaff_EDI)();
      puVar9 = puVar8 + 1;
      pcVar18 = unaff_EDI;
    }
    if (*(int *)(puVar16 + -0xc) == 2) {
      pcVar18 = *(code **)(puVar16 + -0x20);
      puVar10 = puVar9 + -4;
      *(undefined4 *)(puVar9 + -4) = 0xf995b4;
      (*pcVar18)();
      unaff_EDI = *(code **)(puVar16 + -0x21);
      puVar16 = puVar16 + -2;
      puVar9 = puVar10 + -4;
      *(undefined4 *)(puVar10 + -4) = 0xf995c3;
      (*unaff_EDI)();
      pcVar18 = unaff_EDI;
    }
    *(undefined4 *)(puVar9 + -4) = 0xf995d3;
    FUN_00f9936a();
    if (*(int *)(puVar16 + -0x24) == 0) {
      puVar13 = puVar9 + 1;
      uVar6 = (uint)CONCAT11(puVar16[-0x24],extraout_CL);
      if (*(int *)(unaff_EDI + 0x18) != 0) {
        puVar13 = puVar9 + 2;
        uVar6 = (uint)(byte)((char)(CONCAT11(unaff_EDI[0x29],extraout_CL) + 1 >> 8) - 8) << 8;
      }
      while( true ) {
        uVar3 = (ushort)pcVar18;
        puVar15 = puVar13 + -1;
        bVar21 = puVar13 + -1 < *(undefined1 **)(puVar16 + -0x18);
        puVar4 = puVar16;
        if (!bVar21) break;
        bVar20 = (byte)(uVar6 >> 8);
        if (puVar13[-1] == bVar20) {
          pcVar18 = unaff_EDI + 0x18;
          *(ushort *)pcVar18 =
               *(ushort *)pcVar18 +
               (ushort)((byte)puVar13[-1] < bVar20) * ((uVar3 & 3) - (*(ushort *)pcVar18 & 3));
          *(undefined4 *)(puVar13 + -5) = 0xf99656;
          FUN_00f9936a();
        }
        unaff_EDI = *(code **)(puVar16 + -0x1f);
        puVar14 = puVar13 + -5;
        *(undefined4 *)(puVar13 + -5) = 0xf99665;
        (*unaff_EDI)();
        uVar6 = extraout_ECX_00 - 1;
        puVar13 = puVar14 + 1;
        pcVar18 = unaff_EDI;
      }
    }
    else {
      *(undefined1 **)(puVar16 + -0x38) = puVar9 + -1;
      puVar7 = puVar9;
      while( true ) {
        puVar15 = puVar7 + -1;
        uVar3 = (ushort)pcVar18;
        bVar21 = false;
        puVar4 = puVar16;
        if (puVar16 == (undefined1 *)0x0) break;
        pcVar18 = (code *)(puVar16 + -0x38);
        uVar3 = (ushort)pcVar18;
        *(undefined4 *)(puVar7 + -5) = 0xf9960d;
        FUN_00f9a44c();
        puVar15 = puVar7 + -2;
        puVar12 = puVar7 + -2;
        puVar4 = puVar16 + -1;
        bVar21 = puVar7 + -2 < puVar4;
        if (puVar4 < puVar7 + -2) break;
        puVar16 = puVar16 + (-2 - (int)(puVar7 + -2));
        if (puVar7 == (undefined1 *)0x2) {
          puVar12 = (undefined1 *)(int)(char)unaff_EDI[0x21];
          puVar16 = (undefined1 *)0x0;
        }
        puVar16 = puVar16 + 1;
        bVar20 = 0;
        iVar19 = 0;
        while( true ) {
          uVar3 = (ushort)iVar19;
          puVar4 = (undefined1 *)
                   CONCAT22((short)((uint)iVar19 >> 0x10),
                            uVar3 + (ushort)bVar20 * ((uVar3 & 3) - (uVar3 & 3)));
          bVar20 = puVar4 < puVar12 + -1;
          puVar7 = puVar12;
          if (!(bool)bVar20) break;
          cVar2 = (puVar16 + -0x2a)[(int)puVar4];
          unaff_EDI = *(code **)(puVar16 + -0x20);
          puVar16 = puVar16 + -1;
          puVar11 = (undefined4 *)(puVar12 + -5);
          puVar12 = puVar12 + -5;
          *puVar11 = 0xf995ef;
          (*unaff_EDI)();
          iVar19 = cVar2 + 1;
          pcVar18 = unaff_EDI;
        }
      }
    }
    puVar1 = (ushort *)(puVar4 + -4);
    *puVar1 = *puVar1 + (ushort)bVar21 * ((uVar3 & 3) - (*puVar1 & 3));
    *(undefined4 *)(puVar15 + -4) = 0xf9967b;
    FUN_00f9939f();
    uVar5 = *(undefined4 *)(puVar4 + -0x10);
  }
  return uVar5;
}



//===== FUN_00f99689 @ 00f99689 size=65 =====

/* WARNING: Unable to track spacebase fully for stack */

void __fastcall FUN_00f99689(undefined4 param_1,int param_2)

{
  int iVar1;
  int unaff_EDI;
  
  *(undefined4 *)(unaff_EDI + -4) = 0xf996a9;
  iVar1 = thunk_FUN_00f99360();
  if (param_2 != 0) {
    *(char *)(iVar1 + -2) = (char)param_2;
  }
  *(undefined1 *)(unaff_EDI + 0x1e) = 0;
  *(undefined4 *)(unaff_EDI + -5) = 0xf996c5;
  FUN_00f993a9();
  return;
}



//===== FUN_00f996ca @ 00f996ca size=71 =====

char * __fastcall FUN_00f996ca(undefined4 param_1,char *param_2)

{
  char cVar1;
  char cVar2;
  uint uVar3;
  sbyte sVar4;
  uint unaff_ESI;
  int unaff_EDI;
  uint uVar5;
  
  cVar1 = *(char *)(unaff_EDI + 0x29) + -0x51;
  sVar4 = 4;
  uVar5 = 0xf;
  if (*(char *)(unaff_EDI + 0x29) == 'o') {
    sVar4 = 3;
    uVar5 = 7;
  }
  for (; unaff_ESI != 0; unaff_ESI = unaff_ESI >> sVar4) {
    uVar3 = (unaff_ESI & uVar5) + 0x30;
    cVar2 = (char)uVar3;
    if (0x39 < uVar3) {
      cVar2 = cVar2 + cVar1 + -1;
    }
    param_2 = param_2 + -1;
    *param_2 = cVar2;
    cVar1 = cVar1 + -4;
  }
  return param_2;
}



//===== FUN_00f99711 @ 00f99711 size=61 =====

void FUN_00f99711(void)

{
  int unaff_ESI;
  int unaff_EDI;
  
  if ((unaff_ESI == 0) && ((*(int *)(unaff_EDI + 4) != 0 || (*(char *)(unaff_EDI + 0x29) != 'o'))))
  {
    *(undefined1 *)(unaff_EDI + 0x1f) = 0;
  }
  FUN_00f996ca();
  FUN_00f993a9();
  return;
}



//===== FUN_00f9974e @ 00f9974e size=1439 =====

/* WARNING: Unable to track spacebase fully for stack */

int __fastcall FUN_00f9974e(int param_1,int param_2)

{
  char cVar1;
  short sVar2;
  int in_EAX;
  undefined4 *puVar3;
  undefined4 *puVar4;
  int *piVar5;
  undefined3 uVar11;
  uint uVar6;
  ushort *puVar7;
  int iVar8;
  uint *puVar9;
  int iVar10;
  code *pcVar12;
  undefined1 *puVar13;
  int *piVar14;
  uint uVar15;
  undefined4 unaff_EBX;
  undefined1 *puVar16;
  char *pcVar17;
  char *pcVar18;
  char *pcVar19;
  code *unaff_ESI;
  undefined4 unaff_EDI;
  bool bVar20;
  
  pcVar12 = (code *)(param_1 + 1);
  puVar16 = (undefined1 *)(param_2 + -4);
  *(undefined4 *)(param_2 + -4) = unaff_EBX;
  puVar3 = (undefined4 *)(in_EAX + -3);
  *(undefined4 *)(in_EAX + -7) = 0;
  if (param_2 == 0) {
    puVar16 = &DAT_00424468;
  }
  *(undefined4 *)(in_EAX + -0x3b) = unaff_EDI;
  *(code **)(in_EAX + -0x33) = unaff_ESI;
  pcVar19 = puVar16;
LAB_00f99cd3:
  while (cVar1 = *pcVar19, cVar1 != '\0') {
    if (cVar1 == '%') {
      puVar4 = puVar3 + -10;
      puVar3[-0xf] = 0xffff8300;
      pcVar18 = pcVar19 + 1;
      while (puVar4 = (undefined4 *)((int)puVar4 + -2),
            puVar4 <= (undefined4 *)((int)puVar3 + -0x17)) {
        *(undefined1 *)puVar4 = 0;
      }
      do {
        cVar1 = *pcVar18;
        puVar4 = (undefined4 *)CONCAT31((int3)((uint)puVar4 >> 8),cVar1);
        if (cVar1 == '-') {
          *(undefined1 *)((int)puVar3 + -0x23) = 0x2d;
        }
        else if (cVar1 == '+') {
LAB_00f997f6:
          *(char *)((int)puVar3 + -0x22) = cVar1;
        }
        else if (cVar1 == '0') {
          *(undefined1 *)(puVar3 + -9) = 0x30;
        }
        else if (cVar1 == ' ') {
          if (*(char *)((int)puVar3 + -0x22) == '\0') goto LAB_00f997f6;
        }
        else {
          if (cVar1 != '#') goto LAB_00f99808;
          *(undefined1 *)((int)puVar3 + -0x21) = 0x23;
        }
        pcVar18 = pcVar18 + 1;
      } while( true );
    }
    pcVar17 = pcVar19;
    if (unaff_ESI != (code *)0x0) {
      pcVar12 = (code *)(int)(char)(cVar1 + -1);
      puVar3 = (undefined4 *)((int)puVar3 + -1);
      pcVar17 = pcVar19 + -5;
      pcVar19[-0xffffffff00000005] = -0x5b;
      pcVar19[-0xffffffff00000004] = -0x69;
      pcVar19[-0xffffffff00000003] = -7;
      pcVar19[-0xffffffff00000002] = '\0';
      (*pcVar12)();
      unaff_ESI = pcVar12;
    }
    puVar3[-1] = puVar3[-1] + 1;
    pcVar19 = pcVar17 + 1;
  }
LAB_00f99cdf:
  return puVar3[-1];
LAB_00f99808:
  puVar13 = (undefined1 *)0x0;
  if (cVar1 == '*') {
    *(ushort *)pcVar12 = *(ushort *)pcVar12;
    if ((int)((int)puVar4 + -2) < 0x30) {
      piVar5 = (int *)((int)puVar4 + *(int *)(pcVar12 + 0x10) + -4);
      *(undefined1 **)pcVar12 = (undefined1 *)((int)puVar4 + 5);
    }
    else {
      piVar5 = (int *)(*(int *)(pcVar12 + 8) + -2);
      *(int *)(pcVar12 + 8) = *(int *)(pcVar12 + 8) + 7;
    }
    iVar10 = *piVar5;
    puVar3[-0x10] = iVar10;
    if (iVar10 < 0) {
      puVar3[-0x10] = -iVar10;
      piVar5 = (int *)CONCAT31((int3)((uint)piVar5 >> 8),*pcVar18);
      *(char *)((int)puVar3 + -0x23) = *pcVar18;
    }
    pcVar18 = pcVar18 + 1;
  }
  else {
    while( true ) {
      puVar3[-0x10] = puVar13;
      cVar1 = *pcVar18;
      piVar5 = (int *)CONCAT31((int3)((uint)puVar4 >> 8),cVar1);
      if (9 < (int)cVar1 - 0x30U) break;
      puVar4 = (undefined4 *)(int)cVar1;
      puVar13 = (undefined1 *)((int)puVar4 + (int)puVar13 * 10 + -0x30);
      pcVar18 = pcVar18 + 1;
    }
  }
  pcVar19 = pcVar18;
  if (*pcVar18 != '.') goto LAB_00f998db;
  pcVar19 = pcVar18 + 1;
  piVar14 = (int *)0x0;
  if (pcVar18[1] != '*') {
    while( true ) {
      cVar1 = *pcVar19;
      piVar5 = (int *)CONCAT31((int3)((uint)piVar5 >> 8),cVar1);
      if (9 < (int)cVar1 - 0x30U) break;
      piVar5 = (int *)((int)cVar1 + (int)piVar14 * 10 + -0x30);
      pcVar19 = pcVar19 + 1;
      piVar14 = piVar5;
    }
    puVar3[-0xf] = piVar14;
    goto LAB_00f998db;
  }
  *(ushort *)pcVar12 = *(ushort *)pcVar12;
  if ((int)((int)piVar5 + -2) < 0x30) {
    puVar4 = (undefined4 *)((int)piVar5 + *(int *)(pcVar12 + 0x10) + -4);
    *(undefined1 **)pcVar12 = (undefined1 *)((int)piVar5 + 5);
  }
  else {
    puVar4 = (undefined4 *)(*(int *)(pcVar12 + 8) + -2);
    *(int *)(pcVar12 + 8) = *(int *)(pcVar12 + 8) + 7;
  }
  piVar5 = (int *)*puVar4;
  puVar3[-0xf] = piVar5;
  pcVar19 = pcVar18 + 1;
  if ((int)piVar5 < 0) {
    puVar3[-0xf] = 0xffff8300;
    pcVar19 = pcVar18 + 1;
  }
  do {
    pcVar19 = pcVar19 + 1;
LAB_00f998db:
    cVar1 = *pcVar19;
    uVar11 = (undefined3)((uint)piVar5 >> 8);
    piVar5 = (int *)CONCAT31(uVar11,cVar1);
  } while (cVar1 == ' ');
  if (((((cVar1 == 'd') || (cVar1 == 'x')) || (cVar1 == 'u')) || ((cVar1 == 'o' || (cVar1 == 'X'))))
     || (cVar1 == 'p')) {
    *(char *)((int)puVar3 + -0x1e) = cVar1;
    cVar1 = *pcVar19;
    piVar5 = (int *)CONCAT31(uVar11,cVar1);
    if (cVar1 != 'p') {
      *(char *)(puVar3 + -6) = cVar1;
    }
  }
  cVar1 = *pcVar19;
  if (cVar1 == 'l') {
    *(undefined1 *)((int)puVar3 + -0x1e) = 0x6c;
    pcVar17 = pcVar19 + 1;
    if (pcVar19[1] == 'l') {
LAB_00f99941:
      pcVar17 = pcVar19 + 2;
    }
  }
  else if (cVar1 == 'L') {
    *(undefined1 *)(puVar3 + -7) = 0x4c;
    *(undefined1 *)((int)puVar3 + -0x1e) = 0x4c;
    pcVar17 = pcVar19 + 1;
  }
  else if (cVar1 == 'j') {
LAB_00f99955:
    *(char *)((int)puVar3 + -0x1e) = cVar1;
    pcVar17 = pcVar19 + 1;
  }
  else if (cVar1 == 'h') {
    if (pcVar19[1] == 'h') {
      *(undefined1 *)((int)puVar3 + -0x19) = 0x68;
      goto LAB_00f99941;
    }
    *(undefined1 *)((int)puVar3 + -0x1a) = 0x68;
    pcVar17 = pcVar19 + 1;
  }
  else if ((cVar1 == 'z') || (pcVar17 = pcVar19, cVar1 == 't')) goto LAB_00f99955;
  cVar1 = *pcVar17;
  pcVar19 = pcVar17 + 1;
  iVar10 = CONCAT31((int3)((uint)piVar5 >> 8),cVar1);
  if (cVar1 == '\0') goto LAB_00f99cdf;
  *(char *)((int)puVar3 + -0x17) = cVar1;
  uVar15 = (int)cVar1 | 0x20;
  uVar6 = iVar10 - 1;
  unaff_ESI = (code *)((int)puVar3 + -6);
  if (uVar15 == 0x61) {
LAB_00f99b34:
    unaff_ESI = (code *)((int)&DAT_0042446e + 1);
    pcVar17[-0xffffffff00000003] = 'D';
    pcVar17[-0xffffffff00000002] = -0x65;
    pcVar17[-0xffffffff00000001] = -7;
    pcVar17[0] = '\0';
    iVar10 = FUN_00f993a9();
    goto LAB_00f99cd0;
  }
  if (uVar15 - 0x61 < 2) goto LAB_00f999d7;
  sVar2 = (short)iVar10;
  if (uVar15 == 99) {
    *(ushort *)pcVar12 = *(ushort *)pcVar12;
    if (iVar10 + -3 < 0x30) {
      puVar9 = (uint *)(iVar10 + -5 + *(int *)(pcVar12 + 0x10));
      *(int *)pcVar12 = iVar10 + 4;
    }
    else {
      puVar9 = (uint *)(*(int *)(pcVar12 + 8) + -2);
      *(int *)(pcVar12 + 8) = *(int *)(pcVar12 + 8) + 7;
    }
    uVar6 = *puVar9;
    puVar3[-3] = uVar6;
    if (*(char *)((int)puVar3 + -0x1e) != '\0') {
      uVar6 = uVar6 - 1;
      unaff_ESI = (code *)(puVar3 + -3);
      puVar3[-0xf] = 0xffff8300;
    }
LAB_00f99cab:
    *(char *)((int)puVar3 + -6) = (char)uVar6;
    *(undefined1 *)((int)puVar3 + -0x1f) = 1;
LAB_00f99cb2:
    pcVar17[-0xffffffff00000003] = -0x45;
    pcVar17[-0xffffffff00000002] = -100;
    pcVar17[-0xffffffff00000001] = -7;
    pcVar17[0] = '\0';
    iVar10 = FUN_00f993a9();
    if (iVar10 < 0) {
      if (puVar3 != (undefined4 *)0x0) {
        *puVar3 = 3;
        return iVar10;
      }
      return iVar10;
    }
    goto LAB_00f99cd0;
  }
  bVar20 = uVar15 == 99;
  if (uVar15 == 100) {
LAB_00f999e0:
    *(ushort *)pcVar12 =
         *(ushort *)pcVar12 + (ushort)bVar20 * ((sVar2 - 2U & 3) - (*(ushort *)pcVar12 & 3));
    if (*(char *)((int)puVar3 + -0x1e) == '\0') {
      bVar20 = iVar10 - 3U < 0x30;
      if ((int)(iVar10 - 3U) < 0x30) {
        bVar20 = CARRY4(iVar10 - 5U,*(uint *)(pcVar12 + 0x10));
        iVar8 = (iVar10 - 5U) + *(uint *)(pcVar12 + 0x10);
        *(int *)pcVar12 = iVar10 + 4;
      }
      else {
        iVar8 = *(int *)(pcVar12 + 8) + -2;
        *(int *)(pcVar12 + 8) = *(int *)(pcVar12 + 8) + 7;
      }
      puVar7 = (ushort *)(iVar8 + -1);
      *puVar7 = *puVar7 + (ushort)bVar20 * (((ushort)puVar7 & 3) - (*puVar7 & 3));
    }
    else {
      if (iVar10 + -3 < 0x30) {
        iVar8 = iVar10 + -5 + *(int *)(pcVar12 + 0x10);
        *(int *)pcVar12 = iVar10 + 4;
      }
      else {
        iVar8 = *(int *)(pcVar12 + 8) + -2;
        *(int *)(pcVar12 + 8) = *(int *)(pcVar12 + 8) + 7;
      }
      puVar7 = *(ushort **)(iVar8 + -1);
    }
    if (*(char *)((int)puVar3 + -0x1a) == '\0') {
      if (*(char *)((int)puVar3 + -0x19) == '\0') {
        if (*(char *)(puVar3 + -6) != '\0') {
          puVar7 = (ushort *)((int)puVar7 + -1);
        }
      }
      else {
        puVar7 = (ushort *)(int)(char)((char)puVar7 + -1);
      }
    }
    else {
      puVar7 = (ushort *)(int)(short)((short)puVar7 + -1);
    }
    unaff_ESI = (code *)((int)puVar7 + -1);
    if ((int)(puVar7 + -1) < 0) {
      unaff_ESI = (code *)-(int)unaff_ESI;
    }
LAB_00f99b2a:
    pcVar17[-0xffffffff00000003] = '/';
    pcVar17[-0xffffffff00000002] = -0x65;
    pcVar17[-0xffffffff00000001] = -7;
    pcVar17[0] = '\0';
    iVar10 = FUN_00f99689();
  }
  else {
    if (uVar15 - 100 < 3 || uVar15 == 0x67) goto LAB_00f99b34;
    bVar20 = uVar15 - 0x67 < 2;
    if (uVar15 == 0x69) goto LAB_00f999e0;
    if (uVar15 - 0x69 < 5) {
LAB_00f999d7:
      *(undefined1 *)((int)puVar3 + -0x1e) = 0;
      goto LAB_00f99cab;
    }
    if (uVar15 == 0x6e) {
      if (puVar3 != (undefined4 *)0x0) {
        *puVar3 = 1;
        return -1;
      }
      if (cRamffffffe7 == '\0') {
        if (cRamffffffe6 == '\0') {
          if ((cRamffffffe3 == '\0') && (cRamffffffe2 == '\0')) {
            *(ushort *)pcVar12 = *(ushort *)pcVar12;
            if (iVar10 + -3 < 0x30) {
              iVar8 = iVar10 + -5 + *(int *)(pcVar12 + 0x10);
              *(int *)pcVar12 = iVar10 + 4;
            }
            else {
              iVar8 = *(int *)(pcVar12 + 8) + -2;
              *(int *)(pcVar12 + 8) = *(int *)(pcVar12 + 8) + 7;
            }
            **(undefined4 **)(iVar8 + -1) = uRamfffffffc;
          }
          else {
            *(ushort *)pcVar12 = *(ushort *)pcVar12;
            bVar20 = iVar10 - 3U < 0x30;
            if ((int)(iVar10 - 3U) < 0x30) {
              iVar8 = iVar10 + 4;
              bVar20 = CARRY4(iVar10 - 5U,*(uint *)(pcVar12 + 0x10));
              iVar10 = (iVar10 - 5U) + *(uint *)(pcVar12 + 0x10);
              *(int *)pcVar12 = iVar8;
            }
            else {
              iVar8 = *(int *)(pcVar12 + 8) + 7;
              iVar10 = *(int *)(pcVar12 + 8) + -2;
              *(int *)(pcVar12 + 8) = iVar8;
            }
            uRamfffffffc = CONCAT22(uRamfffffffc._2_2_,
                                    (ushort)uRamfffffffc +
                                    (ushort)bVar20 *
                                    (((ushort)iVar8 & 3) - ((ushort)uRamfffffffc & 3)));
            *(int *)(*(int *)(iVar10 + -1) + -2) = iVar8;
            pcVar19 = pcVar17 + 1;
          }
        }
        else {
          *(ushort *)pcVar12 = *(ushort *)pcVar12;
          if (iVar10 + -3 < 0x30) {
            iVar8 = iVar10 + -5 + *(int *)(pcVar12 + 0x10);
            *(int *)pcVar12 = iVar10 + 4;
          }
          else {
            iVar8 = *(int *)(pcVar12 + 8) + -2;
            *(int *)(pcVar12 + 8) = *(int *)(pcVar12 + 8) + 7;
          }
          **(undefined2 **)(iVar8 + -1) = (ushort)uRamfffffffc;
          pcVar19 = pcVar17 + 1;
        }
      }
      else {
        *(ushort *)pcVar12 = *(ushort *)pcVar12;
        if (iVar10 + -3 < 0x30) {
          iVar8 = iVar10 + -5 + *(int *)(pcVar12 + 0x10);
          *(int *)pcVar12 = iVar10 + 4;
        }
        else {
          iVar8 = *(int *)(pcVar12 + 8) + -2;
          *(int *)(pcVar12 + 8) = *(int *)(pcVar12 + 8) + 7;
        }
        **(undefined1 **)(iVar8 + -1) = (undefined1)uRamfffffffc;
        pcVar19 = pcVar17 + 1;
      }
      goto LAB_00f99cd3;
    }
    bVar20 = true;
    if (uVar15 - 0x6e < 2) {
LAB_00f99aa9:
      *(ushort *)pcVar12 =
           *(ushort *)pcVar12 + (ushort)bVar20 * ((sVar2 - 2U & 3) - (*(ushort *)pcVar12 & 3));
      if (*(char *)((int)puVar3 + -0x1e) == '\0') {
        if (iVar10 + -3 < 0x30) {
          puVar9 = (uint *)(iVar10 + -5 + *(int *)(pcVar12 + 0x10));
          *(int *)pcVar12 = iVar10 + 4;
        }
        else {
          puVar9 = (uint *)(*(int *)(pcVar12 + 8) + -2);
          *(int *)(pcVar12 + 8) = *(int *)(pcVar12 + 8) + 7;
        }
        uVar6 = *puVar9;
      }
      else {
        if (iVar10 + -3 < 0x30) {
          iVar8 = iVar10 + -5 + *(int *)(pcVar12 + 0x10);
          *(int *)pcVar12 = iVar10 + 4;
        }
        else {
          iVar8 = *(int *)(pcVar12 + 8) + -2;
          *(int *)(pcVar12 + 8) = *(int *)(pcVar12 + 8) + 7;
        }
        uVar6 = *(uint *)(iVar8 + -1);
      }
      if (*(char *)((int)puVar3 + -0x1a) == '\0') {
        if (*(char *)((int)puVar3 + -0x19) == '\0') {
          if (*(char *)(puVar3 + -6) != '\0') {
            *(undefined1 *)((int)puVar3 + -0x1e) = 0;
          }
        }
        else {
          uVar6 = uVar6 & 0xff;
        }
      }
      else {
        uVar6 = uVar6 & 0xffff;
      }
      if (*(char *)((int)puVar3 + -0x17) == 'u') {
        unaff_ESI = (code *)(uVar6 - 2);
        goto LAB_00f99b2a;
      }
    }
    else {
      if (uVar15 != 0x70) {
        if (uVar15 == 0x73) {
          *(undefined1 *)(puVar3 + -9) = 0;
          *(char *)(puVar3 + -8) = (char)uVar6;
          *(ushort *)pcVar12 = *(ushort *)pcVar12;
          if (iVar10 + -3 < 0x30) {
            iVar8 = iVar10 + -5 + *(int *)(pcVar12 + 0x10);
            *(int *)pcVar12 = iVar10 + 4;
          }
          else {
            iVar8 = *(int *)(pcVar12 + 8) + -2;
            *(int *)(pcVar12 + 8) = *(int *)(pcVar12 + 8) + 7;
          }
          unaff_ESI = *(code **)(iVar8 + -1);
          if ((puVar3 != (undefined4 *)0x0) && (unaff_ESI == (code *)0x0)) {
            *puVar3 = 2;
            return -1;
          }
          goto LAB_00f99cb2;
        }
        bVar20 = uVar15 - 0x73 < 2;
        if ((uVar15 != 0x75) && (bVar20 = uVar15 - 0x75 < 3, uVar15 - 0x75 != 3)) goto LAB_00f999d7;
        goto LAB_00f99aa9;
      }
      *(char *)((int)puVar3 + -0x17) = cVar1 + '\a';
      *(ushort *)pcVar12 =
           *(ushort *)pcVar12 +
           (ushort)(uVar6 < 0xfffffff8) * ((sVar2 + 6U & 3) - (*(ushort *)pcVar12 & 3));
      if (iVar10 + 5 < 0x30) {
        iVar8 = iVar10 + 3 + *(int *)(pcVar12 + 0x10);
        *(int *)pcVar12 = iVar10 + 0xc;
      }
      else {
        iVar8 = *(int *)(pcVar12 + 8) + -2;
        *(int *)(pcVar12 + 8) = *(int *)(pcVar12 + 8) + 7;
      }
      uVar6 = *(uint *)(iVar8 + -1);
    }
    unaff_ESI = (code *)(uVar6 - 1);
    pcVar17[-0xffffffff00000003] = -0x5c;
    pcVar17[-0xffffffff00000002] = -0x66;
    pcVar17[-0xffffffff00000001] = -7;
    pcVar17[0] = '\0';
    iVar10 = FUN_00f99711();
  }
LAB_00f99cd0:
  puVar3[-1] = puVar3[-1] + iVar10;
  pcVar19 = pcVar17 + 1;
  goto LAB_00f99cd3;
}



//===== FUN_00f99cf8 @ 00f99cf8 size=357 =====

/* WARNING: Unable to track spacebase fully for stack */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined1 * __fastcall FUN_00f99cf8(int param_1,int param_2)

{
  byte bVar1;
  int iVar2;
  code *pcVar3;
  undefined4 unaff_EBX;
  undefined1 *puVar4;
  undefined1 *puVar5;
  undefined1 *puVar6;
  int unaff_ESI;
  undefined4 *puVar7;
  int *unaff_EDI;
  
  pcVar3 = (code *)(param_1 + 2);
  puVar5 = (undefined1 *)(param_2 + -4);
  *(undefined4 *)(param_2 + -4) = unaff_EBX;
  *(undefined4 *)(unaff_ESI + -8) = 0;
  if (unaff_EDI == (int *)0x0) {
    *(undefined4 *)(param_2 + -8) = 0xf99d2f;
    FUN_00f61e3a();
    puVar4 = (undefined1 *)0xffffffff;
    goto LAB_00f99e4f;
  }
  *(undefined4 *)(param_2 + -8) = 0xf99d3d;
  FUN_00f98a5a();
  if ((*(byte *)((int)unaff_EDI + 0x17) & 0x40) == 0) {
    *(undefined4 *)(param_2 + -8) = 0xf99d4e;
    FUN_00f61e3a();
LAB_00f99e2f:
    puVar6 = (undefined1 *)0xffffffff;
  }
  else {
    bVar1 = *(byte *)((int)unaff_EDI + 0x17);
    *(uint *)(unaff_ESI + -4) = (bVar1 & 8) >> 3;
    iVar2 = unaff_ESI;
    if ((bVar1 & 3) == 2) {
      unaff_EDI[2] = unaff_ESI + -0x110;
      *unaff_EDI = unaff_ESI + -0x110;
      *(undefined4 *)(param_2 + -9) = 0xf99d87;
      iVar2 = FUN_00f99e64();
      puVar5 = (undefined1 *)(param_2 + -6);
      *(int *)(unaff_ESI + -0x10) = iVar2 + -1;
      *(undefined4 *)(param_2 + -10) = 0xf99d98;
      FUN_00f99eb1();
      iVar2 = unaff_ESI + 1;
      pcVar3 = (code *)CONCAT22((short)((uint)pcVar3 >> 0x10),CONCAT11(DAT_00000117,(char)pcVar3));
      _DAT_00000110 = 0x100;
      DAT_00000117 = DAT_00000117 & 0xfc;
    }
    unaff_ESI = iVar2 + 1;
    if (pcVar3 != (code *)0x0) {
      puVar5 = puVar5 + -1;
    }
    puVar7 = &DAT_00239edc;
    *(undefined4 *)(puVar5 + -7) = 0xf99dcd;
    puVar6 = (undefined1 *)FUN_00f9974e();
    puVar4 = puVar6;
    if (DAT_00239ee4 == iVar2 + -0x10f) {
      *(undefined4 *)(puVar6 + -5) = 0xf99de5;
      FUN_00f98b98();
      pcVar3 = (code *)((uint)pcVar3 & 0xffff03ff);
      unaff_ESI = iVar2 + 2;
      DAT_00239ef3 = DAT_00239ef3 & 0xfc | (byte)((uint)pcVar3 >> 8);
      DAT_00239ee4 = 0;
      DAT_00239edc = 0;
      puVar7 = *(undefined4 **)(iVar2 + -0xe);
      puVar4 = puVar6 + -2;
      puVar7[4] = 0;
      *(undefined4 *)(puVar6 + -6) = 0xf99e10;
      FUN_00f99eb1();
    }
    puVar6 = puVar4;
    if ((*(byte *)((int)puVar7 + 0x17) & 3) == 3) {
      puVar6 = puVar4 + -1;
      *(undefined4 *)(puVar4 + -5) = 0xf99e22;
      FUN_00f98b98();
    }
    if ((*(int *)(unaff_ESI + -4) == 0) && ((*(byte *)((int)puVar7 + 0x17) & 8) != 0))
    goto LAB_00f99e2f;
  }
  puVar4 = puVar6 + -1;
  *(undefined4 *)(puVar6 + -5) = 0xf99e3b;
  FUN_00f98ac8();
  if (*(int *)(unaff_ESI + -8) != 0) {
    *(undefined4 *)(puVar6 + -5) = 0xf99e4c;
    puVar4 = (undefined1 *)(*pcVar3)();
  }
LAB_00f99e4f:
  return puVar4 + 5;
}



//===== FUN_00f99e5d @ 00f99e5d size=7 =====

void FUN_00f99e5d(void)

{
  FUN_00f99cf8();
  return;
}



//===== FUN_00f99e64 @ 00f99e64 size=42 =====

int FUN_00f99e64(void)

{
  int iVar1;
  int unaff_EDI;
  
  iVar1 = *(int *)(&WAVE_00a58590.field_0x81f8 +
                  (int)(CONCAT44(unaff_EDI + -0xa60502 >> 0x1f,unaff_EDI + -0xa60503) / 0x18) * 8) +
          -1;
  if (iVar1 == 0) {
    iVar1 = 0x200;
  }
  return iVar1;
}



//===== FUN_00f99eb1 @ 00f99eb1 size=42 =====

void FUN_00f99eb1(void)

{
  int unaff_ESI;
  int unaff_EDI;
  
  if (unaff_ESI == 0) {
    unaff_ESI = 0x200;
  }
  *(int *)(&WAVE_00a58590.field_0x81f8 +
          (int)(CONCAT44(unaff_EDI + -0xa60502 >> 0x1f,unaff_EDI + -0xa60503) / 0x18) * 8) =
       unaff_ESI;
  return;
}



//===== FUN_00f9a44c @ 00f9a44c size=26 =====

void FUN_00f9a44c(void)

{
  int *unaff_ESI;
  
  if (*(int *)*unaff_ESI != 0) {
    *unaff_ESI = (int)((int *)*unaff_ESI + 1);
    FUN_00f9a4b6();
    return;
  }
  return;
}



//===== FUN_00f9a468 @ 00f9a468 size=78 =====

undefined4 FUN_00f9a468(void)

{
  undefined4 uVar1;
  uint unaff_ESI;
  undefined1 *unaff_EDI;
  
  if (unaff_EDI == (undefined1 *)0x0) {
    return 0xffffffff;
  }
  if ((int)unaff_ESI >> 0x10 == 0) {
    uVar1 = 1;
    if (((int)unaff_ESI >> 8) - 0x81U < 0x7e) {
      *unaff_EDI = (char)(unaff_ESI >> 8);
      unaff_EDI = unaff_EDI + 1;
      uVar1 = 2;
    }
    else if (((int)unaff_ESI >> 8 != 0) || (0x7f < (unaff_ESI & 0xff))) goto LAB_00f9a4b1;
    *unaff_EDI = (char)unaff_ESI;
  }
  else {
LAB_00f9a4b1:
    uVar1 = 0xffffffff;
  }
  return uVar1;
}



//===== FUN_00f9a4b6 @ 00f9a4b6 size=16 =====

undefined4 FUN_00f9a4b6(void)

{
  undefined4 uVar1;
  uint unaff_ESI;
  
  if ((unaff_ESI & 0xffff) == unaff_ESI) {
    uVar1 = FUN_00f9a468();
    return uVar1;
  }
  return 0xffffffff;
}



//===== FUN_00f9a750 @ 00f9a750 size=10 =====

void FUN_00f9a750(void)

{
  FUN_00f60b40();
  return;
}



//===== FUN_00f9a958 @ 00f9a958 size=22 =====

void FUN_00f9a958(void)

{
  cRam00000001 = cRam00000001 + '\x02';
  return;
}



//===== thunk_FUN_00f9a958 @ 00f9a96e size=5 =====

void thunk_FUN_00f9a958(void)

{
  cRam00000001 = cRam00000001 + '\x02';
  return;
}



//===== FUN_00f9a98b @ 00f9a98b size=13 =====

void FUN_00f9a98b(void)

{
  cRam00000001 = cRam00000001 + '\x02';
  return;
}



//===== thunk_FUN_00f9a98b @ 00f9a998 size=5 =====

void thunk_FUN_00f9a98b(void)

{
  cRam00000001 = cRam00000001 + '\x02';
  return;
}



//===== FUN_00f9a9e8 @ 00f9a9e8 size=68 =====

/* WARNING: Unable to track spacebase fully for stack */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined1 * FUN_00f9a9e8(void)

{
  int iVar1;
  
  iVar1 = FUN_00f61e60();
  if (iVar1 == -1) {
    _DAT_fffffffb = 0xf9aa24;
    FUN_00f61e3a();
  }
  return (undefined1 *)(iVar1 + 5);
}



//===== FUN_00f9af16 @ 00f9af16 size=17 =====

int FUN_00f9af16(void)

{
  int iVar1;
  int unaff_EDI;
  
  if (*(char *)(unaff_EDI + 0x59) == '\0') {
    iVar1 = *(int *)(unaff_EDI + 100) - *(int *)(unaff_EDI + 0x60);
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}



//===== FUN_00f9af3f @ 00f9af3f size=127 =====

/* WARNING: Unable to track spacebase fully for stack */

undefined4 __fastcall FUN_00f9af3f(undefined4 param_1,int param_2)

{
  undefined1 *puVar1;
  undefined4 uVar2;
  undefined1 *puVar3;
  int unaff_ESI;
  int unaff_EDI;
  
  *(undefined4 *)(param_2 + -4) = 0xf9af56;
  puVar1 = (undefined1 *)FUN_00f9af16();
  if (puVar1 < (undefined1 *)(param_2 + 1)) {
    uVar2 = 0;
  }
  else {
    puVar3 = (undefined1 *)(param_2 + 1);
    if ((undefined1 *)
        (*(uint *)(unaff_EDI + 100) -
        ((*(int *)(unaff_EDI + 0x60) + *(int *)(unaff_EDI + 0x5c)) - 2U) %
        *(uint *)(unaff_EDI + 100)) < (undefined1 *)(param_2 + 1)) {
      *(undefined4 *)(param_2 + -5) = 0xf9af90;
      FUN_00f60c60();
      *(int *)(unaff_EDI + 0x60) = *(int *)(unaff_EDI + 0x60) + unaff_ESI;
      puVar3 = (undefined1 *)(param_2 - unaff_ESI);
    }
    *(undefined4 *)(puVar3 + -6) = 0xf9afab;
    FUN_00f60c60();
    *(int *)(unaff_EDI + 0x60) = (int)(puVar3 + *(int *)(unaff_EDI + 0x60) + -1);
    uVar2 = 1;
  }
  return uVar2;
}



//===== FUN_00f9afbe @ 00f9afbe size=43 =====

uint FUN_00f9afbe(void)

{
  uint uVar1;
  uint uVar2;
  int unaff_EDI;
  
  uVar1 = FUN_00f9af16();
  uVar2 = *(uint *)(unaff_EDI + 100) -
          ((*(int *)(unaff_EDI + 0x60) + *(int *)(unaff_EDI + 0x5c)) - 3U) %
          *(uint *)(unaff_EDI + 100);
  if (uVar1 <= uVar2) {
    uVar2 = uVar1;
  }
  return uVar2;
}



//===== FUN_00f9b052 @ 00f9b052 size=176 =====

int FUN_00f9b052(void)

{
  int in_EAX;
  int iVar1;
  int unaff_EDI;
  
  iVar1 = in_EAX + -3;
  if ((*(char *)(unaff_EDI + 0x58) == '\0') &&
     ((iVar1 = CONCAT31((int3)((uint)iVar1 >> 8),*(char *)(unaff_EDI + 0x59)),
      *(char *)(unaff_EDI + 0x59) != '\0' || (*(int *)(unaff_EDI + 0x60) != 0)))) {
    iVar1 = *(int *)(unaff_EDI + 0x5c) + -1;
    *(undefined4 *)(unaff_EDI + 0x18) = 0x41;
    *(int *)(unaff_EDI + 0x20) = iVar1 + *(int *)(unaff_EDI + 0x10);
    *(undefined4 *)(unaff_EDI + 0x28) = 0;
    *(undefined4 *)(unaff_EDI + 0x30) = 0;
    *(undefined4 *)(unaff_EDI + 0x38) = DAT_004244b8;
    if (((char)iVar1 == '\x04') || (*(int *)(unaff_EDI + 0x60) != 0)) {
      iVar1 = *(int *)(unaff_EDI + 0x60);
      if (*(uint *)(unaff_EDI + 100) - iVar1 < *(uint *)(unaff_EDI + 100)) {
        iVar1 = 0;
      }
    }
    else {
      iVar1 = 0;
      *(undefined1 *)(unaff_EDI + 0x59) = 0;
    }
    *(int *)(unaff_EDI + 0x28) = iVar1 + -1;
    FUN_00f6184c();
    iVar1 = FUN_00f608ac();
    *(undefined1 *)(unaff_EDI + 0x58) = 1;
  }
  return iVar1;
}



//===== FUN_00f9b37b @ 00f9b37b size=171 =====

/* WARNING: Removing unreachable block (ram,0x00f9b3a3) */
/* WARNING: Removing unreachable block (ram,0x00f9b3a7) */
/* WARNING: Removing unreachable block (ram,0x00f9b3ae) */
/* WARNING: Removing unreachable block (ram,0x00f9b3fe) */
/* WARNING: Removing unreachable block (ram,0x00f9b3f9) */
/* WARNING: Removing unreachable block (ram,0x00f9b404) */

int FUN_00f9b37b(void)

{
  int in_EAX;
  int iVar1;
  int unaff_EDI;
  
  iVar1 = in_EAX + -1;
  if ((*(char *)(unaff_EDI + 0x58) == '\0') && (*(char *)(unaff_EDI + 0x59) == '\0')) {
    iVar1 = *(int *)(unaff_EDI + 0x60);
  }
  return iVar1;
}



