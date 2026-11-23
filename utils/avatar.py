"""
utils/avatar.py

Profile pictures are stored in the database as base64 text and are embedded in the
sidebar of EVERY page on EVERY rerun. A photo straight from a phone is several MB, which
makes every page slow and bloats the database (and every cloud backup). So pictures are
shrunk to a small square (192 px) when they are saved, and an older big picture is shrunk
once, automatically, the next time it is loaded.
"""

import base64
import io

AVATAR_SIDE = 192            # px; shown at 38-80 px, so this is sharp even on retina screens
SHRINK_ABOVE_CHARS = 60_000  # a stored picture whose base64 text is longer than this gets re-shrunk


def shrink_avatar_bytes(raw: bytes) -> str:
    """Raw image bytes -> base64 text of a small centred square (JPEG, or PNG if it has transparency)."""
    from PIL import Image, ImageOps

    image = ImageOps.exif_transpose(Image.open(io.BytesIO(raw)))
    has_alpha = image.mode in ("RGBA", "LA") or "transparency" in image.info
    image = image.convert("RGBA" if has_alpha else "RGB")
    image = ImageOps.fit(image, (AVATAR_SIDE, AVATAR_SIDE), method=Image.LANCZOS)

    out = io.BytesIO()
    if has_alpha:
        image.save(out, "PNG", optimize=True)
    else:
        image.save(out, "JPEG", quality=88, optimize=True)
    return base64.b64encode(out.getvalue()).decode("ascii")


def shrink_avatar_b64(avatar_base64: str) -> str:
    """Return the picture unchanged if it is already small (or can't be read), else a shrunk copy."""
    if not avatar_base64 or len(avatar_base64) <= SHRINK_ABOVE_CHARS:
        return avatar_base64
    try:
        return shrink_avatar_bytes(base64.b64decode(avatar_base64))
    except Exception:
        return avatar_base64


def mime_for(avatar_base64: str) -> str:
    """image/jpeg for JPEG data (base64 starts with /9j/), otherwise image/png."""
    return "image/jpeg" if (avatar_base64 or "").startswith("/9j/") else "image/png"
