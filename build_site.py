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
import urllib.request

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "dist"
PARTS = [ROOT / f"cabinet_room.part{index:02d}.bin" for index in range(1, 6)]
FILES = [ROOT / "index.html", ROOT / "cabinet_photo.png", ROOT / "forest_background.png"]
# Add the Preppy viewer without modifying the previously validated room model.
RUG_PARTS = [ROOT / f"rug-matmi.part{index:02d}.bin" for index in range(1, 6)]
RUG_PHOTO = ROOT / "rug-sanderson-original.jpg"
RUG_SIZE = 7_033_840
RUG_SHA256 = "8e4b006a10f91da0251de0a5fe347513afea1341f2db967cab2b8a8c256ae538"
EXTRA_FILES = [ROOT / "table-02.html", ROOT / "table-02.glb", *RUG_PARTS, RUG_PHOTO, ROOT / "tkano-tea.html"]
TKANO_FILES = [ROOT / "assets" / "tkano-tea.glb", ROOT / "assets" / "tkano-original.webp"]
TKANO_SIZE = 1_536_044
TKANO_SHA256 = "5b823b003ab06e147528754963966d6ba76f5b072479665aec7e7bae72489ad4"
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
    for path in [*FILES, *EXTRA_FILES, *PARTS, *TKANO_FILES]:
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
    rug = b"".join(part.read_bytes() for part in RUG_PARTS)
    if len(rug) != RUG_SIZE or rug[:4] != b"glTF" or hashlib.sha256(rug).hexdigest() != RUG_SHA256:
        raise ValueError("Sanderson rug GLB invalid or checksum mismatch")
    if RUG_PHOTO.read_bytes()[:3] != bytes.fromhex("ffd8ff"):
        raise ValueError("Sanderson original photo invalid")
    tkano = TKANO_FILES[0].read_bytes()
    if len(tkano) != TKANO_SIZE or tkano[:4] != b"glTF" or hashlib.sha256(tkano).hexdigest() != TKANO_SHA256:
        raise ValueError("TKANO 160x230 original design 3D model invalid")
    tkano_photo = TKANO_FILES[1].read_bytes()
    if tkano_photo[:4] != b"RIFF" or tkano_photo[8:12] != b"WEBP":
        raise ValueError("TKANO official reference photo invalid")
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for path in [*FILES, *EXTRA_FILES, *PARTS, *TKANO_FILES]:
        dest = OUT / path.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    # Mirror the exact manufacturer images into the GitHub Pages build.  The
    # remote host disallows some mobile/browser hotlinks; local files avoid that.
    preppy_photos = [
        ("preppy-original-main.jpg", "https://imodern.ru/upload/resize_cache/iblock/cf4/1050_666_1/cf41218ec04bd696043ee112e96907b1.jpg", True),
        ("preppy-original-detail.jpg", "https://imodern.ru/upload/resize_cache/iblock/f5e/1050_666_1/f5e498ee3ef3b27b7c849f4ce66be3b8.jpg", False),
    ]
    for name, url, required in preppy_photos:
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; Cabinet3D/1.0)",
                "Referer": "https://imodern.ru/",
                "Accept": "image/avif,image/webp,image/jpeg,image/*;q=0.8",
            })
            with urllib.request.urlopen(req, timeout=25) as reply:
                data = reply.read(8_000_001)
            if len(data) > 8_000_000 or not data.startswith(bytes.fromhex("ffd8ff")):
                raise ValueError("Reference image is not a valid JPEG or exceeds 8 MB")
            (OUT / name).write_bytes(data)
            print(f"Saved Preppy reference {name}: {len(data)} bytes")
        except Exception as exc:
            if required:
                raise RuntimeError(f"Cannot bundle the original Preppy photo: {exc}") from exc
            print(f"Optional Preppy detail image not available: {exc}")

    (OUT / "cabinet_room.glb").write_bytes(model)
    # Assemble the separate photorealistic table HTML, without altering the room tour.
    import gzip
    table_parts = [ROOT / "table-v4" / f"part{i:02d}.gzchunk" for i in range(11)]
    for part in table_parts:
        if not part.is_file():
            raise FileNotFoundError(f"Missing table V4 transfer part: {part}")
    packed_table = b"".join(part.read_bytes() for part in table_parts)
    if len(packed_table) != 16613948 or hashlib.sha256(packed_table).hexdigest() != "d9a7c28bfb67f52938cdd26f2931200813e36fa337ed07bc5f60279746a5d903":
        raise ValueError("The table V4 transfer parts differ from the original")
    table_html = gzip.decompress(packed_table)
    if len(table_html) != 23698943 or hashlib.sha256(table_html).hexdigest() != "3e9d8f2ad6e521498e05df7ec7ba3dff2a952645c784546f6ae84ff55e2258b5":
        raise ValueError("The restored table V4 HTML does not match the browser-tested file")
    if b'modelBytes' not in table_html or b'<model-viewer' not in table_html:
        raise ValueError("The table V4 HTML lacks the embedded 3D model viewer")
    (OUT / "table-01-v4.html").write_bytes(table_html)
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Verified room GLB: {len(model):,} bytes, {nodes} nodes, {meshes} meshes")
    print(f"SHA256: {EXPECTED_SHA256}")
    print(f"Verified Sanderson rug GLB: {len(rug):,} bytes")
    print(f"Verified TKANO rug GLB: {len(tkano):,} bytes | SHA256: {TKANO_SHA256}")
    print(f"GitHub Pages output: {OUT} ({len(list(OUT.iterdir()))} files)")


if __name__ == "__main__":
    try:
        build()
    except Exception as exc:
        print(f"BUILD FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
