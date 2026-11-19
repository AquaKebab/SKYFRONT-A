"""Лёгкие процедурные текстуры, создаваемые локально без внешних файлов."""
import math
from panda3d.core import PNMImage, Texture

_TEXTURES = {}


def get_surface_texture(kind="metal"):
    if kind in _TEXTURES:
        return _TEXTURES[kind]

    size = 64
    image = PNMImage(size, size, 4)
    for y in range(size):
        for x in range(size):
            noise = ((x * 17 + y * 31 + (x * y) % 23) % 13) / 13.0
            if kind == "concrete":
                base = 0.82 + noise * 0.10
                if x % 16 in (0, 1) or y % 16 in (0, 1):
                    base *= 0.78
                rgb = (base * 0.95, base, base * 1.04)
            elif kind == "camo":
                band = ((x // 8) + (y // 11) * 2) % 4
                palette = ((0.78, 0.82, 0.74), (0.88, 0.90, 0.80),
                           (0.70, 0.78, 0.74), (0.92, 0.88, 0.78))
                b = palette[band]
                factor = 0.94 + noise * 0.12
                rgb = (b[0] * factor, b[1] * factor, b[2] * factor)
            elif kind == "sand":
                base = 0.86 + noise * 0.10
                rgb = (base, base * 0.88, base * 0.68)
            elif kind == "snow":
                base = 0.92 + noise * 0.07
                rgb = (base * 0.94, base * 0.98, base)
            elif kind == "asphalt":
                base = 0.76 + noise * 0.08
                rgb = (base * 0.95, base, base * 1.04)
            elif kind == "grass":
                base = 0.78 + noise * 0.10
                rgb = (base * 0.70, base, base * 0.66)
            else:
                base = 0.82 + noise * 0.10
                if x % 16 in (0, 1) or y % 16 in (0, 1):
                    base *= 0.68
                if (x % 16 in (2, 13)) and (y % 16 in (2, 13)):
                    base = min(0.95, base + 0.22)
                brushed = 0.96 + 0.04 * math.sin(y * 0.9)
                rgb = (base * brushed, base * 1.02 * brushed,
                       base * 1.08 * brushed)
            image.setXelA(x, y, rgb[0], rgb[1], rgb[2], 1.0)

    texture = Texture("skyfront-" + kind)
    texture.load(image)
    texture.setWrapU(Texture.WM_repeat)
    texture.setWrapV(Texture.WM_repeat)
    texture.setMinfilter(Texture.FT_linear)
    texture.setMagfilter(Texture.FT_linear)
    _TEXTURES[kind] = texture
    return texture
