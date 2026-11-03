"""
LUT Converter - core logic (no user interface code here).

Reads .cube LUT files and turns them into PNG LUT textures for game engines,
or applies them to images for previewing.
"""

import math
import os

import numpy as np
from PIL import Image

MAX_1D_SIZE = 65536
MAX_3D_SIZE = 256


class LUTError(Exception):
    """A problem with a .cube file, worded for the person using the app."""


class LUT:
    def __init__(self, kind, size, data, title=None, domain_min=(0, 0, 0), domain_max=(1, 1, 1), path=None):
        self.kind = kind                      # "1D" or "3D"
        self.size = size
        self.data = data                      # 1D: (N, 3)   3D: (N, N, N, 3) indexed [b, g, r]
        self.title = title
        self.domain_min = np.asarray(domain_min, dtype=np.float32)
        self.domain_max = np.asarray(domain_max, dtype=np.float32)
        self.path = path

    @property
    def name(self):
        return os.path.splitext(os.path.basename(self.path))[0] if self.path else (self.title or "LUT")

    @property
    def description(self):
        return f"1D · {self.size} entries" if self.kind == "1D" else f"3D · {self.size}³"

    # -- applying ---------------------------------------------------------
    def apply(self, rgb):
        """rgb: float array (..., 3) in 0..1 -> float array (..., 3) in 0..1."""
        rgb = np.asarray(rgb, dtype=np.float32)
        span = np.where(self.domain_max - self.domain_min == 0, 1, self.domain_max - self.domain_min)
        x = np.clip((rgb - self.domain_min) / span, 0, 1)
        out = _apply_1d(self.data, x) if self.kind == "1D" else _apply_3d(self.data, x)
        return np.clip(out, 0, 1)


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------

def parse_cube(path):
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            text = f.read()
    except OSError as e:
        raise LUTError(f"The file could not be opened ({e.strerror or e}).")
    return parse_cube_text(text, path)


def parse_cube_text(text, path=None):
    kind = size = title = None
    dmin, dmax = [0.0, 0.0, 0.0], [1.0, 1.0, 1.0]
    rows = []

    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        key = parts[0].upper()

        if key == "TITLE":
            title = line[5:].strip().strip('"') or None
        elif key in ("LUT_1D_SIZE", "LUT_3D_SIZE"):
            if kind:
                raise LUTError("This file declares more than one LUT size. Files containing both a 1D and 3D LUT aren't supported.")
            kind = "1D" if key == "LUT_1D_SIZE" else "3D"
            try:
                size = int(parts[1])
            except (IndexError, ValueError):
                raise LUTError(f"Line {lineno}: the LUT size is missing or not a number.")
        elif key in ("DOMAIN_MIN", "DOMAIN_MAX"):
            vals = _floats(parts[1:4], lineno)
            if key == "DOMAIN_MIN":
                dmin = vals
            else:
                dmax = vals
        elif key in ("LUT_1D_INPUT_RANGE", "LUT_3D_INPUT_RANGE"):
            lo, hi = _floats(parts[1:3], lineno, count=2)
            dmin, dmax = [lo] * 3, [hi] * 3
        elif key[0].isdigit() or key[0] in "-+.":
            rows.append(_floats(parts[:3], lineno))
        # Any other keyword (vendor extensions) is ignored.

    if not kind:
        raise LUTError("This doesn't look like a .cube LUT: no LUT_1D_SIZE or LUT_3D_SIZE line was found.")
    limit = MAX_1D_SIZE if kind == "1D" else MAX_3D_SIZE
    if size < 2 or size > limit:
        raise LUTError(f"Unsupported LUT size ({size}). {kind} LUTs must be between 2 and {limit}.")

    expected = size if kind == "1D" else size ** 3
    if len(rows) < expected:
        raise LUTError(f"The file is incomplete: it should have {expected:,} color rows but only has {len(rows):,}.")
    if len(rows) > expected:
        raise LUTError(f"The file has {len(rows):,} color rows but its size says {expected:,}. It may be damaged.")

    data = np.asarray(rows, dtype=np.float32)
    if not np.all(np.isfinite(data)):
        raise LUTError("The file contains invalid numbers (NaN or infinity).")
    if any(hi <= lo for lo, hi in zip(dmin, dmax)):
        raise LUTError("The file's DOMAIN_MIN must be smaller than its DOMAIN_MAX.")

    if kind == "3D":
        data = data.reshape(size, size, size, 3)   # red changes fastest in .cube files
    return LUT(kind, size, data, title, dmin, dmax, path)


def _floats(parts, lineno, count=3):
    if len(parts) < count:
        raise LUTError(f"Line {lineno}: expected {count} numbers.")
    try:
        return [float(p) for p in parts[:count]]
    except ValueError:
        raise LUTError(f"Line {lineno}: '{' '.join(parts)}' isn't a valid set of numbers.")


# --------------------------------------------------------------------------
# Interpolation
# --------------------------------------------------------------------------

def _apply_1d(d, x):
    n = d.shape[0]
    out = np.empty_like(x)
    for c in range(3):
        idx = x[..., c] * (n - 1)
        lo = np.floor(idx).astype(np.int32)
        hi = np.minimum(lo + 1, n - 1)
        f = idx - lo
        out[..., c] = d[lo, c] * (1 - f) + d[hi, c] * f
    return out


