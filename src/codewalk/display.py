"""Helpers for walkthrough authors.

`image(array_or_bytes)` wraps an image for the objects pane. It is importable as
`codewalk.image` and available as `cw.image` inside `show=` expressions.
"""

from __future__ import annotations

import struct
import sys
import zlib
from typing import Any, Optional

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class ImageDisplay:
    """An image to display: raw encoded bytes, or an HxW / HxWx3 / HxWx4 (or CxHxW) array."""

    def __init__(self, data: Any, *, mime: Optional[str] = None) -> None:
        self.data = data
        self.mime = mime

    @property
    def type(self) -> str:
        return "image"

    def encoded(self) -> tuple[bytes, str]:
        if isinstance(self.data, (bytes, bytearray, memoryview)):
            raw = bytes(self.data)
            return raw, self.mime or sniff_mime(raw)
        return encode_png(self.data), "image/png"

    def __repr__(self) -> str:
        return f"ImageDisplay({type(self.data).__name__})"


def image(data: Any, *, mime: Optional[str] = None) -> ImageDisplay:
    """Wrap raw image bytes or a pixel array for display. Arrays become PNG without needing PIL."""
    return ImageDisplay(data, mime=mime)


def sniff_mime(data: bytes) -> str:
    head = data[:512]
    if head.startswith(PNG_SIGNATURE):
        return "image/png"
    if head[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if b"<svg" in head:
        return "image/svg+xml"
    return "application/octet-stream"


def png_size(data: bytes) -> tuple[Optional[int], Optional[int]]:
    if data[:8] == PNG_SIGNATURE and len(data) >= 24:
        width, height = struct.unpack(">II", data[16:24])
        return int(width), int(height)
    return None, None


def _to_numpy(array: Any) -> Any:
    if hasattr(array, "detach") and hasattr(array, "cpu"):  # a torch tensor
        tensor = array.detach().cpu()
        if str(getattr(tensor, "dtype", "")) == "torch.bfloat16":
            tensor = tensor.float()
        return tensor.numpy()
    return array


def _to_uint8(a: Any, np: Any) -> Any:
    if a.dtype == np.bool_:
        return a.astype(np.uint8) * 255
    f = a.astype(np.float64)
    finite = np.isfinite(f)
    if not finite.any():
        return np.zeros(a.shape, dtype=np.uint8)
    lo, hi = float(f[finite].min()), float(f[finite].max())
    if np.issubdtype(a.dtype, np.integer):
        if not (0.0 <= lo and hi <= 255.0) and hi > lo:
            f = (f - lo) / (hi - lo) * 255.0
    elif 0.0 <= lo and hi <= 1.0:
        f = f * 255.0
    elif hi > lo:
        f = (f - lo) / (hi - lo) * 255.0
    elif not (0.0 <= lo <= 255.0):
        f = np.zeros_like(f)
    f = np.nan_to_num(f, nan=0.0, posinf=255.0, neginf=0.0)
    return np.clip(np.rint(f), 0, 255).astype(np.uint8)


def encode_png(array: Any) -> bytes:
    """Encode an HxW (gray), HxWx3 (RGB) or HxWx4 (RGBA) array as PNG. CxHxW is transposed."""
    try:
        import numpy as np
    except ImportError as e:  # pragma: no cover - numpy is a hard requirement for arrays
        raise TypeError("numpy is required to turn an array into an image") from e
    a = np.asarray(_to_numpy(array))
    if a.ndim == 3 and a.shape[0] in (1, 3, 4) and a.shape[2] not in (1, 3, 4):
        a = np.moveaxis(a, 0, -1)
    if a.ndim == 2:
        a = a[:, :, None]
    if a.ndim != 3 or a.shape[2] not in (1, 3, 4):
        raise ValueError(f"expected an HxW, HxWx3 or HxWx4 image array, got shape {tuple(a.shape)}")
    if a.dtype != np.uint8:
        a = _to_uint8(a, np)
    a = np.ascontiguousarray(a)
    height, width, channels = a.shape
    color_type = {1: 0, 3: 2, 4: 6}[channels]
    rows = b"".join(b"\x00" + a[y].tobytes() for y in range(height))

    def chunk(tag: bytes, body: bytes) -> bytes:
        return (
            struct.pack(">I", len(body))
            + tag
            + body
            + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)
    return PNG_SIGNATURE + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows, 6)) + chunk(b"IEND", b"")


__all__ = ["ImageDisplay", "image", "encode_png", "png_size", "sniff_mime", "PNG_SIGNATURE"]
