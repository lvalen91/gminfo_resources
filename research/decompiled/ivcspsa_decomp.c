// === ivcspsa.dll ===
// ImageBase: 10000000

// 3 functions matched name-filter

// total with callees: 50
//===== getVersion @ 10006410 size=6 =====

undefined4 getVersion(void)

{
                    /* 0x6410  3  getVersion */
  return 1;
}



//===== GetPsaKey @ 10010f30 size=2630 =====

/* WARNING: Removing unreachable block (ram,0x10011120) */
/* WARNING: Removing unreachable block (ram,0x10011595) */

void GetPsaKey(uint *param_1,uint *param_2,uint *param_3,uint *param_4,undefined4 param_5,
              char *param_6,uint *param_7,uint *param_8)

{
  char cVar1;
  int iVar2;
  byte *pbVar3;
  uint *puVar4;
  uint *puVar5;
  char ****ppppcVar6;
  int extraout_EAX;
  byte ****ppppbVar7;
  int iVar8;
  uint uVar9;
  undefined4 extraout_ECX;
  undefined4 extraout_ECX_00;
  void *extraout_ECX_01;
  undefined4 extraout_ECX_02;
  undefined4 extraout_ECX_03;
  undefined4 uVar10;
  char ****ppppcVar11;
  char *pcVar12;
  void *in_stack_fffff7cc;
  undefined1 uVar13;
  undefined *puVar14;
  uint uStack_804;
  undefined4 local_7dc [8];
  undefined1 local_7bc [136];
  int local_734;
  int local_710;
  int local_70c;
  int local_6cc;
  byte ***local_6bc [5];
  uint local_6a8;
  undefined4 local_67c [42];
  undefined4 local_5d4 [24];
  uint local_574 [6];
  undefined4 local_55c [20];
  uint local_50c [4];
  int local_4fc;
  undefined4 local_4f8;
  uint local_4f4 [4];
  int local_4e4;
  undefined4 local_4e0;
  uint local_4dc [4];
  undefined *local_4cc;
  undefined4 local_4c8;
  void *local_4c4 [4];
  undefined *local_4b4;
  uint local_4b0;
  char ***local_4ac [4];
  undefined4 local_49c;
  uint local_498;
  uint local_494 [6];
  void *local_47c [4];
  int local_46c;
  uint local_468;
  void *local_464 [4];
  int local_454;
  uint local_450;
  char ***local_44c [4];
  int local_43c;
  uint local_438;
  void *local_434 [4];
  undefined4 local_424;
  uint local_420;
  undefined4 local_41c;
  uint local_18;
  undefined1 *local_14;
  void *local_10;
  undefined1 *puStack_c;
  undefined4 local_8;
  
                    /* 0x10f30  1  GetPsaKey */
  local_8 = 0xffffffff;
  puStack_c = &LAB_10052ac6;
  local_10 = ExceptionList;
  uStack_804 = DAT_100681bc ^ (uint)&stack0xfffffffc;
  local_14 = (undefined1 *)&uStack_804;
  ExceptionList = &local_10;
  local_18 = uStack_804;
  _memset(&local_41c,0,0x400);
  local_8 = 0;
  local_420 = 0xf;
  local_424 = 0;
  local_434[0] = (void *)((uint)local_434[0] & 0xffffff00);
  if ((char)*param_1 == '\0') {
    uVar9 = 0;
  }
  else {
    puVar4 = param_1;
    do {
      uVar9 = *puVar4;
      puVar4 = (uint *)((int)puVar4 + 1);
    } while ((char)uVar9 != '\0');
    uVar9 = (int)puVar4 - ((int)param_1 + 1);
  }
  FUN_10002340(local_434,param_1,uVar9);
  local_8._0_1_ = 1;
  _memset(local_7dc,0,0x160);
  FUN_10016570(local_7dc,param_5);
  _memset(local_67c,0,0xa8);
  FUN_1000e7c0(local_67c);
  local_8._0_1_ = 3;
  _memset(local_55c,0,0x50);
  FUN_10009180(local_55c);
  local_8._0_1_ = 4;
  puVar14 = (undefined *)0x10011085;
  iVar2 = FUN_100109a0(local_67c,param_2,param_3,param_4,param_5,param_6);
  if (iVar2 != 0) {
    FUN_100090c0(local_55c);
    FUN_1000e850(local_67c);
    FUN_100167d0(local_7dc);
    if (0xf < local_420) {
      FUN_100021c0(local_434[0],local_420 + 1);
      FUN_100119c9();
      return;
    }
    goto LAB_100119cb;
  }
  local_468 = 7;
  local_46c = 0;
  local_47c[0] = (void *)((uint)local_47c[0] & 0xffff0000);
  local_450 = 7;
  local_454 = 0;
  local_464[0] = (void *)((uint)local_464[0] & 0xffff0000);
  local_8._0_1_ = 6;
                    /* WARNING: Ignoring partial resolution of indirect */
  uVar13 = 0;
  FUN_10001da0(&stack0xfffff7e4,(uint *)local_434,0,0xffffffff);
  iVar2 = FUN_10016d10(local_7dc,puVar14);
  puVar4 = param_8;
  if (iVar2 == 0) {
    local_438 = 7;
    local_44c[0] = (char ***)((uint)local_44c[0] & 0xffff0000);
    local_8._0_1_ = 7;
    local_43c = iVar2;
    iVar2 = FUN_10001940(local_434,(int *)&DAT_1005f254,extraout_ECX,3);
    if (iVar2 == 0) {
      pbVar3 = FUN_10010ef0(local_7dc,(undefined1 *)local_4c4);
      local_8._0_1_ = 8;
      FUN_10009080(local_55c,(uint *)&stack0xfffff7e4,pbVar3);
      puVar4 = (uint *)FUN_1000f0d0(local_67c,local_494,puVar14);
      FUN_100096a0(local_44c,puVar4);
      FUN_1000add0(local_494);
      local_8 = CONCAT31(local_8._1_3_,7);
      if (0xf < local_4b0) {
        FUN_100021c0(local_4c4[0],local_4b0 + 1);
      }
      puVar4 = (uint *)0x0;
    }
    else {
      iVar2 = FUN_10001940(local_434,(int *)&DAT_1005f268,extraout_ECX_00,3);
      if (iVar2 != 0) {
        FUN_100027f0(&DAT_1006b110,3,"httpclient.cpp",0x89,"GetPsaKey","NOT SUPPORTED App");
        FUN_1000add0(local_44c);
        FUN_1000add0(local_464);
        FUN_1000add0(local_47c);
        FUN_100090c0(local_55c);
        FUN_1000e850(local_67c);
        FUN_100167d0(local_7dc);
        FUN_10001c70(local_434);
        goto LAB_100119cb;
      }
      local_4f8 = 7;
      local_50c[0]._0_2_ = 0;
      local_4e0 = 7;
      local_4f4[0]._0_2_ = 0;
      puVar4 = (uint *)0x1;
      local_4fc = iVar2;
      local_4e4 = iVar2;
      _memset(local_5d4,0,0x5c);
      FUN_100088f0(local_5d4);
      local_8._0_1_ = 0xb;
      puVar14 = (undefined *)FUN_100089f0(extraout_ECX_01);
      if (puVar14 != (undefined *)0x0) {
        FUN_100027f0(&DAT_1006b110,3,"httpclient.cpp",0x7f,"GetPsaKey","Failed on callback\n");
        FUN_10008940((int)local_5d4);
        FUN_1000add0(local_4f4);
        FUN_1000add0(local_50c);
        FUN_1000add0(local_44c);
        FUN_1000add0(local_464);
        FUN_1000add0(local_47c);
        FUN_100090c0(local_55c);
        FUN_1000e850(local_67c);
        FUN_100167d0(local_7dc);
        FUN_10001c70(local_434);
        goto LAB_100119cb;
      }
      FUN_10008c70(local_5d4,(uint *)local_464);
      FUN_10008ae0(local_5d4,(uint *)local_47c);
      local_4b0 = 0xf;
      local_4c4[0] = (void *)((uint)local_4c4[0] & 0xffffff00);
      local_4c8 = 0xf;
      local_4dc[0] = local_4dc[0] & 0xffffff00;
      local_8._0_1_ = 0xd;
      local_4cc = puVar14;
      local_4b4 = puVar14;
      puVar5 = FUN_10011bd0(local_55c,local_494,(char *)local_47c);
      FUN_1000bf40(local_4c4,puVar5);
      FUN_10001c70(local_494);
      puVar5 = FUN_10011bd0(local_55c,local_494,(char *)local_464);
      FUN_1000bf40(local_4dc,puVar5);
      FUN_10001c70(local_494);
      if (local_46c == 0) {
        FUN_100027f0(&DAT_1006b110,3,"httpclient.cpp",0x67,"GetPsaKey","Failed to get token!!\n");
        FUN_10001c70(local_4dc);
        FUN_10001c70(local_4c4);
        FUN_10008940((int)local_5d4);
        FUN_1000add0(local_4f4);
        FUN_1000add0(local_50c);
        FUN_1000add0(local_44c);
        FUN_1000add0(local_464);
        FUN_1000add0(local_47c);
        FUN_100090c0(local_55c);
        FUN_1000e850(local_67c);
        FUN_100167d0(local_7dc);
        FUN_10001c70(local_434);
        goto LAB_100119cb;
      }
      FUN_100027f0(&DAT_1006b110,0,"httpclient.cpp",99,"GetPsaKey","Got Token");
      if (local_454 == 0) {
        puVar14 = &DAT_1006b110;
        FUN_100027f0(&DAT_1006b110,3,"httpclient.cpp",0x71,"GetPsaKey","Failed to get DevID\n");
        uVar10 = extraout_ECX_03;
      }
      else {
        FUN_100027f0(&DAT_1006b110,0,"httpclient.cpp",0x6d,"GetPsaKey","Got devID: %s");
        uVar10 = extraout_ECX_02;
      }
      iVar2 = FUN_10001940(local_7bc,(int *)&DAT_1005f268,uVar10,3);
      if ((iVar2 == 0) && (local_734 != 0)) {
        FUN_10008da0(local_5d4,local_50c,local_4f4);
        FUN_10011bd0(local_55c,local_494,(char *)local_50c);
        local_8._0_1_ = 0xe;
        FUN_10011bd0(local_55c,local_574,(char *)local_4f4);
        local_8._0_1_ = 0xf;
        FUN_10006e50(&stack0xfffff7e4,local_574);
        local_8._0_1_ = 0x10;
        FUN_10006e50(&stack0xfffff7cc,local_494);
        local_8._0_1_ = 0xf;
        FUN_10016c70(in_stack_fffff7cc);
        FUN_10001c70(local_574);
        FUN_10001c70(local_494);
      }
      FUN_10001c70(local_4dc);
      local_8._0_1_ = 0xb;
      FUN_10001c70(local_4c4);
      FUN_10009da0(&stack0xfffff7e4,(uint *)local_464);
      local_8._0_1_ = 0x11;
      FUN_10009da0(&stack0xfffff7cc,(uint *)local_47c);
      local_8._0_1_ = 0xb;
      puVar5 = (uint *)FUN_1000f7a0(local_67c,local_494,in_stack_fffff7cc);
      FUN_100096a0(local_44c,puVar5);
      FUN_1000add0(local_494);
      FUN_10008940((int)local_5d4);
      FUN_1000add0(local_4f4);
      local_8 = CONCAT31(local_8._1_3_,7);
      FUN_1000add0(local_50c);
    }
    ppppcVar6 = local_44c;
    if (7 < local_438) {
      ppppcVar6 = (char ****)local_44c[0];
    }
    ppppcVar11 = local_44c;
    if (7 < local_438) {
      ppppcVar11 = (char ****)local_44c[0];
    }
    FUN_10011fe0(local_4ac,(char *)ppppcVar11,(char *)((int)ppppcVar6 + local_43c * 2));
    local_8 = CONCAT31(local_8._1_3_,0x12);
    ppppcVar6 = local_4ac;
    if (0xf < local_498) {
      ppppcVar6 = (char ****)local_4ac[0];
    }
    GetTickCount64();
    local_70c = extraout_EAX + local_710;
                    /* WARNING: Ignoring partial resolution of indirect */
    uVar13 = 0;
    FUN_10001da0(&stack0xfffff7e4,(uint *)local_434,0,0xffffffff);
    FUN_100173b0(local_7dc,(char *)ppppcVar6,puVar14);
    if (0xf < local_498) {
      FUN_100021c0(local_4ac[0],local_498 + 1);
    }
    local_8._0_1_ = 6;
    local_498 = 0xf;
    local_49c = 0;
    local_4ac[0] = (char ***)((uint)local_4ac[0] & 0xffffff00);
    iVar2 = local_6cc;
    if (7 < local_438) {
      FUN_1000acd0(local_44c[0],local_438 + 1);
    }
  }
  iVar8 = 0;
  if ((iVar2 == 200) || (iVar2 == 500)) {
    ppppbVar7 = local_6bc;
    if (0xf < local_6a8) {
      ppppbVar7 = (byte ****)local_6bc[0];
    }
    if (puVar4 == (uint *)0x0) {
      iVar8 = FUN_1000cdc0((byte *)ppppbVar7,(int)&local_41c);
      if (iVar8 == 0x1014) {
        iVar8 = 0x3ec;
      }
      else if (iVar8 - 4000U < 1000) {
        iVar8 = 4000;
      }
    }
    else if (puVar4 == (uint *)0x1) {
      iVar8 = FUN_1000d330((byte *)ppppbVar7,(int)&local_41c);
    }
    pcVar12 = (char *)&local_41c;
    do {
      cVar1 = *pcVar12;
      pcVar12 = pcVar12 + 1;
    } while (cVar1 != '\0');
    uVar9 = (int)pcVar12 - ((int)&local_41c + 1);
    if (iVar8 != 0) {
      param_7 = param_8;
    }
    FUN_10034570(param_7,&local_41c,uVar9);
    *(undefined1 *)(uVar9 + (int)param_7) = 0;
  }
  else {
    FUN_100027f0(&DAT_1006b110,3,"httpclient.cpp",0xbf,"GetPsaKey","Http request error %d");
  }
  if (7 < local_450) {
    FUN_1000acd0(local_464[0],local_450 + 1);
  }
  local_450 = 7;
  local_464[0] = (void *)((uint)local_464[0] & 0xffff0000);
  local_454 = 0;
  if (7 < local_468) {
    FUN_1000acd0(local_47c[0],local_468 + 1);
  }
  local_468 = 7;
  local_46c = 0;
  local_47c[0] = (void *)((uint)local_47c[0] & 0xffff0000);
  FUN_100090c0(local_55c);
  FUN_1000e850(local_67c);
  FUN_100167d0(local_7dc);
  if (0xf < local_420) {
    FUN_100021c0(local_434[0],local_420 + 1);
    FUN_100119c9();
    return;
  }
LAB_100119cb:
  ExceptionList = local_10;
  __security_check_cookie(local_18 ^ (uint)&stack0xfffffffc);
  return;
}



//===== GetPsaVersion @ 100119f0 size=369 =====

void __cdecl GetPsaVersion(uint *param_1)

{
  DWORD DVar1;
  BOOL BVar2;
  uint ****ppppuVar3;
  uint *local_14c;
  HMODULE local_148;
  uint ***local_144 [4];
  int local_134;
  uint local_130;
  DWORD local_12c;
  undefined8 local_128;
  undefined4 local_120;
  uint local_11c;
  CHAR local_118 [268];
  uint local_c;
  
                    /* 0x119f0  2  GetPsaVersion */
  local_c = DAT_100681bc ^ (uint)&stack0xfffffffc;
  _memset(local_118,0,0x105);
  local_148 = (HMODULE)0x0;
  GetModuleHandleExA(6,(LPCSTR)GetPsaVersion,&local_148);
  DVar1 = GetModuleFileNameA(local_148,local_118,0x104);
  if ((DVar1 != 0) && (DVar1 = GetFileVersionInfoSizeA(local_118,&local_12c), DVar1 != 0)) {
    local_120 = 0;
    local_128 = 0;
    FUN_10011b70(&local_128,DVar1);
    BVar2 = GetFileVersionInfoA(local_118,0,DVar1,(LPVOID)local_128);
    if (BVar2 != 0) {
      local_14c = (uint *)0x0;
      local_11c = 0;
      BVar2 = VerQueryValueA((LPVOID)local_128,"\\StringFileInfo\\040904B0\\ProductVersion",
                             &local_14c,&local_11c);
      if (BVar2 != 0) {
        FUN_10002440(local_144,local_14c);
        ppppuVar3 = local_144;
        if (0xf < local_130) {
          ppppuVar3 = (uint ****)local_144[0];
        }
        FUN_10034570(param_1,(uint *)ppppuVar3,local_134 + 1);
        FUN_10001c70(local_144);
      }
    }
    FUN_10011c10((uint *)&local_128);
    __security_check_cookie(local_c ^ (uint)&stack0xfffffffc);
    return;
  }
  __security_check_cookie(local_c ^ (uint)&stack0xfffffffc);
  return;
}



//===== FUN_10016570 @ 10016570 size=603 =====

int __thiscall FUN_10016570(void *this,undefined4 param_1)

