#!/usr/bin/env python3
"""Build the approved Blender room tour for free GitHub Pages.

No geometry/material/camera modifications; only binary GLB concatenation.
No external Python packages needed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "dist"
PARTS = [ROOT / f"cabinet_room.part{index:02d}.bin" for index in range(1, 6)]
FILES = [ROOT / "index.html", ROOT / "cabinet_photo.png", ROOT / "forest_background.png"]
# Add the Preppy viewer without modifying the previously validated room model.
EXTRA_FILES = [ROOT / "table-02.html", ROOT / "table-02.glb"]
EXPECTED_SIZE = 10_104_552
EXPECTED_SHA256 = "1ba8304d90217b3c97f021cda9a4d7b2ce4e69716408549033ffde3685185648"


def validate_glb(data: bytes) -> tuple[int, int]:
    if len(data) != EXPECTED_SIZE:
        raise ValueError(f"Unexpected GLB size: {len(data)} != {EXPECTED_SIZE}")
    if hashlib.sha256(data).hexdigest() != EXPECTED_SHA256:
        raise ValueError("The model differs from the validated GLB (SHA-256 mismatch)")
    if data[:4] != b"glTF":
        raise ValueError("The file is not a GLB 2.0")
    version, declared_length = struct.unpack_from("<II", data, 4)
    if version != 2 or declared_length != len(data):
        raise ValueError("GLB version or length mismatch")
    chunk_length, chunk_type = struct.unpack_from("<I4s", data, 12)
    if chunk_type != b"JSON" or 20 + chunk_length > len(data):
        raise ValueError("Invalid GLB JSON chunk")
    gltf = json.loads(data[20:20 + chunk_length])
    if gltf.get("asset", {}).get("version") != "2.0":
        raise ValueError("Unexpected glTF version")
    return len(gltf.get("nodes", [])), len(gltf.get("meshes", []))


def build() -> None:
    for path in [*FILES, *EXTRA_FILES, *PARTS]:
        if not path.is_file():
            raise FileNotFoundError(f"Missing source: {path.name}")
        if path.stat().st_size == 0:
            raise ValueError(f"Empty source: {path.name}")
    html = FILES[0].read_text(encoding="utf-8")
    if "roomParts" not in html or "GLTFLoader" not in html:
        raise ValueError("HTML is not the existing room-tour viewer")
    for png in FILES[1:]:
        with png.open("rb") as file:
            if file.read(8) != bytes.fromhex("89504e470d0a1a0a"):
                raise ValueError(f"Invalid PNG: {png.name}")
    model = b"".join(part.read_bytes() for part in PARTS)
    nodes, meshes = validate_glb(model)
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for path in [*FILES, *EXTRA_FILES, *PARTS]:
        shutil.copyfile(path, OUT / path.name)
    (OUT / "cabinet_room.glb").write_bytes(model)
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Verified room GLB: {len(model):,} bytes, {nodes} nodes, {meshes} meshes")
    print(f"SHA256: {EXPECTED_SHA256}")
    print(f"GitHub Pages output: {OUT} ({len(list(OUT.iterdir()))} files)")


if __name__ == "__main__":
    try:
        build()
    except Exception as exc:
        print(f"BUILD FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