def _apply_3d(d, x):
    n = d.shape[0]

    def split(v):
        p = v * (n - 1)
        p0 = np.minimum(np.floor(p).astype(np.int32), n - 2) if n > 1 else np.zeros_like(p, np.int32)
        return p0, p0 + 1, (p - p0)[..., None]

    r0, r1, fr = split(x[..., 0])
    g0, g1, fg = split(x[..., 1])
    b0, b1, fb = split(x[..., 2])

    c00 = d[b0, g0, r0] * (1 - fr) + d[b0, g0, r1] * fr
    c10 = d[b0, g1, r0] * (1 - fr) + d[b0, g1, r1] * fr
    c01 = d[b1, g0, r0] * (1 - fr) + d[b1, g0, r1] * fr
    c11 = d[b1, g1, r0] * (1 - fr) + d[b1, g1, r1] * fr
    c0 = c00 * (1 - fg) + c10 * fg
    c1 = c01 * (1 - fg) + c11 * fg
    return c0 * (1 - fb) + c1 * fb


# --------------------------------------------------------------------------
# Output layouts
# --------------------------------------------------------------------------

class Target:
    def __init__(self, key, label, slices, flip, suffix, hint):
        self.key, self.label, self.slices, self.flip, self.suffix, self.hint = key, label, slices, flip, suffix, hint

    @property
    def is_strip(self):
        return self.slices == 0


TARGETS = [
    Target("ue", "Unreal Engine", 16, False, "_UE",
           "<b>In Unreal:</b> set Mip Gen Settings to <i>NoMipmaps</i> and Texture Group to "
           "<i>ColorLookupTable</i>, then use it as the Color Grading LUT in a Post Process Volume."),
    Target("unity", "Unity", 32, True, "_Unity",
           "<b>In Unity:</b> turn off mipmaps, set Wrap Mode to <i>Clamp</i> and Compression to "
           "<i>None</i>, then use it in a Color Lookup override."),
    Target("g16", "Generic · 16", 16, False, "_LUT16", "16 slices of 16 × 16, laid side by side."),
    Target("g32", "Generic · 32", 32, False, "_LUT32", "32 slices of 32 × 32, laid side by side."),
    Target("g64", "Generic · 64", 64, False, "_LUT64", "64 slices of 64 × 64, laid side by side. Highest quality, larger file."),
    Target("strip", "Gradient strip", 0, False, "_strip",
           "A horizontal black-to-white ramp run through the LUT. Handy for 1D LUTs and color ramps."),
]
TARGETS_BY_KEY = {t.key: t for t in TARGETS}


def neutral_grid(target, strip_w=512, strip_h=32):
    """The untouched input colors for a layout, as floats (H, W, 3)."""
    if target.is_strip:
        t = np.linspace(0, 1, max(2, strip_w), dtype=np.float32)
        row = np.stack([t, t, t], axis=-1)
        return np.repeat(row[None], max(1, strip_h), axis=0)
    m = target.slices
    X, Y = np.meshgrid(np.arange(m * m), np.arange(m))
    r = (X % m) / (m - 1)
    g = Y / (m - 1)
    b = (X // m) / (m - 1)
    if target.flip:
        g = 1 - g
    return np.stack([r, g, b], axis=-1).astype(np.float32)


def blend(neutral, graded, strength):
    """Mix between the original (0) and the full LUT result (1)."""
    if strength >= 1:
        return graded
    return neutral + (graded - neutral) * strength


def to_uint8(rgb):
    return (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)


def render_texture(lut, target, strength=1.0, strip_w=512, strip_h=32):
    grid = neutral_grid(target, strip_w, strip_h)
    rgb = grid if lut is None else blend(grid, lut.apply(grid), strength)
    return Image.fromarray(to_uint8(rgb), "RGB")


def output_name(lut, target, strength=1.0):
    name = lut.name if lut else "Neutral"
    pct = "" if strength >= 1 else f"_{int(round(strength * 100))}pct"
    return f"{name}{target.suffix}{pct}.png"


# --------------------------------------------------------------------------
# Built-in preview image
# --------------------------------------------------------------------------

def sample_image(w=960, h=600):
    """A color test chart: hue sweep, skin / foliage / sky swatches and a gray ramp."""
    img = np.zeros((h, w, 3), np.float32)

    # Hue sweep with saturation fading towards the bottom
    top = int(h * 0.55)
    hue = np.linspace(0, 1, w, endpoint=False)
    sat = np.linspace(1, 0.15, top)[:, None]
    val = np.linspace(0.95, 0.6, top)[:, None]
    H, S, V = np.broadcast_arrays(hue[None, :], sat, val)
    img[:top] = _hsv_to_rgb(H, S, V)

    # Swatches: skin tones, foliage, sky, neutrals
    sw_y0, sw_y1 = top, int(h * 0.82)
    swatches = ["#3b2219", "#6b4632", "#a8745a", "#d7a688", "#f1cdb3",
                "#2f4a1e", "#5f7f3a", "#3d6e9e", "#8db7dc", "#c43b2f", "#e3b23c", "#4a3a6b"]
    n = len(swatches)
    for i, hx in enumerate(swatches):
        x0, x1 = i * w // n, (i + 1) * w // n
        img[sw_y0:sw_y1, x0:x1] = [int(hx[k:k + 2], 16) / 255 for k in (1, 3, 5)]

    # Gray ramp
    img[sw_y1:] = np.linspace(0, 1, w)[None, :, None]
    return img


def _hsv_to_rgb(h, s, v):
    i = np.floor(h * 6).astype(int) % 6
    f = h * 6 - np.floor(h * 6)
    p, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    choices = [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)]
    out = np.zeros(h.shape + (3,), np.float32)
    for k, (r, g, b) in enumerate(choices):
        m = i == k
        out[m, 0], out[m, 1], out[m, 2] = r[m], g[m], b[m]
    return out


def load_image(path, max_side=1600):
    """Open any image as float RGB, scaled down for fast previewing."""
    with Image.open(path) as im:
        im = im.convert("RGB")
        scale = max_side / max(im.size)
        if scale < 1:
            im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS)
        return np.asarray(im, dtype=np.float32) / 255