{
  undefined4 *puVar1;
  undefined4 *puVar2;
  void *local_10;
  undefined1 *puStack_c;
  undefined1 local_8;
  undefined3 uStack_7;
  
  puStack_c = &LAB_10052eeb;
  local_10 = ExceptionList;
  ExceptionList = &local_10;
  puVar1 = (undefined4 *)((int)this + 8);
  *(undefined4 *)((int)this + 0x1c) = 0xf;
  *(undefined4 *)((int)this + 0x18) = 0;
  if (0xf < *(uint *)((int)this + 0x1c)) {
    puVar1 = (undefined4 *)*puVar1;
  }
  *(undefined1 *)puVar1 = 0;
  puVar1 = (undefined4 *)((int)this + 0x20);
  *(undefined4 *)((int)this + 0x34) = 0xf;
  *(undefined4 *)((int)this + 0x30) = 0;
  if (0xf < *(uint *)((int)this + 0x34)) {
    puVar1 = (undefined4 *)*puVar1;
  }
  *(undefined1 *)puVar1 = 0;
  puVar1 = (undefined4 *)((int)this + 0x38);
  *(undefined4 *)((int)this + 0x4c) = 0xf;
  *(undefined4 *)((int)this + 0x48) = 0;
  if (0xf < *(uint *)((int)this + 0x4c)) {
    puVar1 = (undefined4 *)*puVar1;
  }
  *(undefined1 *)puVar1 = 0;
  puVar1 = (undefined4 *)((int)this + 0x50);
  *(undefined4 *)((int)this + 100) = 0xf;
  *(undefined4 *)((int)this + 0x60) = 0;
  if (0xf < *(uint *)((int)this + 100)) {
    puVar1 = (undefined4 *)*puVar1;
  }
  *(undefined1 *)puVar1 = 0;
  puVar1 = (undefined4 *)((int)this + 0x68);
  local_8 = 3;
  uStack_7 = 0;
  *(undefined4 *)((int)this + 0x7c) = 0xf;
  *(undefined4 *)((int)this + 0x78) = 0;
  puVar2 = puVar1;
  if (0xf < *(uint *)((int)this + 0x7c)) {
    puVar2 = (undefined4 *)*puVar1;
  }
  *(undefined1 *)puVar2 = 0;
  FUN_10002340(puVar1,(uint *)&DAT_1005e8f8,0);
  puVar1 = (undefined4 *)((int)this + 0x80);
  local_8 = 4;
  *(undefined4 *)((int)this + 0x94) = 0xf;
  *(undefined4 *)((int)this + 0x90) = 0;
  puVar2 = puVar1;
  if (0xf < *(uint *)((int)this + 0x94)) {
    puVar2 = (undefined4 *)*puVar1;
  }
  *(undefined1 *)puVar2 = 0;
  FUN_10002340(puVar1,(uint *)&DAT_1005e8f8,0);
  puVar1 = (undefined4 *)((int)this + 0x98);
  *(undefined4 *)((int)this + 0xac) = 0xf;
  *(undefined4 *)((int)this + 0xa8) = 0;
  if (0xf < *(uint *)((int)this + 0xac)) {
    puVar1 = (undefined4 *)*puVar1;
  }
  *(undefined1 *)puVar1 = 0;
  puVar1 = (undefined4 *)((int)this + 0xb4);
  *(undefined4 *)((int)this + 200) = 0xf;
  *(undefined4 *)((int)this + 0xc4) = 0;
  if (0xf < *(uint *)((int)this + 200)) {
    puVar1 = (undefined4 *)*puVar1;
  }
  *(undefined1 *)puVar1 = 0;
  *(undefined4 *)((int)this + 0xcc) = param_1;
  puVar1 = (undefined4 *)((int)this + 0xd8);
  *(undefined2 *)((int)this + 0xd4) = 0x100;
  *(undefined4 *)((int)this + 0xec) = 0xf;
  *(undefined4 *)((int)this + 0xe8) = 0;
  if (0xf < *(uint *)((int)this + 0xec)) {
    puVar1 = (undefined4 *)*puVar1;
  }
  *(undefined1 *)puVar1 = 0;
  puVar1 = (undefined4 *)((int)this + 0xf0);
  *(undefined4 *)((int)this + 0x104) = 0xf;
  *(undefined4 *)((int)this + 0x100) = 0;
  puVar2 = puVar1;
  if (0xf < *(uint *)((int)this + 0x104)) {
    puVar2 = (undefined4 *)*puVar1;
  }
  *(undefined1 *)puVar2 = 0;
  puVar2 = (undefined4 *)((int)this + 0x120);
  *(undefined1 *)((int)this + 0x118) = 0;
  *(undefined4 *)((int)this + 0x134) = 0xf;
  *(undefined4 *)((int)this + 0x130) = 0;
  if (0xf < *(uint *)((int)this + 0x134)) {
    puVar2 = (undefined4 *)*puVar2;
  }
  *(undefined1 *)puVar2 = 0;
  _local_8 = CONCAT31(uStack_7,10);
  *(undefined1 *)((int)this + 0x138) = 1;
  FUN_10002340(puVar1,(uint *)&DAT_1005e8f8,0);
  *(undefined4 *)((int)this + 0x108) = 0;
  *(undefined4 *)((int)this + 0x10c) = 0;
  *(undefined4 *)((int)this + 0x110) = 4;
  *(undefined1 *)((int)this + 0x118) = 0;
  *(undefined4 *)((int)this + 0x11c) = 0;
  *(undefined4 *)((int)this + 0x144) = 0;
  *(undefined4 *)((int)this + 0x140) = 0;
  *(undefined4 *)((int)this + 0x13c) = 0;
  *(undefined4 *)((int)this + 0x154) = 0;
  *(undefined4 *)((int)this + 0x150) = 0;
  *(undefined4 *)((int)this + 0x14c) = 0;
  *(undefined4 *)((int)this + 0x148) = 0;
  ExceptionList = local_10;
  return (int)this;
}



//===== FUN_10008940 @ 10008940 size=163 =====

void __fastcall FUN_10008940(int param_1)

{
  undefined4 *puVar1;
  
  puVar1 = (undefined4 *)(param_1 + 0x44);
  if (7 < *(uint *)(param_1 + 0x58)) {
    FUN_1000acd0((void *)*puVar1,*(uint *)(param_1 + 0x58) + 1);
  }
  *(undefined4 *)(param_1 + 0x58) = 7;
  *(undefined4 *)(param_1 + 0x54) = 0;
  if (7 < *(uint *)(param_1 + 0x58)) {
    puVar1 = (undefined4 *)*puVar1;
  }
  *(undefined2 *)puVar1 = 0;
  puVar1 = (undefined4 *)(param_1 + 0x2c);
  if (7 < *(uint *)(param_1 + 0x40)) {
    FUN_1000acd0((void *)*puVar1,*(uint *)(param_1 + 0x40) + 1);
  }
  *(undefined4 *)(param_1 + 0x40) = 7;
  *(undefined4 *)(param_1 + 0x3c) = 0;
  if (7 < *(uint *)(param_1 + 0x40)) {
    puVar1 = (undefined4 *)*puVar1;
  }
  *(undefined2 *)puVar1 = 0;
  if (7 < *(uint *)(param_1 + 0x24)) {
    FUN_1000acd0(*(void **)(param_1 + 0x10),*(uint *)(param_1 + 0x24) + 1);
  }
  *(undefined4 *)(param_1 + 0x24) = 7;
  *(undefined4 *)(param_1 + 0x20) = 0;
  if (7 < *(uint *)(param_1 + 0x24)) {
    **(undefined2 **)(param_1 + 0x10) = 0;
    return;
  }
  *(undefined2 *)(param_1 + 0x10) = 0;
  return;
}



//===== FUN_1000d330 @ 1000d330 size=1624 =====

/* WARNING: Type propagation algorithm not settling */

void FUN_1000d330(byte *param_1,int param_2)

{
  int iVar1;
  char *******_Str;
  undefined4 *******pppppppuVar2;
  uint uVar3;
  undefined4 extraout_ECX;
  undefined4 extraout_ECX_00;
  undefined4 uVar4;
  uint *puVar5;
  undefined4 extraout_ECX_01;
  uint *puVar6;
  int iVar7;
  char *local_1b0;
  undefined4 local_1ac [6];
  int local_194;
  undefined4 local_164 [6];
  undefined4 local_14c [6];
  undefined4 local_134 [6];
  undefined4 local_11c [6];
  undefined4 local_104 [6];
  undefined4 local_ec [6];
  undefined4 local_d4 [6];
  undefined4 local_bc [6];
  undefined4 local_a4 [6];
  undefined4 local_8c [6];
  undefined4 local_74 [4];
  uint local_64;
  void *local_5c [4];
  undefined4 local_4c;
  uint local_48;
  char *******local_44 [4];
  int local_34;
  uint local_30;
  undefined4 *******local_2c [4];
  uint local_1c;
  uint local_18;
  uint local_14;
  void *local_10;
  undefined1 *puStack_c;
  undefined1 local_8;
  undefined3 uStack_7;
  
  local_8 = 0xff;
  uStack_7 = 0xffffff;
  puStack_c = &LAB_100523c7;
  local_10 = ExceptionList;
  local_14 = DAT_100681bc ^ (uint)&stack0xfffffffc;
  ExceptionList = &local_10;
  if (param_1 != (byte *)0x0) {
    _memset(local_1ac,0,0x48);
    FUN_10013290(local_1ac);
    local_8 = 0;
    uStack_7 = 0;
    FUN_10014ba0(local_1ac,param_1,(undefined4 *)0x0,1);
    if (local_194 != 0) {
      puVar6 = (uint *)(*(int *)(local_194 + 0x20) + 8);
      local_48 = 0xf;
      local_4c = 0;
      local_5c[0] = (void *)((uint)local_5c[0] & 0xffffff00);
      if (*(char *)puVar6 == '\0') {
        uVar3 = 0;
      }
      else {
        puVar5 = puVar6;
        do {
          uVar3 = *puVar5;
          puVar5 = (uint *)((int)puVar5 + 1);
        } while ((char)uVar3 != '\0');
        uVar3 = (int)puVar5 - (*(int *)(local_194 + 0x20) + 9);
      }
      FUN_10002340(local_5c,puVar6,uVar3);
      local_8 = 1;
      iVar7 = *(int *)(local_194 + 0x28);
      if (iVar7 != 0) {
        puVar6 = (uint *)FUN_10002440(local_44,(uint *)(*(int *)(iVar7 + 0x20) + 8));
        FUN_1000bf40(local_5c,puVar6);
        uVar4 = extraout_ECX;
        if (0xf < local_30) {
          FUN_100021c0(local_44[0],local_30 + 1);
          uVar4 = extraout_ECX_00;
        }
        iVar1 = FUN_10001940(local_5c,(int *)":Envelope",uVar4,9);
        if ((iVar1 != -1) && (iVar7 = *(int *)(iVar7 + 0x18), iVar7 != 0)) {
LAB_1000d470:
          puVar6 = (uint *)(*(int *)(iVar7 + 0x20) + 8);
          local_18 = 0xf;
          local_1c = 0;
          local_2c[0] = (undefined4 *******)((uint)local_2c[0] & 0xffffff00);
          if (*(char *)puVar6 == '\0') {
            uVar3 = 0;
          }
          else {
            puVar5 = puVar6;
            do {
              uVar3 = *puVar5;
              puVar5 = (uint *)((int)puVar5 + 1);
            } while ((char)uVar3 != '\0');
            uVar3 = (int)puVar5 - (*(int *)(iVar7 + 0x20) + 9);
          }
          FUN_10002340(local_2c,puVar6,uVar3);
          iVar1 = FUN_10001940(local_2c,(int *)":Body",extraout_ECX_01,5);
          if (iVar1 == -1) {
            iVar7 = *(int *)(iVar7 + 0x28);
            if (iVar7 != 0) {
              if (0xf < local_18) {
                FUN_100021c0(local_2c[0],local_18 + 1);
              }
              goto LAB_1000d470;
            }
            FUN_10001c70(local_2c);
          }
          else {
            FUN_10001c70(local_2c);
            iVar7 = *(int *)(iVar7 + 0x18);
            if (iVar7 == 0) goto LAB_1000d93a;
            FUN_10002440(local_bc,(uint *)(*(int *)(iVar7 + 0x20) + 8));
            local_8 = 2;
            iVar1 = FUN_1000bf00(local_bc,(int *)"getKey4bRSP");
            if (iVar1 == -1) {
              iVar1 = FUN_1000bf00(local_bc,(int *)"Fault");
              if ((iVar1 == -1) || (iVar7 = *(int *)(iVar7 + 0x18), iVar7 == 0)) goto LAB_1000d92f;
              FUN_10002440(local_164,(uint *)(*(int *)(iVar7 + 0x20) + 8));
              local_8 = 8;
              if (*(int *)(iVar7 + 0x18) == 0) {
                FUN_10001c70(local_164);
                goto LAB_1000d92f;
              }
              FUN_10002440(local_14c,(uint *)(*(int *)(*(int *)(iVar7 + 0x18) + 0x20) + 8));
              local_8 = 9;
              iVar7 = *(int *)(iVar7 + 0x28);
              if (iVar7 == 0) goto LAB_1000d912;
              FUN_10002440(local_134,(uint *)(*(int *)(iVar7 + 0x20) + 8));
              local_8 = 10;
              if (*(int *)(iVar7 + 0x18) == 0) goto LAB_1000d907;
              FUN_10002440(local_74,(uint *)(*(int *)(*(int *)(iVar7 + 0x18) + 0x20) + 8));
              local_8 = 0xb;
              iVar7 = *(int *)(iVar7 + 0x28);
              if (iVar7 != 0) {
                FUN_10002440(local_11c,(uint *)(*(int *)(iVar7 + 0x20) + 8));
                local_8 = 0xc;
                iVar7 = *(int *)(iVar7 + 0x18);
                if (iVar7 != 0) {
                  FUN_10002440(local_104,(uint *)(*(int *)(iVar7 + 0x20) + 8));
                  local_8 = 0xd;
                  iVar7 = *(int *)(iVar7 + 0x18);
                  if (iVar7 != 0) {
                    FUN_10002440(local_ec,(uint *)(*(int *)(iVar7 + 0x20) + 8));
                    local_8 = 0xe;
                    if (*(int *)(iVar7 + 0x18) != 0) {
                      FUN_10002440(local_d4,(uint *)(*(int *)(*(int *)(iVar7 + 0x18) + 0x20) + 8));
                      local_8 = 0xf;
                      iVar7 = *(int *)(iVar7 + 0x28);
                      if (iVar7 != 0) {
                        FUN_10002440(local_8c,(uint *)(*(int *)(iVar7 + 0x20) + 8));
                        local_8 = 0x10;
                        if (*(int *)(iVar7 + 0x18) != 0) {
                          FUN_10002440(local_44,(uint *)(*(int *)(*(int *)(iVar7 + 0x18) + 0x20) + 8
                                                        ));
                          local_8 = 0x11;
                          if (local_34 != 0) {
                            _Str = (char *******)local_44;
                            if (0xf < local_30) {
                              _Str = local_44[0];
                            }
                            _strtol((char *)_Str,&local_1b0,10);
                          }
                          iVar7 = *(int *)(iVar7 + 0x28);
                          if (iVar7 != 0) {
                            FUN_10002440(local_a4,(uint *)(*(int *)(iVar7 + 0x20) + 8));
                            local_8 = 0x12;
                            if (*(int *)(iVar7 + 0x18) != 0) {
                              FUN_10002440(local_2c,(uint *)(*(int *)(*(int *)(iVar7 + 0x18) + 0x20)
                                                            + 8));
                              local_8 = 0x13;
                              uVar3 = 0;
                              if (local_64 != 0) {
                                do {
                                  if (local_1c <= uVar3) {
LAB_1000d633:
                    /* WARNING: Subroutine does not return */
                                    FUN_10019412("invalid string position");
                                  }
                                  pppppppuVar2 = local_2c;
                                  if (0xf < local_18) {
                                    pppppppuVar2 = local_2c[0];
                                  }
                                  *(undefined1 *)(param_2 + uVar3) =
                                       *(undefined1 *)((int)pppppppuVar2 + uVar3);
                                  uVar3 = uVar3 + 1;
                                } while (uVar3 < local_64);
                              }
                              *(undefined1 *)(local_1c + param_2) = 0;
                              FUN_10001c70(local_2c);
                            }
                            FUN_10001c70(local_a4);
                          }
                          FUN_10001c70(local_44);
                        }
                        FUN_10001c70(local_8c);
                      }
                      FUN_10001c70(local_d4);
                    }
                    FUN_10001c70(local_ec);
                  }
                  FUN_10001c70(local_104);
                }
                FUN_10001c70(local_11c);
              }
              FUN_10001c70(local_74);
LAB_1000d907:
              FUN_10001c70(local_134);
LAB_1000d912:
              FUN_10001c70(local_14c);
              FUN_10001c70(local_164);
            }
            else {
              iVar7 = *(int *)(iVar7 + 0x18);
              if (iVar7 == 0) goto LAB_1000d92f;
              FUN_10002440(local_a4,(uint *)(*(int *)(iVar7 + 0x20) + 8));
              local_8 = 3;
              iVar7 = *(int *)(iVar7 + 0x18);
              if (iVar7 == 0) {
                FUN_10001c70(local_a4);
                goto LAB_1000d92f;
              }
              FUN_10002440(local_8c,(uint *)(*(int *)(iVar7 + 0x20) + 8));
              local_8 = 4;
              if (*(int *)(iVar7 + 0x18) == 0) goto LAB_1000d59c;
              FUN_10002440(local_44,(uint *)(*(int *)(*(int *)(iVar7 + 0x18) + 0x20) + 8));
              local_8 = 5;
              FUN_10006e50(local_74,(uint *)local_44);
              local_8 = 6;
              FUN_10001710(local_2c,local_74);
              local_8 = 7;
              uVar3 = 0;
              if (local_1c == 0) goto LAB_1000d610;
              if (local_1c == 0) goto LAB_1000d633;
              do {
                pppppppuVar2 = local_2c;
                if (0xf < local_18) {
                  pppppppuVar2 = local_2c[0];
                }
                *(undefined1 *)(param_2 + uVar3) = *(undefined1 *)((int)pppppppuVar2 + uVar3);
                uVar3 = uVar3 + 1;
              } while (uVar3 < local_1c);
LAB_1000d610:
              *(undefined1 *)(local_1c + param_2) = 0;
              FUN_10001c70(local_2c);
              FUN_10001c70(local_74);
              FUN_10001c70(local_44);
LAB_1000d59c:
              FUN_10001c70(local_8c);
              FUN_10001c70(local_a4);
            }
LAB_1000d92f:
            FUN_10001c70(local_bc);
          }
        }
      }
LAB_1000d93a:
      if (0xf < local_48) {
        FUN_100021c0(local_5c[0],local_48 + 1);
      }
      local_48 = 0xf;
      local_4c = 0;
      local_5c[0] = (void *)((uint)local_5c[0] & 0xffffff00);
    }
    FUN_1000c9b0(local_1ac);
  }
  ExceptionList = local_10;
  __security_check_cookie(local_14 ^ (uint)&stack0xfffffffc);
  return;
}



//===== FUN_1000e7c0 @ 1000e7c0 size=139 =====

undefined4 * __fastcall FUN_1000e7c0(undefined4 *param_1)

{
  *param_1 = CWSDLEncoder::vftable;
  param_1[6] = 7;
  param_1[5] = 0;
  *(undefined2 *)(param_1 + 1) = 0;
  param_1[0xb] = 0;
  param_1[0xc] = 7;
  *(undefined2 *)(param_1 + 7) = 0;
  param_1[0x11] = 0;
  param_1[0x12] = 7;
  *(undefined2 *)(param_1 + 0xd) = 0;
  param_1[0x17] = 0;
  param_1[0x18] = 7;
  *(undefined2 *)(param_1 + 0x13) = 0;
  param_1[0x1d] = 0;
  param_1[0x1e] = 7;
  *(undefined2 *)(param_1 + 0x19) = 0;
  param_1[0x21] = 0;
  param_1[0x22] = 0;
  param_1[0x23] = 0;
  param_1[0x24] = 0;
  param_1[0x25] = 0;
  param_1[0x26] = 0;
  param_1[0x27] = 0;
  param_1[0x28] = 0;
  param_1[0x29] = 0;
  return param_1;
}



//===== FUN_1000cdc0 @ 1000cdc0 size=1377 =====

/* WARNING: Type propagation algorithm not settling */

void FUN_1000cdc0(byte *param_1,int param_2)

