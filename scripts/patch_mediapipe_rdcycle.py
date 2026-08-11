#!/usr/bin/env python3
"""Patch rdcycle illegal-instruction issues in the MediaPipe riscv64 wheel.

Background:
MES20 Linux 6.6 blocks user-space reads of the cycle CSR. Older Abseil
builds use rdcycle as a high-resolution timer on RISC-V, which can cause
mp.solutions.hands.Hands() to receive SIGILL during initialization.

This script searches the installed MediaPipe _framework_bindings*.so for:

    csrr <rd>, cycle

and replaces it with:

    csrr <rd>, time

This is a runtime patch for quick recovery after reflashing the board image.
For a permanent fix, rebuild the wheel with the patched Abseil bindings.
"""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import struct
from pathlib import Path


SO_NAME = "_framework_bindings.cpython-310-riscv64-linux-gnu.so"
BACKUP_SUFFIX = ".bak_rdcycle"


def find_mediapipe_binding() -> Path:
    spec = importlib.util.find_spec("mediapipe")
    if spec is None or spec.origin is None:
        raise RuntimeError("mediapipe is not installed; install the local riscv64 wheel first")
    so_path = Path(spec.origin).parent / "python" / SO_NAME
    if not so_path.exists():
        raise RuntimeError(f"MediaPipe native library not found: {so_path}")
    return so_path


def is_rdcycle(word: int) -> bool:
    # RISC-V: csrr rd, cycle
    # csr=0xc00, funct3=CSRRS, rs1=x0, opcode=SYSTEM; rd may vary.
    return (word & 0xFFF0707F) == 0xC0002073


def replace_with_rdtime(word: int) -> int:
    rd = (word >> 7) & 0x1F
    return (0xC01 << 20) | (2 << 12) | (rd << 7) | 0x73


def patch_so(so_path: Path, dry_run: bool = False) -> int:
    data = bytearray(so_path.read_bytes())
    patched = 0

    # RISC-V instructions are 4 bytes, but code sections in the .so are not
    # always 4-byte aligned. Scan with a 2-byte step to handle mixed layouts.
    for offset in range(0, len(data) - 3, 2):
        word = struct.unpack_from("<I", data, offset)[0]
        if not is_rdcycle(word):
            continue
        new_word = replace_with_rdtime(word)
        rd = (word >> 7) & 0x1F
        print(f"found rdcycle: offset=0x{offset:x}, rd=x{rd}, 0x{word:08x} -> 0x{new_word:08x}")
        if not dry_run:
            struct.pack_into("<I", data, offset, new_word)
        patched += 1

    if patched and not dry_run:
        backup = so_path.with_suffix(so_path.suffix + BACKUP_SUFFIX)
        if not backup.exists():
            shutil.copy2(so_path, backup)
            print(f"backed up original library: {backup}")
        so_path.write_bytes(data)
        print(f"wrote patched library: {so_path}")
    return patched


def restore_so(so_path: Path) -> None:
    backup = so_path.with_suffix(so_path.suffix + BACKUP_SUFFIX)
    if not backup.exists():
        raise RuntimeError(f"backup not found: {backup}")
    shutil.copy2(backup, so_path)
    print(f"restored original library: {so_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Patch MediaPipe riscv64 rdcycle SIGILL issues")
    parser.add_argument("--apply", action="store_true", help="apply the patch")
    parser.add_argument("--check", action="store_true", help="only check for remaining rdcycle instructions")
    parser.add_argument("--restore", action="store_true", help="restore from .bak_rdcycle backup")
    args = parser.parse_args()

    so_path = find_mediapipe_binding()
    print(f"MediaPipe native library: {so_path}")

    if args.restore:
        restore_so(so_path)
        return 0

    dry_run = not args.apply
    patched = patch_so(so_path, dry_run=dry_run)
    if patched == 0:
        print("no rdcycle instructions found; patch is not required or already applied")
        return 0

    if dry_run:
        print(f"found {patched} rdcycle instruction(s). Apply the patch with:")
        print("python3 scripts/patch_mediapipe_rdcycle.py --apply")
        return 1 if args.check else 0

    print(f"patch complete; replaced {patched} rdcycle instruction(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
