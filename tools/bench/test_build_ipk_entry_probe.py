"""Regression tests for build_ipk_entry_probe.py against REAL Y175 bench-dump images (the archived ELK source it is SHA-pinned to is gone, so SOURCE_SHA256 is monkeypatched per-test to each carved fixture's own sha256 to reach the structural path)."""
import hashlib
import importlib.util
import os
import struct
from pathlib import Path

import pytest

TOOL = Path(__file__).with_name("build_ipk_entry_probe.py")

BENCH_DIR = Path(os.environ.get(
    "GMINFO_BENCH_DIR",
    os.path.join(os.environ["GM_RESEARCH_ROOT"], "aaos/gm_aaos/2024_Silverado_ICE/emmc_dump/Y175_bench")))

ELK = dict(
    file="ifwi_mapped_ff800000_8MiB.bin", offset=0x501040,
    sha256="3100e21d8d420422af8d4022adb33725cda1a485dad63412abb58554f60a3dce",
    length=1130124)
GHS_A = dict(
    file="emmc_user_wifi.bin", offset=0x100000,
    sha256="7b02d1b77d04df0486c33ccea2ee561fc019e44c8072beee3090d5f113ed39db",
    length=14928792)

pytestmark = pytest.mark.skipif(
    not BENCH_DIR.is_dir(), reason=f"bench dir absent: {BENCH_DIR}")


def load_tool():
    """Fresh module instance per call so SOURCE_SHA256 patches don't leak between tests."""
    spec = importlib.util.spec_from_file_location("build_ipk_entry_probe_ut", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def carve(spec):
    """Carve the ipk. container at (file, offset); SKIP if file missing or sha mismatch."""
    path = BENCH_DIR / spec["file"]
    if not path.exists():
        pytest.skip(f"fixture file absent: {path}")
    with path.open("rb") as fh:
        fh.seek(spec["offset"])
        head = fh.read(0x60)
        payload_len, header_len = struct.unpack_from("<II", head, 12)
        total = header_len + payload_len + 4
        fh.seek(spec["offset"])
        data = fh.read(total)
    if data[:4] != b"ipk.":
        pytest.skip(f"no ipk. magic at {spec['file']}+{spec['offset']:#x}")
    if hashlib.sha256(data).hexdigest() != spec["sha256"]:
        pytest.skip(f"carved {spec['file']} sha mismatch (external, build-specific image)")
    assert len(data) == spec["length"]
    return data


@pytest.fixture
def elk():
    return carve(ELK)


@pytest.fixture
def ghs_a():
    return carve(GHS_A)


def test_check_ipk_parses_real_elk(elk):
    mod = load_tool()
    header_len, sizes, _end = mod.check_ipk(elk)
    assert header_len == 44
    assert len(sizes) == 4
    assert sizes[0] == 512


def test_check_ipk_parses_real_ghs_isys_a(ghs_a):
    mod = load_tool()
    header_len, sizes, _end = mod.check_ipk(ghs_a)
    assert header_len == 44
    assert sizes == (0x2e, 0xe3ca20, 0x14, 0x104)


def test_build_elk_produces_unsigned_marker_container(elk):
    mod = load_tool()
    mod.SOURCE_SHA256 = hashlib.sha256(elk).hexdigest()
    img, info = mod.build(elk)
    mod.check_ipk(img)  # raises if malformed
    assert img[5] == 0  # signed flag cleared
    start = info["elf_offset"] + info["marker_file"]
    assert img[start:start + 32] == bytes(32)
    assert info["entry"] < info["stub_addr"] < info["marker_addr"]


def test_build_rejects_ghs_isys_a_wrong_components(ghs_a):
    mod = load_tool()
    mod.SOURCE_SHA256 = hashlib.sha256(ghs_a).hexdigest()
    with pytest.raises(ValueError, match="Unexpected IPK components"):
        mod.build(ghs_a)


def test_emulate_elk_stub(elk):
    pytest.importorskip("unicorn")
    mod = load_tool()
    mod.SOURCE_SHA256 = hashlib.sha256(elk).hexdigest()
    img, info = mod.build(elk)
    mod.emulate(img, info)  # internally asserts marker executed + handoff preserved