{
  int iVar1;
  char *******_Str;
  undefined4 *******pppppppuVar2;
  uint uVar3;
  undefined4 extraout_ECX;
  undefined4 extraout_ECX_00;
  undefined4 uVar4;
  uint *puVar5;
  undefined4 extraout_ECX_01;
  uint *puVar6;
  int iVar7;
  char *local_150;
  undefined4 local_14c [6];
  int local_134;
  undefined4 local_104 [6];
  undefined4 local_ec [6];
  undefined4 local_d4 [6];
  undefined4 local_bc [6];
  undefined4 local_a4 [6];
  undefined4 local_8c [6];
  uint local_74 [6];
  void *local_5c [4];
  undefined4 local_4c;
  uint local_48;
  char *******local_44 [4];
  int local_34;
  uint local_30;
  undefined4 *******local_2c [4];
  uint local_1c;
  uint local_18;
  uint local_14;
  void *local_10;
  undefined1 *puStack_c;
  undefined1 local_8;
  undefined3 uStack_7;
  
  local_8 = 0xff;
  uStack_7 = 0xffffff;
  puStack_c = &LAB_100522d0;
  local_10 = ExceptionList;
  local_14 = DAT_100681bc ^ (uint)&stack0xfffffffc;
  ExceptionList = &local_10;
  if (param_1 == (byte *)0x0) goto LAB_1000d307;
  _memset(local_14c,0,0x48);
  FUN_10013290(local_14c);
  local_8 = 0;
  uStack_7 = 0;
  FUN_10014ba0(local_14c,param_1,(undefined4 *)0x0,1);
  if (local_134 != 0) {
    puVar6 = (uint *)(*(int *)(local_134 + 0x20) + 8);
    local_48 = 0xf;
    local_4c = 0;
    local_5c[0] = (void *)((uint)local_5c[0] & 0xffffff00);
    if (*(char *)puVar6 == '\0') {
      uVar3 = 0;
    }
    else {
      puVar5 = puVar6;
      do {
        uVar3 = *puVar5;
        puVar5 = (uint *)((int)puVar5 + 1);
      } while ((char)uVar3 != '\0');
      uVar3 = (int)puVar5 - (*(int *)(local_134 + 0x20) + 9);
    }
    FUN_10002340(local_5c,puVar6,uVar3);
    local_8 = 1;
    iVar7 = *(int *)(local_134 + 0x28);
    if (iVar7 != 0) {
      puVar6 = (uint *)FUN_10002440(local_44,(uint *)(*(int *)(iVar7 + 0x20) + 8));
      FUN_1000bf40(local_5c,puVar6);
      uVar4 = extraout_ECX;
      if (0xf < local_30) {
        FUN_100021c0(local_44[0],local_30 + 1);
        uVar4 = extraout_ECX_00;
      }
      iVar1 = FUN_10001940(local_5c,(int *)":Envelope",uVar4,9);
      if ((iVar1 != -1) && (iVar7 = *(int *)(iVar7 + 0x18), iVar7 != 0)) {
        while( true ) {
          puVar6 = (uint *)(*(int *)(iVar7 + 0x20) + 8);
          local_18 = 0xf;
          local_1c = 0;
          local_2c[0] = (undefined4 *******)((uint)local_2c[0] & 0xffffff00);
          if (*(char *)puVar6 == '\0') {
            uVar3 = 0;
          }
          else {
            puVar5 = puVar6;
            do {
              uVar3 = *puVar5;
              puVar5 = (uint *)((int)puVar5 + 1);
            } while ((char)uVar3 != '\0');
            uVar3 = (int)puVar5 - (*(int *)(iVar7 + 0x20) + 9);
          }
          FUN_10002340(local_2c,puVar6,uVar3);
          iVar1 = FUN_10001940(local_2c,(int *)":Body",extraout_ECX_01,5);
          if (iVar1 != -1) {
            FUN_10001c70(local_2c);
            iVar7 = *(int *)(iVar7 + 0x18);
            if (iVar7 == 0) goto LAB_1000d2d3;
            FUN_10002440(local_a4,(uint *)(*(int *)(iVar7 + 0x20) + 8));
            local_8 = 2;
            iVar1 = FUN_1000bf00(local_a4,(int *)"PSA4BUnlockCodeResponse");
            if (iVar1 == -1) {
              iVar1 = FUN_1000bf00(local_a4,(int *)"Fault");
              if ((iVar1 == -1) || (iVar7 = *(int *)(iVar7 + 0x18), iVar7 == 0)) goto LAB_1000d2c8;
              FUN_10002440(local_104,(uint *)(*(int *)(iVar7 + 0x20) + 8));
              local_8 = 7;
              if (*(int *)(iVar7 + 0x18) == 0) {
                FUN_10001c70(local_104);
                goto LAB_1000d2c8;
              }
              FUN_10002440(local_ec,(uint *)(*(int *)(*(int *)(iVar7 + 0x18) + 0x20) + 8));
              local_8 = 8;
              iVar7 = *(int *)(iVar7 + 0x28);
              if (iVar7 == 0) goto LAB_1000d2ab;
              FUN_10002440(local_d4,(uint *)(*(int *)(iVar7 + 0x20) + 8));
              local_8 = 9;
              if (*(int *)(iVar7 + 0x18) == 0) goto LAB_1000d2a0;
              FUN_10002440(local_2c,(uint *)(*(int *)(*(int *)(iVar7 + 0x18) + 0x20) + 8));
              local_8 = 10;
              iVar7 = *(int *)(iVar7 + 0x28);
              if (iVar7 == 0) goto LAB_1000d298;
              FUN_10002440(local_bc,(uint *)(*(int *)(iVar7 + 0x20) + 8));
              local_8 = 0xb;
              iVar7 = *(int *)(iVar7 + 0x18);
              if (iVar7 == 0) goto LAB_1000d28d;
              FUN_10002440(local_74,(uint *)(*(int *)(iVar7 + 0x20) + 8));
              local_8 = 0xc;
              iVar7 = *(int *)(iVar7 + 0x18);
              if (iVar7 == 0) goto LAB_1000d285;
              FUN_10002440(local_8c,(uint *)(*(int *)(iVar7 + 0x20) + 8));
              local_8 = 0xd;
              if (*(int *)(iVar7 + 0x18) == 0) goto LAB_1000d27a;
              FUN_10002440(local_44,(uint *)(*(int *)(*(int *)(iVar7 + 0x18) + 0x20) + 8));
              local_8 = 0xe;
              if (local_34 != 0) {
                _Str = (char *******)local_44;
                if (0xf < local_30) {
                  _Str = local_44[0];
                }
                _strtol((char *)_Str,&local_150,10);
              }
              uVar3 = 0;
              if (local_1c == 0) goto LAB_1000d26e;
              if (local_1c != 0) goto LAB_1000d24b;
            }
            else {
              iVar7 = *(int *)(iVar7 + 0x18);
              if (iVar7 == 0) goto LAB_1000d2c8;
              FUN_10002440(local_8c,(uint *)(*(int *)(iVar7 + 0x20) + 8));
              local_8 = 3;
              if (*(int *)(iVar7 + 0x18) == 0) {
                FUN_10001c70(local_8c);
                goto LAB_1000d2c8;
              }
              FUN_10002440(local_74,(uint *)(*(int *)(*(int *)(iVar7 + 0x18) + 0x20) + 8));
              local_8 = 4;
              FUN_10006e50(local_44,local_74);
              local_8 = 5;
              FUN_10001710(local_2c,local_44);
              local_8 = 6;
              uVar3 = 0;
              if (local_1c == 0) goto LAB_1000d063;
              if (local_1c != 0) goto LAB_1000d04f;
            }
                    /* WARNING: Subroutine does not return */
            FUN_10019412("invalid string position");
          }
          iVar7 = *(int *)(iVar7 + 0x28);
          if (iVar7 == 0) break;
          if (0xf < local_18) {
            FUN_100021c0(local_2c[0],local_18 + 1);
          }
        }
        FUN_10001c70(local_2c);
      }
    }
    goto LAB_1000d2d3;
  }
  goto LAB_1000d2fa;
LAB_1000d04f:
  do {
    pppppppuVar2 = local_2c;
    if (0xf < local_18) {
      pppppppuVar2 = local_2c[0];
    }
    *(undefined1 *)(param_2 + uVar3) = *(undefined1 *)((int)pppppppuVar2 + uVar3);
    uVar3 = uVar3 + 1;
  } while (uVar3 < local_1c);
LAB_1000d063:
  *(undefined1 *)(local_1c + param_2) = 0;
  FUN_10001c70(local_2c);
  FUN_10001c70(local_44);
  FUN_10001c70(local_74);
  FUN_10001c70(local_8c);
  goto LAB_1000d2c8;
LAB_1000d24b:
  do {
    pppppppuVar2 = local_2c;
    if (0xf < local_18) {
      pppppppuVar2 = local_2c[0];
    }
    *(undefined1 *)(param_2 + uVar3) = *(undefined1 *)((int)pppppppuVar2 + uVar3);
    uVar3 = uVar3 + 1;
  } while (uVar3 < local_1c);
LAB_1000d26e:
  *(undefined1 *)(local_1c + param_2) = 0;
  FUN_10001c70(local_44);
LAB_1000d27a:
  FUN_10001c70(local_8c);
LAB_1000d285:
  FUN_10001c70(local_74);
LAB_1000d28d:
  FUN_10001c70(local_bc);
LAB_1000d298:
  FUN_10001c70(local_2c);
LAB_1000d2a0:
  FUN_10001c70(local_d4);
LAB_1000d2ab:
  FUN_10001c70(local_ec);
  FUN_10001c70(local_104);
LAB_1000d2c8:
  FUN_10001c70(local_a4);
LAB_1000d2d3:
  if (0xf < local_48) {
    FUN_100021c0(local_5c[0],local_48 + 1);
  }
  local_48 = 0xf;
  local_4c = 0;
  local_5c[0] = (void *)((uint)local_5c[0] & 0xffffff00);
LAB_1000d2fa:
  FUN_1000c9b0(local_14c);
LAB_1000d307:
  ExceptionList = local_10;
  __security_check_cookie(local_14 ^ (uint)&stack0xfffffffc);
  return;
}



//===== FUN_10011fe0 @ 10011fe0 size=109 =====

undefined4 * __thiscall FUN_10011fe0(void *this,char *param_1,char *param_2)

{
  uint uVar1;
  bool bVar2;
  uint uVar3;
  void *pvVar4;
  
  *(undefined4 *)((int)this + 0x14) = 0xf;
  *(undefined4 *)((int)this + 0x10) = 0;
  *(undefined1 *)this = 0;
  uVar1 = *(uint *)((int)this + 0x10);
  uVar3 = (int)param_2 - (int)param_1 >> 1;
  if (((uVar1 <= uVar3) && (*(uint *)((int)this + 0x14) != uVar3)) &&
     (bVar2 = FUN_10002280(this,uVar3,'\x01'), bVar2)) {
    *(uint *)((int)this + 0x10) = uVar1;
    pvVar4 = this;
    if (0xf < *(uint *)((int)this + 0x14)) {
      pvVar4 = *(void **)this;
    }
    *(undefined1 *)((int)pvVar4 + uVar1) = 0;
  }
  FUN_10012050(this,param_1,param_2);
  return this;
}



//===== FUN_100167d0 @ 100167d0 size=650 =====

void __fastcall FUN_100167d0(undefined4 *param_1)

{
  undefined4 *puVar1;
  void *local_10;
  undefined1 *puStack_c;
  undefined4 uStack_8;
  
  uStack_8 = 0xffffffff;
  puStack_c = &LAB_10052f10;
  local_10 = ExceptionList;
  ExceptionList = &local_10;
  FUN_10016ac0(param_1);
  if ((void *)param_1[0x47] != (void *)0x0) {
    FUN_10031cd2((void *)param_1[0x47]);
    param_1[0x47] = 0;
  }
  puVar1 = param_1 + 0x48;
  if (0xf < (uint)param_1[0x4d]) {
    FUN_100021c0((void *)*puVar1,param_1[0x4d] + 1);
  }
  param_1[0x4d] = 0xf;
  param_1[0x4c] = 0;
  if (0xf < (uint)param_1[0x4d]) {
    puVar1 = (undefined4 *)*puVar1;
  }
  *(undefined1 *)puVar1 = 0;
  puVar1 = param_1 + 0x3c;
  if (0xf < (uint)param_1[0x41]) {
    FUN_100021c0((void *)*puVar1,param_1[0x41] + 1);
  }
  param_1[0x41] = 0xf;
  param_1[0x40] = 0;
  if (0xf < (uint)param_1[0x41]) {
    puVar1 = (undefined4 *)*puVar1;
  }
  *(undefined1 *)puVar1 = 0;
  puVar1 = param_1 + 0x36;
  if (0xf < (uint)param_1[0x3b]) {
    FUN_100021c0((void *)*puVar1,param_1[0x3b] + 1);
  }
  param_1[0x3b] = 0xf;
  param_1[0x3a] = 0;
  if (0xf < (uint)param_1[0x3b]) {
    puVar1 = (undefined4 *)*puVar1;
  }
  *(undefined1 *)puVar1 = 0;
  puVar1 = param_1 + 0x2d;
  if (0xf < (uint)param_1[0x32]) {
    FUN_100021c0((void *)*puVar1,param_1[0x32] + 1);
  }
  param_1[0x32] = 0xf;
  param_1[0x31] = 0;
  if (0xf < (uint)param_1[0x32]) {
    puVar1 = (undefined4 *)*puVar1;
  }
  *(undefined1 *)puVar1 = 0;
  puVar1 = param_1 + 0x26;
  if (0xf < (uint)param_1[0x2b]) {
    FUN_100021c0((void *)*puVar1,param_1[0x2b] + 1);
  }
  param_1[0x2b] = 0xf;
  param_1[0x2a] = 0;
  if (0xf < (uint)param_1[0x2b]) {
    puVar1 = (undefined4 *)*puVar1;
  }
  *(undefined1 *)puVar1 = 0;
  puVar1 = param_1 + 0x20;
  if (0xf < (uint)param_1[0x25]) {
    FUN_100021c0((void *)*puVar1,param_1[0x25] + 1);
  }
  param_1[0x25] = 0xf;
  param_1[0x24] = 0;
  if (0xf < (uint)param_1[0x25]) {
    puVar1 = (undefined4 *)*puVar1;
  }
  *(undefined1 *)puVar1 = 0;
  puVar1 = param_1 + 0x1a;
  if (0xf < (uint)param_1[0x1f]) {
    FUN_100021c0((void *)*puVar1,param_1[0x1f] + 1);
  }
  param_1[0x1f] = 0xf;
  param_1[0x1e] = 0;
  if (0xf < (uint)param_1[0x1f]) {
    puVar1 = (undefined4 *)*puVar1;
  }
  *(undefined1 *)puVar1 = 0;
  puVar1 = param_1 + 0x14;
  if (0xf < (uint)param_1[0x19]) {
    FUN_100021c0((void *)*puVar1,param_1[0x19] + 1);
  }
  param_1[0x19] = 0xf;
  param_1[0x18] = 0;
  if (0xf < (uint)param_1[0x19]) {
    puVar1 = (undefined4 *)*puVar1;
  }
  *(undefined1 *)puVar1 = 0;
  puVar1 = param_1 + 0xe;
  if (0xf < (uint)param_1[0x13]) {
    FUN_100021c0((void *)*puVar1,param_1[0x13] + 1);
  }
  param_1[0x13] = 0xf;
  param_1[0x12] = 0;
  if (0xf < (uint)param_1[0x13]) {
    puVar1 = (undefined4 *)*puVar1;
  }
  *(undefined1 *)puVar1 = 0;
  puVar1 = param_1 + 8;
  if (0xf < (uint)param_1[0xd]) {
    FUN_100021c0((void *)*puVar1,param_1[0xd] + 1);
  }
  param_1[0xd] = 0xf;
  param_1[0xc] = 0;
  if (0xf < (uint)param_1[0xd]) {
    puVar1 = (undefined4 *)*puVar1;
  }
  *(undefined1 *)puVar1 = 0;
  if (0xf < (uint)param_1[7]) {
    FUN_100021c0((void *)param_1[2],param_1[7] + 1);
  }
  param_1[7] = 0xf;
  param_1[6] = 0;
  if (0xf < (uint)param_1[7]) {
    *(undefined1 *)param_1[2] = 0;
    ExceptionList = local_10;
    return;
  }
  *(undefined1 *)(param_1 + 2) = 0;
  ExceptionList = local_10;
  return;
}



//===== FUN_1000f0d0 @ 1000f0d0 size=1734 =====

void __thiscall FUN_1000f0d0(void *this,undefined4 *param_1,void *param_2)

