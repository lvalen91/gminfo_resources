// === sa015bcr.dll ===
// ImageBase: 6ed00000

// 7 functions matched name-filter

// total with callees: 10
//===== sa015bcr @ 6ed014bf size=162 =====

/* sa015bcr */

int __cdecl sa015bcr(int param_1,undefined2 *param_2,int param_3,int param_4)

{
  int iVar1;
  undefined4 *puVar2;
  undefined4 *puVar3;
  undefined4 local_88 [4];
  undefined4 local_78 [13];
  int local_44;
  undefined4 local_40 [8];
  int local_20;
  
                    /* 0x14bf  2  sa015bcr */
  local_20 = parsePassword(param_2,local_78,param_1,param_3);
  if (local_20 == 0) {
    calc_hash_chain(local_44,local_78,local_40);
    puVar2 = local_40;
    puVar3 = local_88;
    for (iVar1 = 4; iVar1 != 0; iVar1 = iVar1 + -1) {
      *puVar3 = *puVar2;
      puVar2 = puVar2 + 1;
      puVar3 = puVar3 + 1;
    }
    iVar1 = calcMAC((int)local_88,param_1,param_4);
    if (iVar1 == 0) {
      local_20 = 0;
    }
    else {
      local_20 = 4;
    }
  }
  return local_20;
}



//===== getVersion @ 6ed01561 size=10 =====

/* getVersion */

undefined4 __cdecl getVersion(void)

{
                    /* 0x1561  1  getVersion */
  return _version;
}



//===== _EscSha256_UpdateHashFast @ 6ed016dc size=558 =====

void __fastcall _EscSha256_UpdateHashFast(undefined4 param_1,int param_2)

{
  uint uVar1;
  uint uVar2;
  uint uVar3;
  uint uVar4;
  uint uVar5;
  uint uVar6;
  uint uVar7;
  uint uVar8;
  uint uVar9;
  uint *in_EAX;
  uint uVar10;
  uint uVar11;
  uint uVar12;
  int iVar13;
  uint uVar14;
  uint uVar15;
  uint uVar16;
  uint uVar17;
  uint local_9c;
  uint local_98;
  uint local_94;
  uint local_68;
  uint auStack_51 [16];
  
  iVar13 = 0;
  do {
    *(uint *)((int)auStack_51 + iVar13) =
         (uint)*(byte *)(param_2 + iVar13) << 0x18 | (uint)*(byte *)(param_2 + 1 + iVar13) << 0x10 |
         (uint)*(byte *)(param_2 + 3 + iVar13) | (uint)*(byte *)(param_2 + 2 + iVar13) << 8;
    iVar13 = iVar13 + 4;
  } while (iVar13 != 0x40);
  uVar1 = *in_EAX;
  uVar14 = 0;
  uVar2 = in_EAX[1];
  uVar3 = in_EAX[2];
  uVar4 = in_EAX[3];
  uVar5 = in_EAX[4];
  uVar6 = in_EAX[5];
  uVar7 = in_EAX[6];
  uVar8 = in_EAX[7];
  uVar10 = uVar5;
  uVar17 = uVar1;
  uVar15 = uVar8;
  uVar12 = uVar2;
  local_9c = uVar7;
  local_98 = uVar3;
  local_94 = uVar6;
  local_68 = uVar4;
  while( true ) {
    uVar16 = uVar12;
    uVar12 = uVar17;
    uVar11 = uVar10;
    uVar9 = local_9c;
    iVar13 = *(int *)(&_K_960 + uVar14 * 4);
    if ((byte)uVar14 < 0x10) {
      uVar10 = auStack_51[uVar14];
    }
    else {
      uVar10 = auStack_51[uVar14 + 0xe & 0xf];
      uVar17 = auStack_51[uVar14 + 1 & 0xf];
      uVar10 = ((uVar17 >> 0x12 | uVar17 << 0xe) ^ (uVar17 >> 7 | uVar17 << 0x19) ^ uVar17 >> 3) +
               ((uVar10 >> 0x13 | uVar10 << 0xd) ^ (uVar10 >> 0x11 | uVar10 << 0xf) ^ uVar10 >> 10)
               + auStack_51[uVar14 + 9 & 0xf] + auStack_51[uVar14 & 0xf];
      auStack_51[uVar14 & 0xf] = uVar10;
    }
    iVar13 = uVar10 + ((local_9c ^ local_94) & uVar11 ^ local_9c) + iVar13 + uVar15 +
                      ((uVar11 >> 0xb | uVar11 << 0x15) ^ (uVar11 >> 6 | uVar11 << 0x1a) ^
                      (uVar11 >> 0x19 | uVar11 << 7));
    uVar10 = iVar13 + local_68;
    uVar14 = uVar14 + 1;
    uVar17 = ((uVar16 ^ uVar12) & local_98 | uVar16 & uVar12) +
             ((uVar12 >> 0xd | uVar12 << 0x13) ^ (uVar12 >> 2 | uVar12 << 0x1e) ^
             (uVar12 >> 0x16 | uVar12 << 10)) + iVar13;
    if (uVar14 == 0x40) break;
    local_9c = local_94;
    local_68 = local_98;
    uVar15 = uVar9;
    local_98 = uVar16;
    local_94 = uVar11;
  }
  in_EAX[1] = uVar12 + uVar2;
  in_EAX[3] = local_98 + uVar4;
  in_EAX[4] = uVar10 + uVar5;
  in_EAX[6] = local_94 + uVar7;
  *in_EAX = uVar17 + uVar1;
  in_EAX[2] = uVar16 + uVar3;
  in_EAX[5] = uVar11 + uVar6;
  in_EAX[7] = local_9c + uVar8;
  return;
}



