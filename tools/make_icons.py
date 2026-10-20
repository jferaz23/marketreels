"""Render the PNG app icons (iOS needs PNG, not SVG). Run once: python tools/make_icons.py"""
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "assets" / "icons"
GREEN, RED, WHITE = (43, 213, 118), (255, 84, 104), (255, 255, 255)


def draw(size: int, maskable: bool = False) -> Image.Image:
    s = size / 512
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bg = Image.new("RGBA", (size, size))
    px = bg.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * size)
            px[x, y] = (int(13 - 7 * t), int(26 - 17 * t), int(43 - 29 * t), 255)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=0 if maskable else int(112 * s), fill=255)
    img.paste(bg, (0, 0), mask)
    d = ImageDraw.Draw(img)
    k = 0.78 if maskable else 1.0  # keep artwork inside the maskable safe zone
    o = 256 * (1 - k)

    def P(x, y):
        return (o + x * k) * s, (o + y * k) * s

    def candle(cx, wick, body, color):
        d.line([P(cx, wick[0]), P(cx, wick[1])], fill=color, width=max(2, int(10 * s * k)))
        d.rounded_rectangle([*P(cx - 24, body[0]), *P(cx + 24, body[1])], radius=int(10 * s * k), fill=color)

    candle(146, (196, 356), (226, 322), RED)
    candle(232, (170, 330), (200, 300), GREEN)
    candle(318, (120, 282), (146, 250), GREEN)
    pts = []
    for i in range(41):  # cubic bezier for the trend line
        t = i / 40
        x = (1 - t) ** 3 * 110 + 3 * (1 - t) ** 2 * t * 190 + 3 * (1 - t) * t ** 2 * 260 + t ** 3 * 400
        y = (1 - t) ** 3 * 392 + 3 * (1 - t) ** 2 * t * 380 + 3 * (1 - t) * t ** 2 * 330 + t ** 3 * 150
        pts.append(P(x, y))
    w = max(3, int(16 * s * k))
    d.line(pts, fill=WHITE, width=w, joint="curve")
    d.line([P(352, 140), P(408, 134), P(402, 190)], fill=WHITE, width=w, joint="curve")
    return img


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    big = draw(1024)
    for name, px in [("icon-512.png", 512), ("icon-192.png", 192)]:
        big.resize((px, px), Image.LANCZOS).save(OUT / name)
    full = draw(1024, maskable=True)  # full-bleed: Android masks it, iOS rounds the corners itself
    full.resize((512, 512), Image.LANCZOS).save(OUT / "icon-maskable-512.png")
    full.resize((180, 180), Image.LANCZOS).convert("RGB").save(OUT / "apple-touch-icon.png")
    print("icons written to", OUT)