{
  undefined1 uVar1;
  undefined2 *puVar2;
  uint *puVar3;
  undefined4 *puVar4;
  int iVar5;
  uint in_stack_0000001c;
  void *local_a10 [5];
  uint local_9fc;
  undefined4 *local_9f8;
  undefined4 local_9f4;
  void *local_9f0 [4];
  undefined4 local_9e0;
  uint local_9dc;
  void *local_9d8 [4];
  undefined4 local_9c8;
  uint local_9c4;
  void *local_9c0 [4];
  undefined4 local_9b0;
  uint local_9ac;
  undefined4 local_9a8;
  undefined4 local_998;
  uint local_994;
  undefined4 local_990;
  undefined4 local_980;
  uint local_97c;
  undefined1 local_978 [2400];
  uint local_18;
  void *local_10;
  undefined1 *puStack_c;
  undefined4 local_8;
  
  puStack_c = &LAB_100526db;
  local_10 = ExceptionList;
  local_18 = DAT_100681bc ^ (uint)&stack0xfffffffc;
  ExceptionList = &local_10;
  local_9f8 = param_1;
  local_9f4 = 0;
  local_8 = 1;
  param_1[4] = 0;
  param_1[5] = 0;
  param_1[5] = 7;
  param_1[4] = 0;
  puVar4 = param_1;
  if (7 < (uint)param_1[5]) {
    puVar4 = (undefined4 *)*param_1;
  }
  *(undefined2 *)puVar4 = 0;
  FUN_1000ab00(param_1,(uint *)
                       L"<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:psa4=\"http://iecs.tis2web.gm.com/PSA4BTypes\">\r\n<soapenv:Header/>\r\n<soapenv:Body>\r\n<psa4:PSA4BUnlockCodeRequest>\r\n"
               ,0xc3);
  local_9f4 = 1;
  puVar2 = FUN_1000e700(this,(undefined2 *)local_9f0);
  local_8._0_1_ = 2;
  puVar3 = FUN_10010ae0((uint *)local_9c0,(uint *)L"<vin>",puVar2);
  local_8._0_1_ = 3;
  puVar3 = FUN_10010c40((uint *)local_9d8,puVar3,(uint *)L"</vin>\r\n");
  local_8 = CONCAT31(local_8._1_3_,4);
  FUN_10009dd0(param_1,puVar3,0,0xffffffff);
  if (7 < local_9c4) {
    FUN_1000acd0(local_9d8[0],local_9c4 + 1);
  }
  local_9c4 = 7;
  local_9d8[0] = (void *)((uint)local_9d8[0] & 0xffff0000);
  local_9c8 = 0;
  if (7 < local_9ac) {
    FUN_1000acd0(local_9c0[0],local_9ac + 1);
  }
  local_8._0_1_ = 1;
  local_9c0[0] = (void *)((uint)local_9c0[0] & 0xffff0000);
  local_9ac = 7;
  local_9b0 = 0;
  if (7 < local_9dc) {
    FUN_1000acd0(local_9f0[0],local_9dc + 1);
  }
  puVar2 = FUN_1000e740(this,(undefined2 *)local_9f0);
  local_8._0_1_ = 5;
  puVar3 = FUN_10010ae0((uint *)local_9d8,(uint *)L"<iea>",puVar2);
  local_8._0_1_ = 6;
  puVar3 = FUN_10010c40((uint *)local_9c0,puVar3,(uint *)L"</iea>\r\n");
  local_8 = CONCAT31(local_8._1_3_,7);
  FUN_10009dd0(param_1,puVar3,0,0xffffffff);
  if (7 < local_9ac) {
    FUN_1000acd0(local_9c0[0],local_9ac + 1);
  }
  local_9ac = 7;
  local_9c0[0] = (void *)((uint)local_9c0[0] & 0xffff0000);
  local_9b0 = 0;
  if (7 < local_9c4) {
    FUN_1000acd0(local_9d8[0],local_9c4 + 1);
  }
  local_8._0_1_ = 1;
  local_9d8[0] = (void *)((uint)local_9d8[0] & 0xffff0000);
  local_9c4 = 7;
  local_9c8 = 0;
  if (7 < local_9dc) {
    FUN_1000acd0(local_9f0[0],local_9dc + 1);
  }
  puVar2 = FUN_1000e780(this,(undefined2 *)local_9f0);
  local_8._0_1_ = 8;
  puVar3 = FUN_10010ae0((uint *)local_9d8,(uint *)L"<seed>",puVar2);
  local_8._0_1_ = 9;
  puVar3 = FUN_10010c40((uint *)local_9c0,puVar3,(uint *)L"</seed>\r\n");
  local_8 = CONCAT31(local_8._1_3_,10);
  FUN_10009dd0(param_1,puVar3,0,0xffffffff);
  if (7 < local_9ac) {
    FUN_1000acd0(local_9c0[0],local_9ac + 1);
  }
  local_9ac = 7;
  local_9c0[0] = (void *)((uint)local_9c0[0] & 0xffff0000);
  local_9b0 = 0;
  if (7 < local_9c4) {
    FUN_1000acd0(local_9d8[0],local_9c4 + 1);
  }
  local_8._0_1_ = 1;
  local_9d8[0] = (void *)((uint)local_9d8[0] & 0xffff0000);
  local_9c4 = 7;
  local_9c8 = 0;
  if (7 < local_9dc) {
    FUN_1000acd0(local_9f0[0],local_9dc + 1);
  }
  FUN_10009c70(param_1,(uint *)L"<!--Optional:-->\r\n",0x12);
  puVar4 = FUN_10010b30(local_9f0,(uint *)L"<event_refid>",&param_2);
  local_8._0_1_ = 0xb;
  puVar3 = FUN_10010c40((uint *)local_9c0,puVar4,(uint *)L"</event_refid>\r\n");
  local_8 = CONCAT31(local_8._1_3_,0xc);
  FUN_10009dd0(param_1,puVar3,0,0xffffffff);
  if (7 < local_9ac) {
    FUN_1000acd0(local_9c0[0],local_9ac + 1);
  }
  local_9ac = 7;
  local_9c0[0] = (void *)((uint)local_9c0[0] & 0xffff0000);
  local_9b0 = 0;
  if (7 < local_9dc) {
    FUN_1000acd0(local_9f0[0],local_9dc + 1);
  }
  local_994 = 7;
  local_998 = 0;
  local_9a8 = (void *)((uint)local_9a8._2_2_ << 0x10);
  local_97c = 7;
  local_980 = 0;
  local_990 = (void *)((uint)local_990._2_2_ << 0x10);
  local_8._0_1_ = 0xe;
  FUN_10009c70(param_1,(uint *)L"<frames>\r\n",10);
  _eh_vector_constructor_iterator_
            (local_978,0x18,100,(_func_void_void_ptr *)&LAB_10009780,FUN_1000add0);
  iVar5 = 0;
  local_8._0_1_ = 0xf;
  uVar1 = (undefined1)local_8;
  local_8._0_1_ = 0xf;
  if (0 < *(int *)((int)this + 0x7c)) {
    do {
      FUN_1000ff50(this,iVar5,&local_9a8,&local_990);
      puVar4 = FUN_10010b30(local_a10,(uint *)L"<frame>\r\n<id>",&local_9a8);
      local_8._0_1_ = 0x10;
      puVar3 = FUN_10010c40((uint *)local_9f0,puVar4,(uint *)L"</id>\r\n<value>");
      local_8._0_1_ = 0x11;
      puVar3 = FUN_10010ca0((uint *)local_9d8,puVar3,&local_990);
      local_8._0_1_ = 0x12;
      puVar3 = FUN_10010c40((uint *)local_9c0,puVar3,(uint *)L"</value>\r\n</frame>\r\n");
      local_8 = CONCAT31(local_8._1_3_,0x13);
      FUN_10009dd0(param_1,puVar3,0,0xffffffff);
      if (7 < local_9ac) {
        FUN_1000acd0(local_9c0[0],local_9ac + 1);
      }
      local_9ac = 7;
      local_9c0[0] = (void *)((uint)local_9c0[0] & 0xffff0000);
      local_9b0 = 0;
      if (7 < local_9c4) {
        FUN_1000acd0(local_9d8[0],local_9c4 + 1);
      }
      local_9c4 = 7;
      local_9d8[0] = (void *)((uint)local_9d8[0] & 0xffff0000);
      local_9c8 = 0;
      if (7 < local_9dc) {
        FUN_1000acd0(local_9f0[0],local_9dc + 1);
      }
      local_8._0_1_ = 0xf;
      local_9f0[0] = (void *)((uint)local_9f0[0] & 0xffff0000);
      local_9dc = 7;
      local_9e0 = 0;
      if (7 < local_9fc) {
        FUN_1000acd0(local_a10[0],local_9fc + 1);
      }
      iVar5 = iVar5 + 1;
      uVar1 = (undefined1)local_8;
    } while (iVar5 < *(int *)((int)this + 0x7c));
  }
  local_8._0_1_ = uVar1;
  FUN_10009c70(param_1,(uint *)L"</frames>\r\n",0xb);
  FUN_10009c70(param_1,(uint *)L"</psa4:PSA4BUnlockCodeRequest>\r\n",0x20);
  FUN_10009c70(param_1,(uint *)L"</soapenv:Body>\r\n",0x11);
  FUN_10009c70(param_1,(uint *)L"</soapenv:Envelope>\r\n",0x15);
  local_8 = CONCAT31(local_8._1_3_,0xe);
  _eh_vector_destructor_iterator_(local_978,0x18,100,FUN_1000add0);
  if (7 < local_97c) {
    FUN_1000acd0(local_990,local_97c + 1);
  }
  local_97c = 7;
  local_990 = (void *)((uint)local_990 & 0xffff0000);
  local_980 = 0;
  if (7 < local_994) {
    FUN_1000acd0(local_9a8,local_994 + 1);
  }
  local_994 = 7;
  local_998 = 0;
  local_9a8 = (void *)((uint)local_9a8 & 0xffff0000);
  if (7 < in_stack_0000001c) {
    FUN_1000acd0(param_2,in_stack_0000001c + 1);
  }
  ExceptionList = local_10;
  __security_check_cookie(local_18 ^ (uint)&stack0xfffffffc);
  return;
}



//===== FUN_10008ae0 @ 10008ae0 size=387 =====

void __thiscall FUN_10008ae0(void *this,uint *param_1)

{
  int iVar1;
  uint *puVar2;
  uint *puVar3;
  HANDLE hHeap;
  void *local_34 [4];
  undefined4 local_24;
  uint local_20;
  uint *local_1c;
  uint local_18;
  void *local_10;
  undefined1 *puStack_c;
  undefined4 local_8;
  
  local_8 = 0xffffffff;
  puStack_c = &LAB_10051d3e;
  local_10 = ExceptionList;
  local_18 = DAT_100681bc ^ (uint)&stack0xfffffffc;
  ExceptionList = &local_10;
  local_1c = (uint *)0x0;
  iVar1 = FUN_10002650(this,(int)&local_1c);
  if (iVar1 == 0) {
    if (local_1c == (uint *)0x0) {
      FUN_100027f0(&DAT_1006ac38,3,"ClientCallbackImpl.cpp",0x4a,"ClientCallbackImpl::GetToken",
                   "Invalid data ( null pointer )");
    }
    else {
      puVar2 = (uint *)FUN_10009720(local_34,local_1c);
      if (param_1 != puVar2) {
        if (7 < param_1[5]) {
          FUN_1000acd0((void *)*param_1,param_1[5] + 1);
        }
        param_1[5] = 7;
        param_1[4] = 0;
        puVar3 = param_1;
        if (7 < param_1[5]) {
          puVar3 = (uint *)*param_1;
        }
        *(undefined2 *)puVar3 = 0;
        FUN_1000a270(param_1,puVar2);
      }
      local_8 = 0xffffffff;
      if (7 < local_20) {
        FUN_1000acd0(local_34[0],local_20 + 1);
      }
      local_20 = 7;
      local_24 = 0;
      local_34[0] = (void *)((uint)local_34[0] & 0xffff0000);
      if ((uint *)((int)this + 0x10) != param_1) {
        FUN_1000a770((uint *)((int)this + 0x10),param_1,0,0xffffffff);
      }
      FUN_100027f0(&DAT_1006ac38,0,"ClientCallbackImpl.cpp",0x52,"ClientCallbackImpl::GetToken",
                   " EXIT GotToken() callback  ");
      puVar2 = local_1c;
      if ((local_1c != (uint *)0x0) && (hHeap = GetProcessHeap(), hHeap != (HANDLE)0x0)) {
        HeapFree(hHeap,0,puVar2);
      }
    }
  }
  else {
    FUN_100027f0(&DAT_1006ac38,3,"ClientCallbackImpl.cpp",0x44,"ClientCallbackImpl::GetToken",
                 "Failed to get TK data. Error code: 0x%08x");
  }
  ExceptionList = local_10;
  __security_check_cookie(local_18 ^ (uint)&stack0xfffffffc);
  return;
}



//===== FUN_10001940 @ 10001940 size=231 =====

int __thiscall FUN_10001940(void *this,int *param_1,undefined4 param_2,uint param_3)

{
  uint uVar1;
  uint uVar2;
  int *piVar3;
  int *piVar4;
  int *piVar5;
  char *_Buf;
  char *_MaxCount;
  
  if (param_3 == 0) {
    return 0;
  }
  uVar1 = *(uint *)((int)this + 0x10);
  if ((uVar1 != 0) && (param_3 <= uVar1)) {
    _MaxCount = (char *)(uVar1 + (1 - param_3));
    _Buf = this;
    if (0xf < *(uint *)((int)this + 0x14)) {
      _Buf = *(char **)this;
    }
    while ((_MaxCount != (char *)0x0 &&
           (piVar5 = _memchr(_Buf,(int)(char)*param_1,(size_t)_MaxCount), piVar3 = param_1,
           piVar4 = piVar5, uVar1 = param_3, piVar5 != (int *)0x0))) {
      while (uVar2 = uVar1 - 4, 3 < uVar1) {
        if (*piVar4 != *piVar3) goto LAB_100019c6;
        piVar3 = piVar3 + 1;
        piVar4 = piVar4 + 1;
        uVar1 = uVar2;
      }
      if (uVar2 == 0xfffffffc) {
LAB_10001a03:
        if (0xf < *(uint *)((int)this + 0x14)) {
          this = *(void **)this;
        }
        return (int)piVar5 - (int)this;
      }
LAB_100019c6:
      if (((char)*piVar4 == (char)*piVar3) &&
         ((uVar2 == 0xfffffffd ||
          ((*(char *)((int)piVar4 + 1) == *(char *)((int)piVar3 + 1) &&
           ((uVar2 == 0xfffffffe ||
            ((*(char *)((int)piVar4 + 2) == *(char *)((int)piVar3 + 2) &&
             ((uVar2 == 0xffffffff || (*(char *)((int)piVar4 + 3) == *(char *)((int)piVar3 + 3))))))
            ))))))) goto LAB_10001a03;
      _MaxCount = _Buf + (int)(_MaxCount + (-1 - (int)piVar5));
      _Buf = (char *)((int)piVar5 + 1);
    }
  }
  return -1;
}



//===== FUN_100027f0 @ 100027f0 size=504 =====

void __cdecl
FUN_100027f0(byte *param_1,int param_2,char *param_3,undefined4 param_4,char *param_5,char *param_6)

{
  int *piVar1;
  DWORD DVar2;
  undefined4 uVar3;
  byte *pbVar4;
  undefined4 uVar5;
  undefined4 extraout_ECX;
  undefined4 extraout_ECX_00;
  undefined4 extraout_ECX_01;
  undefined4 *puVar6;
  int *piVar7;
  char *_Src;
  uint uStack_43c;
  char local_424;
  char local_420 [4];
  char local_41c [1028];
  uint local_18;
  undefined1 *local_14;
  void *local_10;
  undefined1 *puStack_c;
  undefined4 local_8;
  
  local_8 = 0xffffffff;
  puStack_c = &LAB_10051340;
  local_10 = ExceptionList;
  uStack_43c = DAT_100681bc ^ (uint)&stack0xfffffffc;
  local_14 = (undefined1 *)&uStack_43c;
  ExceptionList = &local_10;
  local_18 = uStack_43c;
  FUN_10002ad0((int)param_1);
  local_8 = 0;
  _memset(local_41c,0,0x400);
  FUN_10007480(local_41c,0x400,param_6,(__crt_locale_pointers *)0x0,&stack0x0000001c);
  puVar6 = *(undefined4 **)(param_1 + 0x38);
  uVar3 = extraout_ECX;
  do {
    if (*(undefined4 **)(param_1 + 0x3c) <= puVar6) {
      ExceptionList = local_10;
      __security_check_cookie(local_18 ^ (uint)&stack0xfffffffc);
      return;
    }
    if ((int)puVar6[2] <= param_2) {
      piVar1 = (int *)*puVar6;
      local_424 = '\0';
      if ((*param_1 & 8) != 0) {
        local_424 = FUN_10002a20(uVar3,piVar1);
      }
      if ((*param_1 & 0x10) != 0) {
        piVar7 = piVar1;
        DVar2 = GetCurrentThreadId();
        uVar3 = FUN_10003160(DVar2,local_424,piVar7);
        local_424 = (char)uVar3;
      }
      if ((*param_1 & 0x20) != 0) {
        pbVar4 = param_1 + 8;
        if (0xf < *(uint *)(param_1 + 0x1c)) {
          pbVar4 = *(byte **)pbVar4;
        }
        uVar3 = FUN_10003190((char *)pbVar4,local_424,piVar1);
        local_424 = (char)uVar3;
      }
      if ((*param_1 & 0x40) != 0) {
        switch(param_2) {
        case 0:
          _Src = "INF";
          break;
        case 1:
          _Src = "DBG";
          break;
        case 2:
          _Src = "WRN";
          break;
        case 3:
          _Src = "ERR";
          break;
        default:
          goto switchD_100028fe_default;
        }
        _strcpy_s(local_420,4,_Src);
switchD_100028fe_default:
        uVar3 = FUN_10003190(local_420,local_424,piVar1);
        local_424 = (char)uVar3;
      }
      if ((*param_1 & 4) != 0) {
        uVar3 = FUN_10003190(param_5,local_424,piVar1);
        local_424 = (char)uVar3;
      }
      if ((*param_1 & 1) != 0) {
        uVar3 = FUN_10003190(param_3,local_424,piVar1);
        local_424 = (char)uVar3;
      }
      if ((*param_1 & 2) != 0) {
        uVar3 = FUN_10003160(param_4,local_424,piVar1);
        local_424 = (char)uVar3;
      }
      uVar5 = FUN_10003190(local_41c,local_424,piVar1);
      uVar3 = extraout_ECX_00;
      if ((char)uVar5 != '\0') {
        FUN_10003480(piVar1);
        FUN_10002c60(piVar1);
        uVar3 = extraout_ECX_01;
      }
    }
    puVar6 = puVar6 + 3;
  } while( true );
}



//===== FUN_100021c0 @ 100021c0 size=85 =====

/* WARNING: Removing unreachable block (ram,0x100021fc) */

void FUN_100021c0(void *param_1,uint param_2)

{
  void *_Memory;
  
  _Memory = param_1;
  if (0xfff < param_2) {
    if (((uint)param_1 & 0x1f) != 0) {
                    /* WARNING: Subroutine does not return */
      FUN_10037231();
    }
    _Memory = *(void **)((int)param_1 + -4);
    if (param_1 <= _Memory) {
                    /* WARNING: Subroutine does not return */
      FUN_10037231();
    }
    if ((uint)((int)param_1 - (int)_Memory) < 4) {
                    /* WARNING: Subroutine does not return */
      FUN_10037231();
    }
    if (0x23 < (uint)((int)param_1 - (int)_Memory)) {
                    /* WARNING: Subroutine does not return */
      FUN_10037231();
    }
  }
  FID_conflict__free(_Memory);
  return;
}



//===== FUN_10009080 @ 10009080 size=52 =====

uint * __thiscall FUN_10009080(void *this,uint *param_1,byte *param_2)

{
  byte *pbVar1;
  
  pbVar1 = param_2;
  if (0xf < *(uint *)(param_2 + 0x14)) {
    pbVar1 = *(byte **)param_2;
  }
  FUN_10009800(this,param_1,pbVar1,pbVar1 + *(int *)(param_2 + 0x10));
  return param_1;
}



//===== FUN_1000add0 @ 1000add0 size=56 =====

void __fastcall FUN_1000add0(undefined4 *param_1)

{
  if (7 < (uint)param_1[5]) {
    FUN_1000acd0((void *)*param_1,param_1[5] + 1);
  }
  param_1[5] = 7;
  param_1[4] = 0;
  if (7 < (uint)param_1[5]) {
    *(undefined2 *)*param_1 = 0;
    return;
  }
  *(undefined2 *)param_1 = 0;
  return;
}



//===== FUN_100089f0 @ 100089f0 size=226 =====

DWORD __fastcall FUN_100089f0(void *param_1)

{
  uint uVar1;
  DWORD DVar2;
  void *local_28 [4];
  undefined4 local_18;
  uint local_14;
  void *local_10;
  undefined1 *puStack_c;
  undefined4 local_8;
  
  local_8 = 0xffffffff;
  puStack_c = &LAB_10051d08;
  local_10 = ExceptionList;
  ExceptionList = &local_10;
  local_14 = 0xf;
  uVar1 = 0x11;
  local_18 = 0;
  if (s_starterbridge_dll_1005e654[0] == '\0') {
    uVar1 = 0;
  }
  local_28[0] = (void *)((uint)local_28[0] & 0xffffff00);
  FUN_10002340(local_28,(uint *)"starterbridge.dll",uVar1);
  local_8 = 0;
  DVar2 = FUN_100024a0(param_1,(LPCSTR)local_28);
  local_8 = 0xffffffff;
  if (0xf < local_14) {
    FUN_100021c0(local_28[0],local_14 + 1);
  }
  local_14 = 0xf;
  local_18 = 0;
  local_28[0] = (void *)((uint)local_28[0] & 0xffffff00);
  if (DVar2 != 0) {
    FUN_100027f0(&DAT_1006ac38,3,"ClientCallbackImpl.cpp",0x24,"ClientCallbackImpl::Initialize",
                 "Initialization failed");
    ExceptionList = local_10;
    return DVar2;
  }
  ExceptionList = local_10;
  return 0;
}