//===== _EscSha256_Init @ 6ed0190a size=43 =====

undefined4 __cdecl _EscSha256_Init(int param_1)

{
  undefined4 in_EAX;
  int iVar1;
  undefined4 uVar2;
  
  uVar2 = CONCAT31((int3)((uint)in_EAX >> 8),1);
  if (param_1 != 0) {
    iVar1 = 0;
    do {
      *(undefined4 *)(param_1 + iVar1) = *(undefined4 *)((int)&_INITIAL_HASH_987 + iVar1);
      iVar1 = iVar1 + 4;
    } while (iVar1 != 0x20);
    *(undefined1 *)(param_1 + 0x60) = 0;
    *(undefined4 *)(param_1 + 0x61) = 0;
    uVar2 = 0;
  }
  return uVar2;
}



//===== _EscSha256_Update @ 6ed01935 size=210 =====

undefined4 __cdecl _EscSha256_Update(int param_1,int param_2,uint param_3)

{
  uint uVar1;
  byte bVar2;
  byte bVar3;
  undefined4 in_EAX;
  uint uVar4;
  undefined4 uVar5;
  uint extraout_ECX;
  uint uVar6;
  uint extraout_ECX_00;
  uint uVar7;
  uint uVar8;
  uint uVar9;
  
  if ((param_2 == 0) || (param_1 == 0)) {
    uVar5 = CONCAT31((int3)((uint)in_EAX >> 8),1);
  }
  else {
    uVar9 = 0;
    uVar1 = param_3 - 0x40;
    uVar6 = uVar1;
    while (param_3 != 0) {
      bVar2 = *(byte *)(param_1 + 0x60);
      if ((param_3 < 0x40) || (bVar2 != 0)) {
        uVar6 = 0x40 - bVar2;
        uVar4 = param_3;
        if (uVar6 <= param_3) {
          uVar4 = (uint)(byte)(0x40 - bVar2);
        }
        uVar7 = uVar4 & 0xff;
        param_3 = param_3 - uVar7;
        *(int *)(param_1 + 0x61) = *(int *)(param_1 + 0x61) + uVar7;
        uVar8 = uVar9;
        for (; (char)uVar4 != '\0'; uVar4 = uVar4 - 1) {
          bVar2 = *(byte *)(param_1 + 0x60);
          bVar3 = *(byte *)(param_2 + uVar8);
          uVar6 = (uint)bVar3;
          *(char *)(param_1 + 0x60) = *(char *)(param_1 + 0x60) + '\x01';
          uVar8 = uVar8 + 1;
          *(byte *)(param_1 + 0x20 + (uint)bVar2) = bVar3;
        }
        uVar9 = uVar9 + uVar7;
        if (*(char *)(param_1 + 0x60) == '@') {
          _EscSha256_UpdateHashFast(uVar6,param_1 + 0x20);
          *(undefined1 *)(param_1 + 0x60) = 0;
          uVar6 = extraout_ECX_00;
        }
      }
      else {
        uVar4 = param_3 & 0xffffffc0;
        param_3 = param_3 - uVar4;
        *(int *)(param_1 + 0x61) = *(int *)(param_1 + 0x61) + uVar4;
        for (; uVar9 <= uVar1; uVar9 = uVar9 + 0x40) {
          _EscSha256_UpdateHashFast(uVar6,param_2 + uVar9);
          uVar6 = extraout_ECX;
        }
      }
    }
    uVar5 = 0;
  }
  return uVar5;
}



//===== _EscSha256_Finish @ 6ed01a07 size=247 =====

undefined4 __thiscall _EscSha256_Finish(void *this,int param_1,int param_2)