//===== FUN_10008c70 @ 10008c70 size=299 =====

void __thiscall FUN_10008c70(void *this,uint *param_1)

{
  int iVar1;
  uint *puVar2;
  uint *puVar3;
  void *local_34 [4];
  undefined4 local_24;
  uint local_20;
  undefined4 local_1c;
  uint local_18;
  void *local_10;
  undefined1 *puStack_c;
  undefined4 local_8;
  
  local_8 = 0xffffffff;
  puStack_c = &LAB_10051d3e;
  local_10 = ExceptionList;
  local_18 = DAT_100681bc ^ (uint)&stack0xfffffffc;
  ExceptionList = &local_10;
  local_1c = 0;
  iVar1 = FUN_100026f0(this,&local_1c);
  if (iVar1 == 0) {
    *(undefined4 *)((int)this + 0x28) = local_1c;
    puVar2 = (uint *)FUN_1000aca0((undefined2 *)local_34);
    if (param_1 != puVar2) {
      if (7 < param_1[5]) {
        FUN_1000acd0((void *)*param_1,param_1[5] + 1);
      }
      param_1[5] = 7;
      param_1[4] = 0;
      puVar3 = param_1;
      if (7 < param_1[5]) {
        puVar3 = (uint *)*param_1;
      }
      *(undefined2 *)puVar3 = 0;
      FUN_1000a270(param_1,puVar2);
    }
    local_8 = 0xffffffff;
    if (7 < local_20) {
      FUN_1000acd0(local_34[0],local_20 + 1);
    }
    local_20 = 7;
    local_24 = 0;
    local_34[0] = (void *)((uint)local_34[0] & 0xffff0000);
    FUN_100027f0(&DAT_1006ac38,0,"ClientCallbackImpl.cpp",0x6a,"ClientCallbackImpl::GetDeviceId",
                 " EXIT GetDeviceId() callback ");
  }
  else {
    FUN_100027f0(&DAT_1006ac38,3,"ClientCallbackImpl.cpp",0x62,"ClientCallbackImpl::GetDeviceId",
                 "Failed to Get DevID. Error code: 0x%08x");
  }
  ExceptionList = local_10;
  __security_check_cookie(local_18 ^ (uint)&stack0xfffffffc);
  return;
}



//===== FUN_1000f7a0 @ 1000f7a0 size=1968 =====

void __thiscall FUN_1000f7a0(void *this,undefined4 *param_1,void *param_2)

{
  undefined1 uVar1;
  undefined2 *puVar2;
  uint *puVar3;
  undefined4 *puVar4;
  int iVar5;
  undefined4 uStack00000018;
  uint in_stack_0000001c;
  void *in_stack_00000020;
  uint in_stack_00000034;
  void *local_a0c [5];
  uint local_9f8;
  undefined4 local_9f4;
  void *local_9f0 [4];
  undefined4 local_9e0;
  uint local_9dc;
  void *local_9d8 [4];
  undefined4 local_9c8;
  uint local_9c4;
  void *local_9c0 [4];
  undefined4 local_9b0;
  uint local_9ac;
  undefined4 local_9a8;
  undefined4 local_998;
  uint local_994;
  undefined4 local_990;
  undefined4 local_980;
  uint local_97c;
  undefined1 local_978 [2400];
  uint local_18;
  void *local_10;
  undefined1 *puStack_c;
  undefined4 local_8;
  
  puStack_c = &LAB_10052829;
  local_10 = ExceptionList;
  local_18 = DAT_100681bc ^ (uint)&stack0xfffffffc;
  ExceptionList = &local_10;
  local_9f4 = 0;
  local_8 = 2;
  FUN_100027f0(&DAT_1006af20,0,"cwsdlencoder.cpp",0xad,"CWSDLEncoder::buildSpsSoapRequest",
               "Build SPS Soap message");
  param_1[4] = 0;
  param_1[5] = 0;
  param_1[5] = 7;
  param_1[4] = 0;
  puVar4 = param_1;
  if (7 < (uint)param_1[5]) {
    puVar4 = (undefined4 *)*param_1;
  }
  *(undefined2 *)puVar4 = 0;
  FUN_1000ab00(param_1,(uint *)
                       L"<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:typ=\"http://eoos-technologies.com/gm/service/psa/types\">\r\n<soapenv:Header/>\r\n<soapenv:Body>\r\n<typ:getKey4bRQ>\r\n<typ:args4b>\r\n"
               ,0xcf);
  local_9f4 = 1;
  puVar2 = FUN_1000e700(this,(undefined2 *)local_9d8);
  local_8._0_1_ = 3;
  puVar3 = FUN_10010ae0((uint *)local_9c0,(uint *)L"<typ:vin>",puVar2);
  local_8._0_1_ = 4;
  puVar3 = FUN_10010c40((uint *)local_9f0,puVar3,(uint *)L"</typ:vin>\r\n");
  local_8 = CONCAT31(local_8._1_3_,5);
  FUN_10009dd0(param_1,puVar3,0,0xffffffff);
  if (7 < local_9dc) {
    FUN_1000acd0(local_9f0[0],local_9dc + 1);
  }
  local_9dc = 7;
  local_9f0[0] = (void *)((uint)local_9f0[0] & 0xffff0000);
  local_9e0 = 0;
  if (7 < local_9ac) {
    FUN_1000acd0(local_9c0[0],local_9ac + 1);
  }
  local_8._0_1_ = 2;
  local_9c0[0] = (void *)((uint)local_9c0[0] & 0xffff0000);
  local_9ac = 7;
  local_9b0 = 0;
  if (7 < local_9c4) {
    FUN_1000acd0(local_9d8[0],local_9c4 + 1);
  }
  puVar4 = FUN_10010b30(local_9d8,(uint *)L"<typ:dev_id>",&stack0x00000020);
  local_8._0_1_ = 6;
  puVar3 = FUN_10010c40((uint *)local_9c0,puVar4,(uint *)L"</typ:dev_id>\r\n");
  local_8 = CONCAT31(local_8._1_3_,7);
  FUN_10009dd0(param_1,puVar3,0,0xffffffff);
  if (7 < local_9ac) {
    FUN_1000acd0(local_9c0[0],local_9ac + 1);
  }
  local_8._0_1_ = 2;
  local_9c0[0] = (void *)((uint)local_9c0[0] & 0xffff0000);
  local_9ac = 7;
  local_9b0 = 0;
  if (7 < local_9c4) {
    FUN_1000acd0(local_9d8[0],local_9c4 + 1);
  }
  puVar2 = FUN_1000e780(this,(undefined2 *)local_9d8);
  local_8._0_1_ = 8;
  puVar3 = FUN_10010ae0((uint *)local_9f0,(uint *)L"<typ:sd4b>",puVar2);
  local_8._0_1_ = 9;
  puVar3 = FUN_10010c40((uint *)local_9c0,puVar3,(uint *)L"</typ:sd4b>\r\n");
  local_8 = CONCAT31(local_8._1_3_,10);
  FUN_10009dd0(param_1,puVar3,0,0xffffffff);
  if (7 < local_9ac) {
    FUN_1000acd0(local_9c0[0],local_9ac + 1);
  }
  local_9ac = 7;
  local_9c0[0] = (void *)((uint)local_9c0[0] & 0xffff0000);
  local_9b0 = 0;
  if (7 < local_9dc) {
    FUN_1000acd0(local_9f0[0],local_9dc + 1);
  }
  local_8._0_1_ = 2;
  local_9f0[0] = (void *)((uint)local_9f0[0] & 0xffff0000);
  local_9dc = 7;
  local_9e0 = 0;
  if (7 < local_9c4) {
    FUN_1000acd0(local_9d8[0],local_9c4 + 1);
  }
  puVar2 = FUN_1000e740(this,(undefined2 *)local_9d8);
  local_8._0_1_ = 0xb;
  puVar3 = FUN_10010ae0((uint *)local_9f0,(uint *)L"<typ:iea>",puVar2);
  local_8._0_1_ = 0xc;
  puVar3 = FUN_10010c40((uint *)local_9c0,puVar3,(uint *)L"</typ:iea>\r\n");
  local_8 = CONCAT31(local_8._1_3_,0xd);
  FUN_10009dd0(param_1,puVar3,0,0xffffffff);
  if (7 < local_9ac) {
    FUN_1000acd0(local_9c0[0],local_9ac + 1);
  }
  local_9ac = 7;
  local_9c0[0] = (void *)((uint)local_9c0[0] & 0xffff0000);
  local_9b0 = 0;
  if (7 < local_9dc) {
    FUN_1000acd0(local_9f0[0],local_9dc + 1);
  }
  local_8._0_1_ = 2;
  local_9f0[0] = (void *)((uint)local_9f0[0] & 0xffff0000);
  local_9dc = 7;
  local_9e0 = 0;
  if (7 < local_9c4) {
    FUN_1000acd0(local_9d8[0],local_9c4 + 1);
  }
  FUN_10009c70(param_1,(uint *)L"<typ:frames>\r\n",0xe);
  local_994 = 7;
  local_998 = 0;
  local_9a8 = (void *)((uint)local_9a8._2_2_ << 0x10);
  local_97c = 7;
  local_980 = 0;
  local_990 = (void *)((uint)local_990._2_2_ << 0x10);
  local_8._0_1_ = 0xf;
  _eh_vector_constructor_iterator_
            (local_978,0x18,100,(_func_void_void_ptr *)&LAB_10009780,FUN_1000add0);
  iVar5 = 0;
  local_8._0_1_ = 0x10;
  uVar1 = (undefined1)local_8;
  local_8._0_1_ = 0x10;
  if (0 < *(int *)((int)this + 0x7c)) {
    do {
      FUN_1000ff50(this,iVar5,&local_9a8,&local_990);
      puVar4 = FUN_10010b30(local_a0c,(uint *)L"<typ:frame>\r\n<typ:id>",&local_9a8);
      local_8._0_1_ = 0x11;
      puVar3 = FUN_10010c40((uint *)local_9d8,puVar4,(uint *)L"</typ:id>\r\n<typ:value>");
      local_8._0_1_ = 0x12;
      puVar3 = FUN_10010ca0((uint *)local_9f0,puVar3,&local_990);
      local_8._0_1_ = 0x13;
      puVar3 = FUN_10010c40((uint *)local_9c0,puVar3,(uint *)L"</typ:value>\r\n</typ:frame>\r\n");
      local_8 = CONCAT31(local_8._1_3_,0x14);
      FUN_10009dd0(param_1,puVar3,0,0xffffffff);
      if (7 < local_9ac) {
        FUN_1000acd0(local_9c0[0],local_9ac + 1);
      }
      local_9ac = 7;
      local_9c0[0] = (void *)((uint)local_9c0[0] & 0xffff0000);
      local_9b0 = 0;
      if (7 < local_9dc) {
        FUN_1000acd0(local_9f0[0],local_9dc + 1);
      }
      local_9dc = 7;
      local_9f0[0] = (void *)((uint)local_9f0[0] & 0xffff0000);
      local_9e0 = 0;
      if (7 < local_9c4) {
        FUN_1000acd0(local_9d8[0],local_9c4 + 1);
      }
      local_8._0_1_ = 0x10;
      local_9d8[0] = (void *)((uint)local_9d8[0] & 0xffff0000);
      local_9c4 = 7;
      local_9c8 = 0;
      if (7 < local_9f8) {
        FUN_1000acd0(local_a0c[0],local_9f8 + 1);
      }
      iVar5 = iVar5 + 1;
      uVar1 = (undefined1)local_8;
    } while (iVar5 < *(int *)((int)this + 0x7c));
  }
  local_8._0_1_ = uVar1;
  FUN_10009c70(param_1,(uint *)L"</typ:frames>\r\n",0xf);
  puVar4 = FUN_10010b30(local_a0c,(uint *)L"<typ:token>",&param_2);
  local_8._0_1_ = 0x15;
  puVar3 = FUN_10010c40((uint *)local_9d8,puVar4,(uint *)L"</typ:token>\r\n");
  local_8 = CONCAT31(local_8._1_3_,0x16);
  FUN_10009dd0(param_1,puVar3,0,0xffffffff);
  if (7 < local_9c4) {
    FUN_1000acd0(local_9d8[0],local_9c4 + 1);
  }
  local_8._0_1_ = 0x10;
  local_9d8[0] = (void *)((uint)local_9d8[0] & 0xffff0000);
  local_9c4 = 7;
  local_9c8 = 0;
  if (7 < local_9f8) {
    FUN_1000acd0(local_a0c[0],local_9f8 + 1);
  }
  FUN_10009c70(param_1,(uint *)L"</typ:args4b>\r\n",0xf);
  FUN_10009c70(param_1,(uint *)L"</typ:getKey4bRQ>\r\n",0x13);
  FUN_10009c70(param_1,(uint *)L"</soapenv:Body>\r\n",0x11);
  FUN_10009c70(param_1,(uint *)L"</soapenv:Envelope>\r\n",0x15);
  local_8 = CONCAT31(local_8._1_3_,0xf);
  _eh_vector_destructor_iterator_(local_978,0x18,100,FUN_1000add0);
  if (7 < local_97c) {
    FUN_1000acd0(local_990,local_97c + 1);
  }
  local_97c = 7;
  local_990 = (void *)((uint)local_990 & 0xffff0000);
  local_980 = 0;
  if (7 < local_994) {
    FUN_1000acd0(local_9a8,local_994 + 1);
  }
  local_994 = 7;
  local_9a8 = (void *)((uint)local_9a8 & 0xffff0000);
  local_998 = 0;
  if (7 < in_stack_0000001c) {
    FUN_1000acd0(param_2,in_stack_0000001c + 1);
  }
  in_stack_0000001c = 7;
  uStack00000018 = 0;
  param_2 = (void *)((uint)param_2 & 0xffff0000);
  if (7 < in_stack_00000034) {
    FUN_1000acd0(in_stack_00000020,in_stack_00000034 + 1);
  }
  ExceptionList = local_10;
  __security_check_cookie(local_18 ^ (uint)&stack0xfffffffc);
  return;
}



//===== FUN_10034570 @ 10034570 size=1330 =====

ulonglong __cdecl FUN_10034570(uint *param_1,uint *param_2,uint param_3)

{
  undefined8 uVar1;
  uint uVar2;
  undefined4 uVar3;
  undefined4 uVar4;
  undefined4 uVar5;
  undefined4 uVar6;
  undefined4 uVar7;
  undefined4 uVar8;
  undefined4 uVar9;
  undefined4 uVar10;
  undefined4 uVar11;
  undefined4 uVar12;
  undefined4 uVar13;
  undefined4 uVar14;
  undefined4 uVar15;
  undefined4 uVar16;
  undefined4 uVar17;
  undefined4 uVar18;
  undefined4 uVar19;
  undefined4 uVar20;
  undefined4 uVar21;
  undefined4 uVar22;
  undefined4 uVar23;
  undefined4 uVar24;
  undefined4 uVar25;
  undefined4 uVar26;
  undefined4 uVar27;
  undefined4 uVar28;
  undefined4 uVar29;
  undefined4 uVar30;
  undefined4 uVar31;
  undefined4 uVar32;
  undefined4 uVar33;
  uint uVar34;
  uint uVar35;
  uint uVar36;
  uint uVar37;
  uint uVar38;
  uint uVar39;
  uint uVar40;
  uint uVar41;
  uint uVar42;
  uint uVar43;
  uint uVar44;
  uint uVar45;
  uint uVar46;
  uint uVar47;
  uint uVar48;
  uint *puVar49;
  undefined4 *puVar50;
  undefined4 *puVar51;
  undefined4 *puVar52;
  undefined4 *puVar53;
  uint *puVar54;
  uint uVar55;
  ulonglong uVar56;
  
  if ((param_2 < param_1) && (param_1 < (uint *)(param_3 + (int)param_2))) {
    puVar50 = (undefined4 *)(param_3 + (int)param_2);
    puVar52 = (undefined4 *)(param_3 + (int)param_1);
    uVar47 = param_3;
    uVar48 = param_3;
    if (0x1f < param_3) {
      if ((DAT_100681d0 >> 1 & 1) == 0) {
        if (((uint)puVar52 & 3) != 0) {
          uVar47 = (uint)puVar52 & 3;
          param_3 = param_3 - uVar47;
          do {
            *(undefined1 *)((int)puVar52 - 1) = *(undefined1 *)((int)puVar50 + -1);
            puVar50 = (undefined4 *)((int)puVar50 + -1);
            puVar52 = (undefined4 *)((int)puVar52 - 1);
            uVar47 = uVar47 - 1;
            uVar48 = 0;
          } while (uVar47 != 0);
        }
        uVar47 = param_3;
        if (0x1f < param_3) {
          uVar47 = param_3 >> 2;
          while( true ) {
            if (uVar47 == 0) break;
            uVar47 = uVar47 - 1;
            puVar52[-1] = puVar50[-1];
            puVar50 = puVar50 + -1;
            puVar52 = puVar52 + -1;
          }
          switch(param_3 & 3) {
          case 0:
            return CONCAT44(param_3,param_1) & 0x3ffffffff;
          case 1:
            *(undefined1 *)((int)puVar52 - 1) = *(undefined1 *)((int)puVar50 + -1);
            return CONCAT44(param_3,param_1) & 0x3ffffffff;
          case 2:
            *(undefined1 *)((int)puVar52 - 1) = *(undefined1 *)((int)puVar50 + -1);
            *(undefined1 *)((int)puVar52 - 2) = *(undefined1 *)((int)puVar50 + -2);
            return CONCAT44(param_3,param_1) & 0x3ffffffff;
          case 3:
            *(undefined1 *)((int)puVar52 - 1) = *(undefined1 *)((int)puVar50 + -1);
            *(undefined1 *)((int)puVar52 - 2) = *(undefined1 *)((int)puVar50 + -2);
            *(undefined1 *)((int)puVar52 - 3) = *(undefined1 *)((int)puVar50 + -3);
            return CONCAT44(param_3,param_1) & 0x3ffffffff;
          }
        }
      }
      else {
        while (puVar51 = puVar50, puVar53 = puVar52, ((uint)puVar52 & 0xf) != 0) {
          puVar50 = (undefined4 *)((int)puVar50 + -1);
          puVar52 = (undefined4 *)((int)puVar52 + -1);
          *(undefined1 *)puVar52 = *(undefined1 *)puVar50;
          uVar47 = uVar47 - 1;
        }
        do {
          puVar50 = puVar51;
          puVar52 = puVar53;
          if (uVar47 < 0x80) break;
          puVar50 = puVar51 + -0x20;
          puVar52 = puVar53 + -0x20;
          uVar3 = puVar51[-0x1f];
          uVar4 = puVar51[-0x1e];
          uVar5 = puVar51[-0x1d];
          uVar6 = puVar51[-0x1c];
          uVar7 = puVar51[-0x1b];
          uVar8 = puVar51[-0x1a];
          uVar9 = puVar51[-0x19];
          uVar10 = puVar51[-0x18];
          uVar11 = puVar51[-0x17];
          uVar12 = puVar51[-0x16];
          uVar13 = puVar51[-0x15];
          uVar14 = puVar51[-0x14];
          uVar15 = puVar51[-0x13];
          uVar16 = puVar51[-0x12];
          uVar17 = puVar51[-0x11];
          uVar18 = puVar51[-0x10];
          uVar19 = puVar51[-0xf];
          uVar20 = puVar51[-0xe];
          uVar21 = puVar51[-0xd];
          uVar22 = puVar51[-0xc];
          uVar23 = puVar51[-0xb];
          uVar24 = puVar51[-10];
          uVar25 = puVar51[-9];
          uVar26 = puVar51[-8];
          uVar27 = puVar51[-7];
          uVar28 = puVar51[-6];
          uVar29 = puVar51[-5];
          uVar30 = puVar51[-4];
          uVar31 = puVar51[-3];
          uVar32 = puVar51[-2];
          uVar33 = puVar51[-1];
          *puVar52 = *puVar50;
          puVar53[-0x1f] = uVar3;
          puVar53[-0x1e] = uVar4;
          puVar53[-0x1d] = uVar5;
          puVar53[-0x1c] = uVar6;
          puVar53[-0x1b] = uVar7;
          puVar53[-0x1a] = uVar8;
          puVar53[-0x19] = uVar9;
          puVar53[-0x18] = uVar10;
          puVar53[-0x17] = uVar11;
          puVar53[-0x16] = uVar12;
          puVar53[-0x15] = uVar13;
          puVar53[-0x14] = uVar14;
          puVar53[-0x13] = uVar15;
          puVar53[-0x12] = uVar16;
          puVar53[-0x11] = uVar17;
          puVar53[-0x10] = uVar18;
          puVar53[-0xf] = uVar19;
          puVar53[-0xe] = uVar20;
          puVar53[-0xd] = uVar21;
          puVar53[-0xc] = uVar22;
          puVar53[-0xb] = uVar23;
          puVar53[-10] = uVar24;
          puVar53[-9] = uVar25;
          puVar53[-8] = uVar26;
          puVar53[-7] = uVar27;
          puVar53[-6] = uVar28;
          puVar53[-5] = uVar29;
          puVar53[-4] = uVar30;
          puVar53[-3] = uVar31;
          puVar53[-2] = uVar32;
          puVar53[-1] = uVar33;
          uVar47 = uVar47 - 0x80;
          puVar51 = puVar50;
          puVar53 = puVar52;
        } while ((uVar47 & 0xffffff80) != 0);
        puVar51 = puVar50;
        puVar53 = puVar52;
        if (0x1f < uVar47) {
          do {
            puVar50 = puVar51 + -8;
            puVar52 = puVar53 + -8;
            uVar3 = puVar51[-7];
            uVar4 = puVar51[-6];
            uVar5 = puVar51[-5];
            uVar6 = puVar51[-4];
            uVar7 = puVar51[-3];
            uVar8 = puVar51[-2];
            uVar9 = puVar51[-1];
            *puVar52 = *puVar50;
            puVar53[-7] = uVar3;
            puVar53[-6] = uVar4;
            puVar53[-5] = uVar5;
            puVar53[-4] = uVar6;
            puVar53[-3] = uVar7;
            puVar53[-2] = uVar8;
            puVar53[-1] = uVar9;
            uVar47 = uVar47 - 0x20;
            puVar51 = puVar50;
            puVar53 = puVar52;
          } while ((uVar47 & 0xffffffe0) != 0);
        }
      }
    }
    for (; (uVar47 & 0xfffffffc) != 0; uVar47 = uVar47 - 4) {
      puVar52 = puVar52 + -1;
      puVar50 = puVar50 + -1;
      *puVar52 = *puVar50;
    }
    for (; uVar47 != 0; uVar47 = uVar47 - 1) {
      puVar52 = (undefined4 *)((int)puVar52 - 1);
      puVar50 = (undefined4 *)((int)puVar50 + -1);
      *(undefined1 *)puVar52 = *(undefined1 *)puVar50;
    }
    return CONCAT44(uVar48,param_1);
  }
  uVar47 = param_3;
  puVar54 = param_1;
  if (0x1f < param_3) {
    if (param_3 < 0x80) {
      if ((DAT_100681d0 >> 1 & 1) != 0) {
LAB_10034a3d:
        if (uVar47 == 0) goto LAB_10034aa0;
        for (uVar48 = uVar47 >> 5; param_3 = 0, uVar48 != 0; uVar48 = uVar48 - 1) {
          uVar55 = param_2[1];
          uVar2 = param_2[2];
          uVar34 = param_2[3];
          uVar35 = param_2[4];
          uVar36 = param_2[5];
          uVar37 = param_2[6];
          uVar38 = param_2[7];
          *puVar54 = *param_2;
          puVar54[1] = uVar55;
          puVar54[2] = uVar2;
          puVar54[3] = uVar34;
          puVar54[4] = uVar35;
          puVar54[5] = uVar36;
          puVar54[6] = uVar37;
          puVar54[7] = uVar38;
          param_2 = param_2 + 8;
          puVar54 = puVar54 + 8;
        }
        goto LAB_10034a6b;
      }
joined_r0x1003479d:
      for (; ((uint)puVar54 & 3) != 0; puVar54 = (uint *)((int)puVar54 + 1)) {
        *(char *)puVar54 = (char)*param_2;
        param_3 = param_3 - 1;
        param_2 = (uint *)((int)param_2 + 1);
      }
    }
    else {
      if ((DAT_1006a3dc >> 1 & 1) != 0) {
        for (; uVar47 != 0; uVar47 = uVar47 - 1) {
          *(char *)puVar54 = (char)*param_2;
          param_2 = (uint *)((int)param_2 + 1);
          puVar54 = (uint *)((int)puVar54 + 1);
        }
        return CONCAT44(param_3,param_1);
      }
      if (((((uint)param_1 ^ (uint)param_2) & 0xf) == 0) && ((DAT_100681d0 >> 1 & 1) != 0)) {
        if (((uint)param_2 & 0xf) != 0) {
          uVar48 = 0x10 - ((uint)param_2 & 0xf);
          param_3 = param_3 - uVar48;
          for (uVar47 = uVar48 & 3; uVar47 != 0; uVar47 = uVar47 - 1) {
            *(char *)puVar54 = (char)*param_2;
            param_2 = (uint *)((int)param_2 + 1);
            puVar54 = (uint *)((int)puVar54 + 1);
          }
          for (uVar48 = uVar48 >> 2; uVar48 != 0; uVar48 = uVar48 - 1) {
            *puVar54 = *param_2;
            param_2 = param_2 + 1;
            puVar54 = puVar54 + 1;
          }
        }
        uVar47 = param_3 & 0x7f;
        for (uVar48 = param_3 >> 7; param_3 = 0, uVar48 != 0; uVar48 = uVar48 - 1) {
          uVar55 = param_2[1];
          uVar2 = param_2[2];
          uVar34 = param_2[3];
          uVar35 = param_2[4];
          uVar36 = param_2[5];
          uVar37 = param_2[6];
          uVar38 = param_2[7];
          uVar39 = param_2[8];
          uVar40 = param_2[9];
          uVar41 = param_2[10];
          uVar42 = param_2[0xb];
          uVar43 = param_2[0xc];
          uVar44 = param_2[0xd];
          uVar45 = param_2[0xe];
          uVar46 = param_2[0xf];
          *puVar54 = *param_2;
          puVar54[1] = uVar55;
          puVar54[2] = uVar2;
          puVar54[3] = uVar34;
          puVar54[4] = uVar35;
          puVar54[5] = uVar36;
          puVar54[6] = uVar37;
          puVar54[7] = uVar38;
          puVar54[8] = uVar39;
          puVar54[9] = uVar40;
          puVar54[10] = uVar41;
          puVar54[0xb] = uVar42;
          puVar54[0xc] = uVar43;
          puVar54[0xd] = uVar44;
          puVar54[0xe] = uVar45;
          puVar54[0xf] = uVar46;
          uVar55 = param_2[0x11];
          uVar2 = param_2[0x12];
          uVar34 = param_2[0x13];
          uVar35 = param_2[0x14];
          uVar36 = param_2[0x15];
          uVar37 = param_2[0x16];
          uVar38 = param_2[0x17];
          uVar39 = param_2[0x18];
          uVar40 = param_2[0x19];
          uVar41 = param_2[0x1a];
          uVar42 = param_2[0x1b];
          uVar43 = param_2[0x1c];
          uVar44 = param_2[0x1d];
          uVar45 = param_2[0x1e];
          uVar46 = param_2[0x1f];
          puVar54[0x10] = param_2[0x10];
          puVar54[0x11] = uVar55;
          puVar54[0x12] = uVar2;
          puVar54[0x13] = uVar34;
          puVar54[0x14] = uVar35;
          puVar54[0x15] = uVar36;
          puVar54[0x16] = uVar37;
          puVar54[0x17] = uVar38;
          puVar54[0x18] = uVar39;
          puVar54[0x19] = uVar40;
          puVar54[0x1a] = uVar41;
          puVar54[0x1b] = uVar42;
          puVar54[0x1c] = uVar43;
          puVar54[0x1d] = uVar44;
          puVar54[0x1e] = uVar45;
          puVar54[0x1f] = uVar46;
          param_2 = param_2 + 0x20;
          puVar54 = puVar54 + 0x20;
        }
        goto LAB_10034a3d;
      }
      if (((DAT_1006a3dc & 1) == 0) || (((uint)param_1 & 3) != 0)) goto joined_r0x1003479d;
      if (((uint)param_2 & 3) == 0) {
        if (((uint)param_1 >> 2 & 1) != 0) {
          uVar47 = *param_2;
          param_3 = param_3 - 4;
          param_2 = param_2 + 1;
          *param_1 = uVar47;
          param_1 = param_1 + 1;
        }
        if (((uint)param_1 >> 3 & 1) != 0) {
          uVar1 = *(undefined8 *)param_2;
          param_3 = param_3 - 8;
          param_2 = param_2 + 2;
          *(undefined8 *)param_1 = uVar1;
          param_1 = param_1 + 2;
        }
        if (((uint)param_2 & 7) == 0) {
          puVar54 = param_2 + -2;
          uVar47 = *param_2;
          uVar48 = param_2[1];
          do {
            puVar49 = puVar54;
            uVar34 = puVar49[8];
            uVar35 = puVar49[9];
            param_3 = param_3 - 0x30;
            uVar36 = puVar49[6];
            uVar37 = puVar49[7];
            uVar38 = puVar49[8];
            uVar39 = puVar49[9];
            uVar55 = puVar49[0xe];
            uVar2 = puVar49[0xf];
            uVar40 = puVar49[10];
            uVar41 = puVar49[0xb];
            uVar42 = puVar49[0xc];
            uVar43 = puVar49[0xd];
            param_1[2] = uVar47;
            param_1[3] = uVar48;
            param_1[4] = uVar34;
            param_1[5] = uVar35;
            param_1[6] = uVar36;
            param_1[7] = uVar37;
            param_1[8] = uVar38;
            param_1[9] = uVar39;
            param_1[10] = uVar40;
            param_1[0xb] = uVar41;
            param_1[0xc] = uVar42;
            param_1[0xd] = uVar43;
            param_1 = param_1 + 0xc;
            puVar54 = puVar49 + 0xc;
            uVar47 = uVar55;
            uVar48 = uVar2;
          } while (0x2f < (int)param_3);
          puVar49 = puVar49 + 0xe;
        }
        else if (((uint)param_2 >> 3 & 1) == 0) {
          puVar54 = param_2 + -1;
          uVar47 = *param_2;
          uVar48 = param_2[1];
          uVar55 = param_2[2];
          do {
            puVar49 = puVar54;
            uVar36 = puVar49[8];
            param_3 = param_3 - 0x30;
            uVar37 = puVar49[5];
            uVar38 = puVar49[6];
            uVar39 = puVar49[7];
            uVar40 = puVar49[8];
            uVar2 = puVar49[0xd];
            uVar34 = puVar49[0xe];
            uVar35 = puVar49[0xf];
            uVar41 = puVar49[9];
            uVar42 = puVar49[10];
            uVar43 = puVar49[0xb];
            uVar44 = puVar49[0xc];
            param_1[1] = uVar47;
            param_1[2] = uVar48;
            param_1[3] = uVar55;
            param_1[4] = uVar36;
            param_1[5] = uVar37;
            param_1[6] = uVar38;
            param_1[7] = uVar39;
            param_1[8] = uVar40;
            param_1[9] = uVar41;
            param_1[10] = uVar42;
            param_1[0xb] = uVar43;
            param_1[0xc] = uVar44;
            param_1 = param_1 + 0xc;
            puVar54 = puVar49 + 0xc;
            uVar47 = uVar2;
            uVar48 = uVar34;
            uVar55 = uVar35;
          } while (0x2f < (int)param_3);
          puVar49 = puVar49 + 0xd;
        }
        else {
          puVar54 = param_2 + -3;
          uVar47 = *param_2;
          do {
            puVar49 = puVar54;
            uVar55 = puVar49[8];
            uVar2 = puVar49[9];
            uVar34 = puVar49[10];
            param_3 = param_3 - 0x30;
            uVar35 = puVar49[7];
            uVar36 = puVar49[8];
            uVar37 = puVar49[9];
            uVar38 = puVar49[10];
            uVar48 = puVar49[0xf];
            uVar39 = puVar49[0xb];
            uVar40 = puVar49[0xc];
            uVar41 = puVar49[0xd];
            uVar42 = puVar49[0xe];
            param_1[3] = uVar47;
            param_1[4] = uVar55;
            param_1[5] = uVar2;
            param_1[6] = uVar34;
            param_1[7] = uVar35;
            param_1[8] = uVar36;
            param_1[9] = uVar37;
            param_1[10] = uVar38;
            param_1[0xb] = uVar39;
            param_1[0xc] = uVar40;
            param_1[0xd] = uVar41;
            param_1[0xe] = uVar42;
            param_1 = param_1 + 0xc;
            puVar54 = puVar49 + 0xc;
            uVar47 = uVar48;
          } while (0x2f < (int)param_3);
          puVar49 = puVar49 + 0xf;
        }
        for (; 0xf < (int)param_3; param_3 = param_3 - 0x10) {
          uVar47 = *puVar49;
          uVar48 = puVar49[1];
          uVar55 = puVar49[2];
          uVar2 = puVar49[3];
          puVar49 = puVar49 + 4;
          *param_1 = uVar47;
          param_1[1] = uVar48;
          param_1[2] = uVar55;
          param_1[3] = uVar2;
          param_1 = param_1 + 4;
        }
        if ((param_3 >> 2 & 1) != 0) {
          uVar47 = *puVar49;
          param_3 = param_3 - 4;
          puVar49 = puVar49 + 1;
          *param_1 = uVar47;
          param_1 = param_1 + 1;
        }
        if ((param_3 >> 3 & 1) != 0) {
          param_3 = param_3 - 8;
          *(undefined8 *)param_1 = *(undefined8 *)puVar49;
        }
                    /* WARNING: Could not recover jumptable at 0x10034795. Too many branches */
                    /* WARNING: Treating indirect jump as call */
        uVar56 = (*(code *)(&switchD_100347c5::switchdataD_100347d4)[param_3])();
        return uVar56;
      }
    }
    uVar47 = param_3;
    if (0x1f < param_3) {
      for (uVar47 = param_3 >> 2; uVar47 != 0; uVar47 = uVar47 - 1) {
        *puVar54 = *param_2;
        param_2 = param_2 + 1;
        puVar54 = puVar54 + 1;
      }
      switch(param_3 & 3) {
      case 0:
        return CONCAT44(param_3,param_1) & 0x3ffffffff;
      case 1:
        *(char *)puVar54 = (char)*param_2;
        return CONCAT44(param_3,param_1) & 0x3ffffffff;
      case 2:
        *(char *)puVar54 = (char)*param_2;
        *(undefined1 *)((int)puVar54 + 1) = *(undefined1 *)((int)param_2 + 1);
        return CONCAT44(param_3,param_1) & 0x3ffffffff;
      case 3:
        *(char *)puVar54 = (char)*param_2;
        *(undefined1 *)((int)puVar54 + 1) = *(undefined1 *)((int)param_2 + 1);
        *(undefined1 *)((int)puVar54 + 2) = *(undefined1 *)((int)param_2 + 2);
        return CONCAT44(param_3,param_1) & 0x3ffffffff;
      }
    }
  }
LAB_10034a6b:
  if ((uVar47 & 0x1f) != 0) {
    for (uVar48 = (uVar47 & 0x1f) >> 2; uVar48 != 0; uVar48 = uVar48 - 1) {
      param_3 = *param_2;
      *puVar54 = param_3;
      puVar54 = puVar54 + 1;
      param_2 = param_2 + 1;
    }
    for (uVar47 = uVar47 & 3; uVar47 != 0; uVar47 = uVar47 - 1) {
      *(char *)puVar54 = (char)*param_2;
      param_2 = (uint *)((int)param_2 + 1);
      puVar54 = (uint *)((int)puVar54 + 1);
    }
  }
LAB_10034aa0:
  return CONCAT44(param_3,param_1);
}



//===== FUN_100173b0 @ 100173b0 size=761 =====

/* WARNING: Removing unreachable block (ram,0x10017439) */

int __thiscall FUN_100173b0(void *this,char *param_1,void *param_2)