{
  byte bVar1;
  uint uVar2;
  char cVar3;
  undefined4 in_EAX;
  int iVar4;
  undefined4 uVar5;
  void *extraout_ECX;
  
  if ((param_2 == 0) || (param_1 == 0)) {
    uVar5 = CONCAT31((int3)((uint)in_EAX >> 8),1);
  }
  else {
    cVar3 = *(byte *)(param_1 + 0x60) + 1;
    *(undefined1 *)(param_1 + 0x20 + (uint)*(byte *)(param_1 + 0x60)) = 0x80;
    *(char *)(param_1 + 0x60) = cVar3;
    if (cVar3 == '@') {
      _EscSha256_UpdateHashFast(this,param_1 + 0x20);
      *(undefined1 *)(param_1 + 0x60) = 0;
      this = extraout_ECX;
    }
    if (0x38 < *(byte *)(param_1 + 0x60)) {
      while( true ) {
        bVar1 = *(byte *)(param_1 + 0x60);
        if (0x3f < bVar1) break;
        *(undefined1 *)(param_1 + 0x20 + (uint)bVar1) = 0;
        *(byte *)(param_1 + 0x60) = bVar1 + 1;
      }
      _EscSha256_UpdateHashFast(this,param_1 + 0x20);
      *(undefined1 *)(param_1 + 0x60) = 0;
    }
    while( true ) {
      bVar1 = *(byte *)(param_1 + 0x60);
      if (0x37 < bVar1) break;
      *(undefined1 *)(param_1 + 0x20 + (uint)bVar1) = 0;
      *(byte *)(param_1 + 0x60) = bVar1 + 1;
    }
    uVar2 = *(uint *)(param_1 + 0x61);
    *(byte *)(param_1 + 0x60) = bVar1 + 8;
    *(undefined1 *)(param_1 + 0x5a) = 0;
    *(undefined1 *)(param_1 + 0x59) = 0;
    *(char *)(param_1 + 0x5f) = (char)uVar2 * '\b';
    *(undefined1 *)(param_1 + 0x58) = 0;
    *(char *)(param_1 + 0x5e) = (char)(uVar2 >> 5);
    *(char *)(param_1 + 0x5d) = (char)(uVar2 >> 0xd);
    *(char *)(param_1 + 0x5c) = (char)(uVar2 >> 0x15);
    *(byte *)(param_1 + 0x5b) = (byte)(uVar2 >> 0x1d);
    _EscSha256_UpdateHashFast(uVar2 >> 0x15,param_1 + 0x20);
    *(undefined1 *)(param_1 + 0x60) = 0;
    iVar4 = 0;
    do {
      uVar5 = *(undefined4 *)(param_1 + iVar4);
      *(char *)(param_2 + 3 + iVar4) = (char)uVar5;
      *(char *)(param_2 + 2 + iVar4) = (char)((uint)uVar5 >> 8);
      *(char *)(param_2 + 1 + iVar4) = (char)((uint)uVar5 >> 0x10);
      *(char *)(param_2 + iVar4) = (char)((uint)uVar5 >> 0x18);
      iVar4 = iVar4 + 4;
    } while (iVar4 != 0x20);
    uVar5 = 0;
  }
  return uVar5;
}



//===== _EscSha256_Calc @ 6ed01afe size=94 =====

undefined4 __cdecl _EscSha256_Calc(int param_1,uint param_2,int param_3)

{
  undefined4 in_EAX;
  undefined4 uVar1;
  void *this;
  undefined1 local_71 [101];
  
  if ((param_3 == 0) || (param_1 == 0)) {
    uVar1 = CONCAT31((int3)((uint)in_EAX >> 8),1);
  }
  else {
    uVar1 = _EscSha256_Init((int)local_71);
    if ((char)uVar1 == '\0') {
      uVar1 = _EscSha256_Update((int)local_71,param_1,param_2);
      if ((char)uVar1 == '\0') {
        uVar1 = _EscSha256_Finish(this,(int)local_71,param_3);
      }
    }
  }
  return uVar1;
}



//===== calcMAC @ 6ed0156b size=238 =====

/* calcMAC */

undefined4 __cdecl calcMAC(int param_1,int param_2,int param_3)

{
  undefined4 uVar1;
  int iVar2;
  undefined1 *puVar3;
  uint local_c8 [44];
  void *local_18;
  undefined1 *local_14;
  int local_10;
  
  local_14 = (undefined1 *)malloc(0x10);
  local_18 = (void *)malloc(0x10);
  puVar3 = local_14;
  for (iVar2 = 0x10; iVar2 != 0; iVar2 = iVar2 + -1) {
    *puVar3 = 0xff;
    puVar3 = puVar3 + 1;
  }
  for (local_10 = 0; local_10 < 5; local_10 = local_10 + 1) {
    local_14[local_10 + 0xb] = *(undefined1 *)(local_10 + param_2);
  }
  uVar1 = _EscAesEcb_Init((void *)0x0,local_c8,param_1);
  if ((char)uVar1 == '\0') {
    uVar1 = _EscAesEcb_Encrypt((int)local_c8,local_14,(int)local_18);
    if ((char)uVar1 == '\0') {
      for (local_10 = 0; local_10 < 5; local_10 = local_10 + 1) {
        *(undefined1 *)(local_10 + param_3) = *(undefined1 *)(local_10 + (int)local_18);
      }
      free(local_18);
      free(local_14);
      uVar1 = 0;
    }
    else {
      uVar1 = 1;
    }
  }
  else {
    uVar1 = 1;
  }
  return uVar1;
}