{
  HANDLE pvVar1;
  int iVar2;
  int iVar3;
  uint in_stack_0000001c;
  undefined1 uVar4;
  undefined *puVar5;
  void *local_10;
  undefined1 *puStack_c;
  undefined4 local_8;
  
  puStack_c = &LAB_10052ff8;
  local_10 = ExceptionList;
  ExceptionList = &local_10;
  puVar5 = &DAT_1006b3e8;
  local_8 = 0;
  FUN_100027f0(&DAT_1006b3e8,0,"WinInetClient.cpp",0x16f,"ivcspsa::WinInetClient::StartHTTPS",
               "\n------------------ Entering StartHTTPS----------------");
  iVar3 = 1;
  local_8 = CONCAT31(local_8._1_3_,1);
  while( true ) {
                    /* WARNING: Ignoring partial resolution of indirect */
    uVar4 = 0;
    FUN_10001da0(&stack0xffffffb8,(uint *)&param_2,0,0xffffffff);
    iVar2 = FUN_10017030(this,puVar5);
    if ((iVar2 == 0) || (5 < iVar3)) break;
    FUN_100027f0(&DAT_1006b3e8,3,"WinInetClient.cpp",0x176,"ivcspsa::WinInetClient::StartHTTPS",
                 "Connect to server failed for attempt: %d");
    iVar3 = iVar3 + 1;
    FUN_100027f0(&DAT_1006b3e8,0,"WinInetClient.cpp",0x178,"ivcspsa::WinInetClient::StartHTTPS",
                 "Closing connection");
    if (*(int *)((int)this + 0x144) != 0) {
      if (*(HANDLE *)((int)this + 0x154) != (HANDLE)0x0) {
        ResetEvent(*(HANDLE *)((int)this + 0x154));
        InternetCloseHandle();
        pvVar1 = *(HANDLE *)((int)this + 0x154);
        Sleep(0);
        WaitForSingleObject(pvVar1,500);
      }
      *(undefined4 *)((int)this + 0x144) = 0;
    }
    if (*(int *)((int)this + 0x140) != 0) {
      if (*(HANDLE *)((int)this + 0x154) != (HANDLE)0x0) {
        ResetEvent(*(HANDLE *)((int)this + 0x154));
        InternetCloseHandle();
        pvVar1 = *(HANDLE *)((int)this + 0x154);
        Sleep(0);
        WaitForSingleObject(pvVar1,500);
      }
      *(undefined4 *)((int)this + 0x140) = 0;
    }
    if (*(int *)((int)this + 0x13c) != 0) {
      InternetCloseHandle();
      InternetSetStatusCallback(*(undefined4 *)((int)this + 0x13c),0);
      *(undefined4 *)((int)this + 0x13c) = 0;
    }
    FUN_100027f0(&DAT_1006b3e8,0,"WinInetClient.cpp",0x185,"ivcspsa::WinInetClient::StartHTTPS",
                 "Waiting 500 ms...");
    puVar5 = (undefined *)0x1f4;
    Sleep(500);
  }
  if (iVar3 == 6) {
    FUN_100027f0(&DAT_1006b3e8,3,"WinInetClient.cpp",0x18a,"ivcspsa::WinInetClient::StartHTTPS",
                 " connect to server failed rc %d");
    if (0xf < in_stack_0000001c) {
      FUN_100021c0(param_2,in_stack_0000001c + 1);
    }
  }
  else {
    iVar2 = FUN_10017700(this,param_1);
    if (iVar2 == 0) {
      local_8 = 0;
      FUN_100027f0(&DAT_1006b3e8,0,"WinInetClient.cpp",0x19b,"ivcspsa::WinInetClient::StartHTTPS",
                   "Exit StartHTTPS");
      if (0xf < in_stack_0000001c) {
        FUN_100021c0(param_2,in_stack_0000001c + 1);
      }
      ExceptionList = local_10;
      return 0;
    }
    FUN_100027f0(&DAT_1006b3e8,3,"WinInetClient.cpp",400,"ivcspsa::WinInetClient::StartHTTPS",
                 " connect to server failed rc %d");
    if (0xf < in_stack_0000001c) {
      FUN_100021c0(param_2,in_stack_0000001c + 1);
      ExceptionList = local_10;
      return iVar2;
    }
  }
  ExceptionList = local_10;
  return iVar2;
}



//===== FUN_100109a0 @ 100109a0 size=320 =====

void __thiscall
FUN_100109a0(void *this,uint *param_1,uint *param_2,uint *param_3,undefined4 param_4,char *param_5)

{
  undefined4 uVar1;
  uint uVar2;
  uint *puVar3;
  uint in_stack_ffffff88;
  void *local_50 [4];
  undefined4 local_40;
  uint local_3c;
  uint *local_34;
  void *local_30 [4];
  undefined4 local_20;
  uint local_1c;
  uint local_18;
  void *local_10;
  undefined1 *puStack_c;
  undefined4 local_8;
  
  local_8 = 0xffffffff;
  puStack_c = &LAB_10052990;
  local_10 = ExceptionList;
  local_18 = DAT_100681bc ^ (uint)&stack0xfffffffc;
  ExceptionList = &local_10;
  local_34 = param_3;
  FUN_10010620(this,param_1);
  FUN_10010750(this,param_2);
  FUN_10010880(this,param_5);
  *(undefined4 *)((int)this + 0x80) = param_4;
  local_1c = 0xf;
  local_20 = 0;
  local_30[0] = (void *)((uint)local_30[0] & 0xffffff00);
  if ((char)*local_34 == '\0') {
    uVar2 = 0;
  }
  else {
    puVar3 = local_34;
    do {
      uVar2 = *puVar3;
      puVar3 = (uint *)((int)puVar3 + 1);
    } while ((char)uVar2 != '\0');
    uVar2 = (int)puVar3 - ((int)local_34 + 1);
  }
  FUN_10002340(local_30,local_34,uVar2);
  local_8 = 0;
  local_3c = 0xf;
  local_40 = 0;
  local_50[0] = (void *)((uint)local_50[0] & 0xffffff00);
  FUN_10001da0(local_50,(uint *)local_30,0,0xffffffff);
  local_8 = CONCAT31(local_8._1_3_,1);
  puVar3 = (uint *)(in_stack_ffffff88 & 0xffffff00);
  FUN_10001da0(&stack0xffffff88,(uint *)local_50,0,0xffffffff);
  uVar1 = FUN_10010380((undefined4 *)((int)this + 0x9c),';',0,puVar3);
  *(undefined4 *)((int)this + 0x7c) = uVar1;
  if (0xf < local_3c) {
    FUN_100021c0(local_50[0],local_3c + 1);
  }
  if (0xf < local_1c) {
    FUN_100021c0(local_30[0],local_1c + 1);
  }
  ExceptionList = local_10;
  __security_check_cookie(local_18 ^ (uint)&stack0xfffffffc);
  return;
}



//===== FUN_10016d10 @ 10016d10 size=740 =====

/* WARNING: Removing unreachable block (ram,0x10016de5) */
/* WARNING: Removing unreachable block (ram,0x10016e85) */

void __thiscall FUN_10016d10(void *this,void *param_1)

{
  HANDLE pvVar1;
  int iVar2;
  undefined4 *extraout_ECX;
  void *this_00;
  undefined4 *extraout_ECX_00;
  undefined4 *extraout_ECX_01;
  undefined4 *puVar3;
  uint uVar4;
  uint in_stack_00000018;
  undefined1 uVar5;
  uint *in_stack_ffffff9c;
  uint uStack_4c;
  void *local_34 [2];
  int local_2c [3];
  undefined4 *local_20;
  uint local_18;
  undefined1 *local_14;
  void *local_10;
  undefined1 *puStack_c;
  undefined4 local_8;
  
  puStack_c = &LAB_10052f90;
  local_10 = ExceptionList;
  uStack_4c = DAT_100681bc ^ (uint)&stack0xfffffffc;
  local_14 = (undefined1 *)&uStack_4c;
  ExceptionList = &local_10;
  local_2c[0] = (int)this + 0x14c;
  local_8 = 1;
  uVar4 = 0;
  local_2c[1] = (int)this + 0x148;
  local_2c[2] = (int)this + 0x150;
  local_20 = (undefined4 *)((int)this + 0x154);
  local_18 = uStack_4c;
  do {
    pvVar1 = CreateEventA((LPSECURITY_ATTRIBUTES)0x0,1,0,(LPCSTR)0x0);
    puVar3 = (undefined4 *)local_2c[uVar4];
    *puVar3 = pvVar1;
    if (pvVar1 == (HANDLE)0x0) {
      GetLastError();
      puVar3 = extraout_ECX;
      break;
    }
    uVar4 = uVar4 + 1;
  } while (uVar4 < 4);
  if (DAT_1006b328 == 0) {
    local_20 = (undefined4 *)0xf;
    local_2c[2] = 0;
    local_34[0] = (void *)((uint)local_34[0] & 0xffffff00);
    FUN_10001da0(local_34,(uint *)&param_1,0,0xffffffff);
    local_8._0_1_ = 2;
                    /* WARNING: Ignoring partial resolution of indirect */
    uVar5 = 0;
    FUN_10001da0(&stack0xffffff9c,(uint *)local_34,0,0xffffffff);
    iVar2 = FUN_1000d990(this_00,(void **)&DAT_1006b318,in_stack_ffffff9c);
    local_8 = CONCAT31(local_8._1_3_,1);
    puVar3 = local_20;
    if ((undefined4 *)0xf < local_20) {
      FUN_100021c0(local_34[0],(int)local_20 + 1);
      puVar3 = extraout_ECX_00;
    }
    if (iVar2 == 0) {
      *(undefined4 *)((int)this + 0x110) = 9;
      if (0xf < in_stack_00000018) {
        FUN_100021c0(param_1,in_stack_00000018 + 1);
      }
      goto LAB_10016fd6;
    }
  }
  iVar2 = FUN_10001940(&param_1,(int *)&DAT_1005f254,puVar3,3);
  if ((iVar2 == 0) && (DAT_1006b4e0 == '\0')) {
    DAT_1006b4e0 = '\x01';
                    /* WARNING: Ignoring partial resolution of indirect */
    uVar5 = 0;
    FUN_10001da0(&stack0xffffff9c,(uint *)&param_1,0,0xffffffff);
    FUN_100181a0(this,in_stack_ffffff9c);
    FUN_10001da0(&DAT_1006b300,(uint *)&param_1,0,0xffffffff);
  }
  if ((undefined4 *)((int)this + 0xb4) != &DAT_1006b34c) {
    FUN_10001da0((undefined4 *)((int)this + 0xb4),&DAT_1006b34c,0,0xffffffff);
  }
  *(undefined1 *)((int)this + 0xb0) = DAT_1006b348;
  *(undefined2 *)((int)this + 0x158) = DAT_1006b37c;
  if ((undefined4 *)((int)this + 0xd8) != &DAT_1006b364) {
    FUN_10001da0((undefined4 *)((int)this + 0xd8),&DAT_1006b364,0,0xffffffff);
  }
  if ((undefined4 *)((int)this + 0x38) != &DAT_1006b318) {
    FUN_10001da0((undefined4 *)((int)this + 0x38),&DAT_1006b318,0,0xffffffff);
  }
  if ((undefined4 *)((int)this + 0x50) != &DAT_1006b330) {
    FUN_10001da0((undefined4 *)((int)this + 0x50),&DAT_1006b330,0,0xffffffff);
  }
  if ((undefined4 *)((int)this + 0x98) != &DAT_1006b398) {
    FUN_10001da0((undefined4 *)((int)this + 0x98),&DAT_1006b398,0,0xffffffff);
  }
  puVar3 = (undefined4 *)((int)this + 0x20);
  if (puVar3 != &DAT_1006b380) {
    FUN_10001da0(puVar3,&DAT_1006b380,0,0xffffffff);
    puVar3 = extraout_ECX_01;
  }
  *(undefined1 *)((int)this + 0xd4) = DAT_1006ab1c;
  iVar2 = FUN_10001940(&param_1,(int *)&DAT_1005f254,puVar3,3);
  if (iVar2 == 0) {
    *(undefined1 *)((int)this + 0x138) = DAT_1006b3b0;
  }
  local_8 = 0;
  FUN_100027f0(&DAT_1006b3e8,0,"WinInetClient.cpp",0xe2,"ivcspsa::WinInetClient::SetupServerInfo",
               "Exit SetupServerInfo");
  if (0xf < in_stack_00000018) {
    FUN_100021c0(param_1,in_stack_00000018 + 1);
  }
LAB_10016fd6:
  ExceptionList = local_10;
  __security_check_cookie(local_18 ^ (uint)&stack0xfffffffc);
  return;
}



//===== FUN_1000bf40 @ 1000bf40 size=118 =====

uint * __thiscall FUN_1000bf40(void *this,uint *param_1)

{
  undefined1 *puVar1;
  void *local_10;
  undefined1 *puStack_c;
  undefined4 uStack_8;
  
  uStack_8 = 0xffffffff;
  puStack_c = &LAB_100519e0;
  local_10 = ExceptionList;
  ExceptionList = &local_10;
  if (this != param_1) {
    if (0xf < *(uint *)((int)this + 0x14)) {
      FUN_100021c0(*(void **)this,*(uint *)((int)this + 0x14) + 1);
    }
    *(undefined4 *)((int)this + 0x14) = 0xf;
    *(undefined4 *)((int)this + 0x10) = 0;
    puVar1 = this;
    if (0xf < *(uint *)((int)this + 0x14)) {
      puVar1 = *(undefined1 **)this;
    }
    *puVar1 = 0;
    FUN_10001b80(this,param_1);
  }
  ExceptionList = local_10;
  return this;
}



//===== FUN_10008da0 @ 10008da0 size=735 =====

void __thiscall FUN_10008da0(void *this,uint *param_1,uint *param_2)

{
  char cVar1;
  undefined4 ***pppuVar2;
  int iVar3;
  uint uVar4;
  char *pcVar5;
  uint *puVar6;
  uint *local_1a4;
  uint *local_1a0;
  undefined4 local_19c [21];
  void *local_148 [4];
  undefined4 local_138;
  uint local_134;
  undefined4 **local_130 [4];
  undefined4 local_120;
  uint local_11c;
  DWORD local_118;
  undefined4 local_114;
  uint local_14;
  void *local_10;
  undefined1 *puStack_c;
  undefined4 local_8;
  
  local_8 = 0xffffffff;
  puStack_c = &LAB_10051d91;
  local_10 = ExceptionList;
  local_14 = DAT_100681bc ^ (uint)&stack0xfffffffc;
  ExceptionList = &local_10;
  local_1a0 = (uint *)0x0;
  local_1a4 = (uint *)0x0;
  local_118 = 0x100;
  GetUserNameA((LPSTR)&local_114,&local_118);
  local_134 = 0xf;
  local_138 = 0;
  local_148[0] = (void *)((uint)local_148[0] & 0xffffff00);
  if ((char)local_114 == '\0') {
    uVar4 = 0;
  }
  else {
    pcVar5 = (char *)&local_114;
    do {
      cVar1 = *pcVar5;
      pcVar5 = pcVar5 + 1;
    } while (cVar1 != '\0');
    uVar4 = (int)pcVar5 - ((int)&local_114 + 1);
  }
  FUN_10002340(local_148,&local_114,uVar4);
  local_8 = 0;
  _memset(local_19c,0,0x50);
  FUN_10009180(local_19c);
  local_8._0_1_ = 1;
  FUN_10009080(local_19c,(uint *)local_130,(byte *)local_148);
  local_8 = CONCAT31(local_8._1_3_,2);
  pppuVar2 = local_130;
  if (7 < local_11c) {
    pppuVar2 = (undefined4 ***)local_130[0];
  }
  iVar3 = FUN_10002770(this,pppuVar2,&local_1a0,&local_1a4);
  if (iVar3 == 0) {
    if (local_1a0 != (uint *)0x0) {
      if ((short)*local_1a0 == 0) {
        uVar4 = 0;
      }
      else {
        puVar6 = local_1a0;
        do {
          uVar4 = *puVar6;
          puVar6 = (uint *)((int)puVar6 + 2);
        } while ((short)uVar4 != 0);
        uVar4 = (int)puVar6 - ((int)local_1a0 + 2) >> 1;
      }
      FUN_1000ab00((void *)((int)this + 0x2c),local_1a0,uVar4);
      FUN_100027f0(&DAT_1006ac38,0,"ClientCallbackImpl.cpp",0x87,
                   "ClientCallbackImpl::GetWebProxyCredentials","Received UserName");
    }
    if (local_1a4 != (uint *)0x0) {
      if ((short)*local_1a4 == 0) {
        uVar4 = 0;
      }
      else {
        puVar6 = local_1a4;
        do {
          uVar4 = *puVar6;
          puVar6 = (uint *)((int)puVar6 + 2);
        } while ((short)uVar4 != 0);
        uVar4 = (int)puVar6 - ((int)local_1a4 + 2) >> 1;
      }
      FUN_1000ab00((void *)((int)this + 0x44),local_1a4,uVar4);
      FUN_100027f0(&DAT_1006ac38,0,"ClientCallbackImpl.cpp",0x8f,
                   "ClientCallbackImpl::GetWebProxyCredentials","Received Password");
    }
    if (param_1 != (uint *)((int)this + 0x2c)) {
      FUN_1000a770(param_1,(uint *)((int)this + 0x2c),0,0xffffffff);
    }
    if (param_2 != (uint *)((int)this + 0x44)) {
      FUN_1000a770(param_2,(uint *)((int)this + 0x44),0,0xffffffff);
    }
    FUN_100027f0(&DAT_1006ac38,0,"ClientCallbackImpl.cpp",0x97,
                 "ClientCallbackImpl::GetWebProxyCredentials",
                 " EXIT GetWebProxyCredentials() callback");
  }
  else {
    FUN_100027f0(&DAT_1006ac38,3,"ClientCallbackImpl.cpp",0x7f,
                 "ClientCallbackImpl::GetWebProxyCredentials","Failed to get requested data from UI"
                );
  }
  if (7 < local_11c) {
    FUN_1000acd0(local_130[0],local_11c + 1);
  }
  local_11c = 7;
  local_120 = 0;
  local_130[0] = (undefined4 **)((uint)local_130[0] & 0xffff0000);
  FUN_100090c0(local_19c);
  if (0xf < local_134) {
    FUN_100021c0(local_148[0],local_134 + 1);
  }
  ExceptionList = local_10;
  __security_check_cookie(local_14 ^ (uint)&stack0xfffffffc);
  return;
}



//===== FUN_100088f0 @ 100088f0 size=78 =====

undefined4 * __fastcall FUN_100088f0(undefined4 *param_1)

{
  *param_1 = 0;
  param_1[1] = 0;
  param_1[2] = 0;
  param_1[3] = 0;
  param_1[9] = 7;
  param_1[8] = 0;
  *(undefined2 *)(param_1 + 4) = 0;
  param_1[0xf] = 0;
  param_1[0x10] = 7;
  *(undefined2 *)(param_1 + 0xb) = 0;
  param_1[0x15] = 0;
  param_1[0x16] = 7;
  *(undefined2 *)(param_1 + 0x11) = 0;
  return param_1;
}



//===== FUN_10001c70 @ 10001c70 size=52 =====

void __fastcall FUN_10001c70(undefined4 *param_1)

{
  if (0xf < (uint)param_1[5]) {
    FUN_100021c0((void *)*param_1,param_1[5] + 1);
  }
  param_1[5] = 0xf;
  param_1[4] = 0;
  if (0xf < (uint)param_1[5]) {
    *(undefined1 *)*param_1 = 0;
    return;
  }
  *(undefined1 *)param_1 = 0;
  return;
}



//===== FUN_100119c9 @ 100119c9 size=30 =====

void FUN_100119c9(void)

{
  uint unaff_EBP;
  undefined4 uStack0000000c;
  
  ExceptionList = *(void **)(unaff_EBP - 0xc);
  uStack0000000c = 0x100119e3;
  __security_check_cookie(*(uint *)(unaff_EBP - 0x14) ^ unaff_EBP);
  return;
}



//===== FUN_10001da0 @ 10001da0 size=287 =====

uint * __thiscall FUN_10001da0(void *this,uint *param_1,uint param_2,uint param_3)

{
  uint *puVar1;
  uint uVar2;
  
  if (param_1[4] < param_2) {
                    /* WARNING: Subroutine does not return */
    FUN_10019412("invalid string position");
  }
  uVar2 = param_1[4] - param_2;
  if (param_3 < uVar2) {
    uVar2 = param_3;
  }
  if (this == param_1) {
    uVar2 = uVar2 + param_2;
    if (*(uint *)((int)this + 0x10) < uVar2) {
                    /* WARNING: Subroutine does not return */
      FUN_10019412("invalid string position");
    }
    *(uint *)((int)this + 0x10) = uVar2;
    if (0xf < *(uint *)((int)this + 0x14)) {
      *(undefined1 *)(*(int *)this + uVar2) = 0;
      FUN_10001d00(this,0,param_2);
      return this;
    }
    *(undefined1 *)((int)this + uVar2) = 0;
    FUN_10001d00(this,0,param_2);
    return this;
  }
  if (uVar2 == 0xffffffff) {
                    /* WARNING: Subroutine does not return */
    FUN_100193f2("string too long");
  }
  if (*(uint *)((int)this + 0x14) < uVar2) {
    FUN_10001fa0(this,uVar2,*(uint *)((int)this + 0x10));
    if (uVar2 == 0) {
      return this;
    }
  }
  else if (uVar2 == 0) {
    *(undefined4 *)((int)this + 0x10) = 0;
    if (0xf < *(uint *)((int)this + 0x14)) {
      **(undefined1 **)this = 0;
      return this;
    }
    *(undefined1 *)this = 0;
    return this;
  }
  if (0xf < param_1[5]) {
    param_1 = (uint *)*param_1;
  }
  puVar1 = this;
  if (0xf < *(uint *)((int)this + 0x14)) {
    puVar1 = *(uint **)this;
  }
  if (uVar2 != 0) {
    FUN_10034570(puVar1,(uint *)((int)param_1 + param_2),uVar2);
  }
  *(uint *)((int)this + 0x10) = uVar2;
  if (*(uint *)((int)this + 0x14) < 0x10) {
    *(undefined1 *)((int)this + uVar2) = 0;
    return this;
  }
  *(undefined1 *)(*(int *)this + uVar2) = 0;
  return this;
}



//===== FUN_1000e850 @ 1000e850 size=565 =====

void __fastcall FUN_1000e850(undefined4 *param_1)

{
  undefined4 *puVar1;
  
  *param_1 = CWSDLEncoder::vftable;
  if ((undefined4 *)param_1[0x27] != (undefined4 *)0x0) {
    FUN_1000c7c0((undefined4 *)param_1[0x27],(undefined4 *)param_1[0x28]);
    FUN_1000c2d0((void *)param_1[0x27],(param_1[0x29] - (int)param_1[0x27]) / 0x18);
    param_1[0x27] = 0;
    param_1[0x28] = 0;
    param_1[0x29] = 0;
  }
  if ((undefined4 *)param_1[0x24] != (undefined4 *)0x0) {
    FUN_1000c7c0((undefined4 *)param_1[0x24],(undefined4 *)param_1[0x25]);
    FUN_1000c2d0((void *)param_1[0x24],(param_1[0x26] - (int)param_1[0x24]) / 0x18);
    param_1[0x24] = 0;
    param_1[0x25] = 0;
    param_1[0x26] = 0;
  }
  if ((undefined4 *)param_1[0x21] != (undefined4 *)0x0) {
    FUN_1000c7c0((undefined4 *)param_1[0x21],(undefined4 *)param_1[0x22]);
    FUN_1000c2d0((void *)param_1[0x21],(param_1[0x23] - (int)param_1[0x21]) / 0x18);
    param_1[0x21] = 0;
    param_1[0x22] = 0;
    param_1[0x23] = 0;
  }
  puVar1 = param_1 + 0x19;
  if (7 < (uint)param_1[0x1e]) {
    FUN_1000acd0((void *)*puVar1,param_1[0x1e] + 1);
  }
  param_1[0x1e] = 7;
  param_1[0x1d] = 0;
  if (7 < (uint)param_1[0x1e]) {
    puVar1 = (undefined4 *)*puVar1;
  }
  *(undefined2 *)puVar1 = 0;
  puVar1 = param_1 + 0x13;
  if (7 < (uint)param_1[0x18]) {
    FUN_1000acd0((void *)*puVar1,param_1[0x18] + 1);
  }
  param_1[0x18] = 7;
  param_1[0x17] = 0;
  if (7 < (uint)param_1[0x18]) {
    puVar1 = (undefined4 *)*puVar1;
  }
  *(undefined2 *)puVar1 = 0;
  puVar1 = param_1 + 0xd;
  if (7 < (uint)param_1[0x12]) {
    FUN_1000acd0((void *)*puVar1,param_1[0x12] + 1);
  }
  param_1[0x12] = 7;
  param_1[0x11] = 0;
  if (7 < (uint)param_1[0x12]) {
    puVar1 = (undefined4 *)*puVar1;
  }
  *(undefined2 *)puVar1 = 0;
  puVar1 = param_1 + 7;
  if (7 < (uint)param_1[0xc]) {
    FUN_1000acd0((void *)*puVar1,param_1[0xc] + 1);
  }
  param_1[0xc] = 7;
  param_1[0xb] = 0;
  if (7 < (uint)param_1[0xc]) {
    puVar1 = (undefined4 *)*puVar1;
  }
  *(undefined2 *)puVar1 = 0;
  if (7 < (uint)param_1[6]) {
    FUN_1000acd0((void *)param_1[1],param_1[6] + 1);
  }
  param_1[6] = 7;
  param_1[5] = 0;
  if (7 < (uint)param_1[6]) {
    *(undefined2 *)param_1[1] = 0;
    return;
  }
  *(undefined2 *)(param_1 + 1) = 0;
  return;
}



//===== FUN_10002340 @ 10002340 size=245 =====

uint * __thiscall FUN_10002340(void *this,uint *param_1,uint param_2)

{
  uint uVar1;
  uint *puVar2;
  void *pvVar3;
  
  if (param_1 != (uint *)0x0) {
    uVar1 = *(uint *)((int)this + 0x14);
    puVar2 = this;
    if (0xf < uVar1) {
      puVar2 = *(uint **)this;
    }
    if (puVar2 <= param_1) {
      pvVar3 = this;
      if (0xf < uVar1) {
        pvVar3 = *(void **)this;
      }
      if (param_1 < (uint *)(*(int *)((int)this + 0x10) + (int)pvVar3)) {
        if (0xf < uVar1) {
          puVar2 = FUN_10001da0(this,this,(int)param_1 - *(int *)this,param_2);
          return puVar2;
        }
        puVar2 = FUN_10001da0(this,this,(int)param_1 - (int)this,param_2);
        return puVar2;
      }
    }
  }
  if (param_2 == 0xffffffff) {
                    /* WARNING: Subroutine does not return */
    FUN_100193f2("string too long");
  }
  if (*(uint *)((int)this + 0x14) < param_2) {
    FUN_10001fa0(this,param_2,*(uint *)((int)this + 0x10));
    if (param_2 == 0) {
      return this;
    }
  }
  else if (param_2 == 0) {
    *(undefined4 *)((int)this + 0x10) = 0;
    if (0xf < *(uint *)((int)this + 0x14)) {
      **(undefined1 **)this = 0;
      return this;
    }
    *(undefined1 *)this = 0;
    return this;
  }
  puVar2 = this;
  if (0xf < *(uint *)((int)this + 0x14)) {
    puVar2 = *(uint **)this;
  }
  if (param_2 != 0) {
    FUN_10034570(puVar2,param_1,param_2);
  }
  *(uint *)((int)this + 0x10) = param_2;
  if (*(uint *)((int)this + 0x14) < 0x10) {
    *(undefined1 *)((int)this + param_2) = 0;
    return this;
  }
  *(undefined1 *)(*(int *)this + param_2) = 0;
  return this;
}



//===== FUN_10010ef0 @ 10010ef0 size=56 =====

undefined1 * __thiscall FUN_10010ef0(void *this,undefined1 *param_1)

{
  *(undefined4 *)(param_1 + 0x14) = 0xf;
  *(undefined4 *)(param_1 + 0x10) = 0;
  *param_1 = 0;
  FUN_10001da0(param_1,(uint *)((int)this + 8),0,0xffffffff);
  return param_1;
}



//===== FUN_10006e50 @ 10006e50 size=42 =====

undefined1 * __thiscall FUN_10006e50(void *this,uint *param_1)

{
  *(undefined4 *)((int)this + 0x14) = 0xf;
  *(undefined4 *)((int)this + 0x10) = 0;
  *(undefined1 *)this = 0;
  FUN_10001da0(this,param_1,0,0xffffffff);
  return this;
}



//===== GetTickCount64 @ EXTERNAL:00000011 size=0 =====
// decompile failed

//===== FUN_1000acd0 @ 1000acd0 size=89 =====

void FUN_1000acd0(void *param_1,uint param_2)

{
  void *_Memory;
  
  if (0x7fffffff < param_2) {
                    /* WARNING: Subroutine does not return */
    FUN_10037231();
  }
  _Memory = param_1;
  if (0xfff < param_2 * 2) {
    if (((uint)param_1 & 0x1f) != 0) {
                    /* WARNING: Subroutine does not return */
      FUN_10037231();
    }
    _Memory = *(void **)((int)param_1 + -4);
    if (param_1 <= _Memory) {
                    /* WARNING: Subroutine does not return */
      FUN_10037231();
    }
    if ((uint)((int)param_1 - (int)_Memory) < 4) {
                    /* WARNING: Subroutine does not return */
      FUN_10037231();
    }
    if (0x23 < (uint)((int)param_1 - (int)_Memory)) {
                    /* WARNING: Subroutine does not return */
      FUN_10037231();
    }
  }
  FID_conflict__free(_Memory);
  return;
}



//===== FUN_10009180 @ 10009180 size=206 =====

undefined4 * __fastcall FUN_10009180(undefined4 *param_1)

{
  _Locimp *p_Var1;
  undefined4 *puVar2;
  facet *pfVar3;
  void *local_10;
  undefined1 *puStack_c;
  undefined4 local_8;
  
  puStack_c = &LAB_10051df6;
  local_10 = ExceptionList;
  ExceptionList = &local_10;
  *param_1 = std::
             wstring_convert<class_std::codecvt_utf8_utf16<wchar_t,1114111,0>,wchar_t,class_std::allocator<wchar_t>,class_std::allocator<char>_>
             ::vftable;
  local_8 = 0;
  p_Var1 = std::locale::_Init(true);
  param_1[3] = p_Var1;
  puVar2 = param_1 + 4;
  param_1[9] = 0xf;
  param_1[8] = 0;
  if (0xf < (uint)param_1[9]) {
    puVar2 = (undefined4 *)*puVar2;
  }
  *(undefined1 *)puVar2 = 0;
  puVar2 = param_1 + 10;
  param_1[0xf] = 7;
  param_1[0xe] = 0;
  if (7 < (uint)param_1[0xf]) {
    puVar2 = (undefined4 *)*puVar2;
  }
  *(undefined2 *)puVar2 = 0;
  local_8._0_1_ = 3;
  local_8._1_3_ = 0;
  *(undefined2 *)(param_1 + 0x12) = 0;
  *(undefined1 *)((int)param_1 + 0x4a) = 0;
  pfVar3 = operator_new(0x34);
  local_8._0_1_ = 4;
  FUN_10009ff0((undefined4 *)pfVar3);
  *(undefined ***)pfVar3 = std::codecvt_utf8_utf16<wchar_t,1114111,0>::vftable;
  local_8 = CONCAT31(local_8._1_3_,3);
  FUN_10009b70(param_1,pfVar3);
  ExceptionList = local_10;
  return param_1;
}



//===== FUN_100096a0 @ 100096a0 size=120 =====

uint * __thiscall FUN_100096a0(void *this,uint *param_1)

{
  undefined2 *puVar1;
  void *local_10;
  undefined1 *puStack_c;
  undefined4 uStack_8;
  
  uStack_8 = 0xffffffff;
  puStack_c = &LAB_100519e0;
  local_10 = ExceptionList;
  ExceptionList = &local_10;
  if (this != param_1) {
    if (7 < *(uint *)((int)this + 0x14)) {
      FUN_1000acd0(*(void **)this,*(uint *)((int)this + 0x14) + 1);
    }
    *(undefined4 *)((int)this + 0x14) = 7;
    *(undefined4 *)((int)this + 0x10) = 0;
    puVar1 = this;
    if (7 < *(uint *)((int)this + 0x14)) {
      puVar1 = *(undefined2 **)this;
    }
    *puVar1 = 0;
    FUN_1000a270(this,param_1);
  }
  ExceptionList = local_10;
  return this;
}



//===== FUN_10011bd0 @ 10011bd0 size=53 =====

uint * __thiscall FUN_10011bd0(void *this,uint *param_1,char *param_2)

{
  char *pcVar1;
  
  pcVar1 = param_2;
  if (7 < *(uint *)(param_2 + 0x14)) {
    pcVar1 = *(char **)param_2;
  }
  FUN_10011c80(this,param_1,pcVar1,pcVar1 + *(int *)(param_2 + 0x10) * 2);
  return param_1;
}



//===== FUN_100090c0 @ 100090c0 size=188 =====

void __fastcall FUN_100090c0(undefined4 *param_1)

{
  uint uVar1;
  undefined4 *puVar2;
  void *local_10;
  undefined1 *puStack_c;
  undefined4 local_8;
  
  local_8 = 0xffffffff;
  puStack_c = &LAB_100513e6;
  local_10 = ExceptionList;
  uVar1 = DAT_100681bc ^ (uint)&stack0xfffffffc;
  ExceptionList = &local_10;
  puVar2 = param_1 + 10;
  *param_1 = std::
             wstring_convert<class_std::codecvt_utf8_utf16<wchar_t,1114111,0>,wchar_t,class_std::allocator<wchar_t>,class_std::allocator<char>_>
             ::vftable;
  if (7 < (uint)param_1[0xf]) {
    FUN_1000acd0((void *)*puVar2,param_1[0xf] + 1);
  }
  param_1[0xf] = 7;
  param_1[0xe] = 0;
  if (7 < (uint)param_1[0xf]) {
    puVar2 = (undefined4 *)*puVar2;
  }
  *(undefined2 *)puVar2 = 0;
  puVar2 = param_1 + 4;
  if (0xf < (uint)param_1[9]) {
    FUN_100021c0((void *)*puVar2,param_1[9] + 1);
  }
  param_1[9] = 0xf;
  param_1[8] = 0;
  if (0xf < (uint)param_1[9]) {
    puVar2 = (undefined4 *)*puVar2;
  }
  *(undefined1 *)puVar2 = 0;
  local_8 = 0;
  if ((int *)param_1[3] != (int *)0x0) {
    puVar2 = (undefined4 *)(**(code **)(*(int *)param_1[3] + 8))(uVar1);
    if (puVar2 != (undefined4 *)0x0) {
      (**(code **)*puVar2)(1);
    }
  }
  ExceptionList = local_10;
  return;
}



//===== FUN_10009da0 @ 10009da0 size=43 =====

undefined2 * __thiscall FUN_10009da0(void *this,uint *param_1)

{
  *(undefined4 *)((int)this + 0x14) = 7;
  *(undefined4 *)((int)this + 0x10) = 0;
  *(undefined2 *)this = 0;
  FUN_1000a770(this,param_1,0,0xffffffff);
  return this;
}



//===== FUN_10016c70 @ 10016c70 size=156 =====

undefined4 FUN_10016c70(void *param_1)

{
  undefined4 uStack00000014;
  uint in_stack_00000018;
  void *in_stack_0000001c;
  uint in_stack_00000030;
  void *local_10;
  undefined1 *puStack_c;
  undefined4 local_8;
  
  puStack_c = &LAB_10052f60;
  local_10 = ExceptionList;
  ExceptionList = &local_10;
  local_8 = 1;
  FUN_10001da0(&DAT_1006b3b4,(uint *)&param_1,0,0xffffffff);
  FUN_10001da0(&DAT_1006b3cc,(uint *)&stack0x0000001c,0,0xffffffff);
  if (0xf < in_stack_00000018) {
    FUN_100021c0(param_1,in_stack_00000018 + 1);
  }
  in_stack_00000018 = 0xf;
  uStack00000014 = 0;
  param_1 = (void *)((uint)param_1 & 0xffffff00);
  if (0xf < in_stack_00000030) {
    FUN_100021c0(in_stack_0000001c,in_stack_00000030 + 1);
  }
  ExceptionList = local_10;
  return 0;
}



//===== GetModuleHandleExA @ EXTERNAL:0000000b size=0 =====
// decompile failed

//===== FUN_10011b70 @ 10011b70 size=91 =====

/* WARNING: Removing unreachable block (ram,0x10011bc1) */

int * __thiscall FUN_10011b70(void *this,uint param_1)

{
  undefined4 uVar1;
  
  *(undefined4 *)this = 0;
  *(undefined4 *)((int)this + 4) = 0;
  *(undefined4 *)((int)this + 8) = 0;
  if (param_1 != 0) {
    uVar1 = FUN_10001f30(param_1);
    *(undefined4 *)this = uVar1;
    *(undefined4 *)((int)this + 4) = uVar1;
    *(uint *)((int)this + 8) = *(int *)this + param_1;
    _memset(*(void **)this,0,param_1);
    *(int *)((int)this + 4) = *(int *)((int)this + 4) + param_1;
  }
  return this;
}



//===== GetModuleFileNameA @ EXTERNAL:00000005 size=0 =====
// decompile failed

//===== FUN_10011c10 @ 10011c10 size=108 =====

/* WARNING: Removing unreachable block (ram,0x10011c63) */

void __fastcall FUN_10011c10(uint *param_1)

{
  void *pvVar1;
  void *_Memory;
  
  pvVar1 = (void *)*param_1;
  if (pvVar1 != (void *)0x0) {
    _Memory = pvVar1;
    if (0xfff < param_1[2] - (int)pvVar1) {
      if (((uint)pvVar1 & 0x1f) != 0) {
                    /* WARNING: Subroutine does not return */
        FUN_10037231();
      }
      _Memory = *(void **)((int)pvVar1 - 4);
      if (pvVar1 <= _Memory) {
                    /* WARNING: Subroutine does not return */
        FUN_10037231();
      }
      if ((uint)((int)pvVar1 - (int)_Memory) < 4) {
                    /* WARNING: Subroutine does not return */
        FUN_10037231();
      }
      if (0x23 < (uint)((int)pvVar1 - (int)_Memory)) {
                    /* WARNING: Subroutine does not return */
        FUN_10037231();
      }
    }
    FID_conflict__free(_Memory);
    *param_1 = 0;
    param_1[1] = 0;
    param_1[2] = 0;
  }
  return;
}



//===== VerQueryValueA @ EXTERNAL:00000062 size=0 =====
// decompile failed

//===== FUN_10002440 @ 10002440 size=81 =====

undefined1 * __thiscall FUN_10002440(void *this,uint *param_1)

{
  uint uVar1;
  uint *puVar2;
  
  *(undefined4 *)((int)this + 0x14) = 0xf;
  *(undefined4 *)((int)this + 0x10) = 0;
  *(undefined1 *)this = 0;
  if ((char)*param_1 == '\0') {
    FUN_10002340(this,param_1,0);
    return this;
  }
  puVar2 = param_1;
  do {
    uVar1 = *puVar2;
    puVar2 = (uint *)((int)puVar2 + 1);
  } while ((char)uVar1 != '\0');
  FUN_10002340(this,param_1,(int)puVar2 - ((int)param_1 + 1));
  return this;
}



//===== GetFileVersionInfoSizeA @ EXTERNAL:00000063 size=0 =====
// decompile failed

//===== GetFileVersionInfoA @ EXTERNAL:00000061 size=0 =====
// decompile failed