//===== calc_hash_chain @ 6ed01659 size=130 =====

/* calc_hash_chain */

undefined4 __cdecl calc_hash_chain(int param_1,undefined4 *param_2,undefined4 *param_3)

{
  int iVar1;
  undefined4 *puVar2;
  undefined1 local_a8 [104];
  undefined4 local_40 [8];
  int local_20;
  
  _EscSha256_Init((int)local_a8);
  puVar2 = local_40;
  for (iVar1 = 8; iVar1 != 0; iVar1 = iVar1 + -1) {
    *puVar2 = *param_2;
    param_2 = param_2 + 1;
    puVar2 = puVar2 + 1;
  }
  for (local_20 = 0; local_20 < param_1; local_20 = local_20 + 1) {
    _EscSha256_Calc((int)local_40,0x20,(int)local_40);
  }
  puVar2 = local_40;
  for (iVar1 = 8; iVar1 != 0; iVar1 = iVar1 + -1) {
    *param_3 = *puVar2;
    puVar2 = puVar2 + 1;
    param_3 = param_3 + 1;
  }
  return 0;
}



//===== parsePassword @ 6ed012dd size=482 =====

/* parsePassword */

undefined4 __cdecl parsePassword(undefined2 *param_1,undefined4 *param_2,int param_3,int param_4)

{
  byte bVar1;
  bool bVar2;
  undefined4 uVar3;
  undefined3 extraout_var;
  int iVar4;
  undefined4 *puVar5;
  byte *pbVar6;
  char *pcVar7;
  undefined4 local_bc [9];
  byte local_98 [34];
  undefined2 uStack_76;
  undefined4 local_74;
  undefined4 local_70;
  int local_6c [2];
  undefined2 local_64;
  undefined1 local_62;
  char local_61 [65];
  int local_20;
  
  puVar5 = (undefined4 *)(param_1 + 1);
  pcVar7 = local_61;
  for (iVar4 = 0xf; iVar4 != 0; iVar4 = iVar4 + -1) {
    *(undefined4 *)pcVar7 = *puVar5;
    puVar5 = puVar5 + 1;
    pcVar7 = pcVar7 + 4;
  }
  local_64 = *param_1;
  local_62 = 0;
  local_20 = strtol((char *)&local_64,(char **)0x0,10);
  if ((local_20 == 3) || (local_20 == 1)) {
    base64_init_decodestate(local_6c);
    base64_decode_block(local_61,0x3c,local_98,local_6c);
    pbVar6 = local_98;
    puVar5 = param_2;
    for (iVar4 = 8; iVar4 != 0; iVar4 = iVar4 + -1) {
      *puVar5 = *(undefined4 *)pbVar6;
      pbVar6 = pbVar6 + 4;
      puVar5 = puVar5 + 1;
    }
    *(short *)(param_2 + 8) = (short)stack0xffffff88;
    *(undefined2 *)((int)param_2 + 0x22) = uStack_76;
    param_2[9] = local_74;
    param_2[10] = local_70;
    pbVar6 = local_98;
    puVar5 = local_bc;
    for (iVar4 = 9; iVar4 != 0; iVar4 = iVar4 + -1) {
      *puVar5 = *(undefined4 *)pbVar6;
      pbVar6 = pbVar6 + 4;
      puVar5 = puVar5 + 1;
    }
    bVar2 = verifyPassword((int)local_bc,param_2 + 9);
    if (CONCAT31(extraout_var,bVar2) == 0) {
      bVar1 = *(byte *)(param_3 + 4);
      param_2[0xb] = (uint)CONCAT11(*(undefined1 *)(param_2 + 8),
                                    *(undefined1 *)((int)param_2 + 0x21));
      param_2[0xc] = (uint)CONCAT11(*(undefined1 *)((int)param_2 + 0x22),
                                    *(undefined1 *)((int)param_2 + 0x23));
      param_2[0xd] = (-param_2[0xb] - (uint)bVar1) + 0xff;
      if (param_4 == param_2[0xc]) {
        if (0xff - bVar1 < (uint)param_2[0xb]) {
          uVar3 = 2;
        }
        else {
          uVar3 = 0;
        }
      }
      else {
        uVar3 = 3;
      }
    }
    else {
      uVar3 = 1;
    }
  }
  else {
    uVar3 = 5;
  }
  return uVar3;
}



