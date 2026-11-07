"""Draws the DeskTrace logo — a document on a gradient tile, with the trace of its versions across it
(three version dots, the newest one green) — as static/icon.ico, plus a grey static/icon-paused.ico that
the tray shows while monitoring is paused. Needs Pillow. Geometry is in a 32×32 grid, like static/logo.svg."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

S = 1024  # draw large, then downsample for smooth edges
U = S / 32
SIZES = [(16, 16), (20, 20), (24, 24), (32, 32), (40, 40), (48, 48), (64, 64), (128, 128), (256, 256)]
DOC = (8.6, 6.0, 23.4, 26.0)
FOLD = 5.3
TRACE = [(11.6, 21.4), (15.2, 16.4), (17.9, 19.0), (21.0, 13.6)]
LINES = [((11.2, 10.0), (16.2, 10.0)), ((11.2, 12.9), (14.6, 12.9))]

THEMES = {
    'icon.ico': dict(c1=(79, 70, 229), c2=(6, 182, 212), ink=(79, 70, 229), fold=(199, 210, 254), dot=(16, 185, 129)),
    'icon-paused.ico': dict(c1=(150, 156, 170), c2=(110, 117, 132), ink=(107, 114, 128), fold=(209, 213, 219), dot=(156, 163, 175)),
    # 2.6.0 #45: tray states
    'icon-busy.ico': dict(c1=(5, 150, 105), c2=(16, 185, 129), ink=(4, 120, 87), fold=(167, 243, 208), dot=(52, 211, 153)),
    'icon-alert.ico': dict(c1=(220, 38, 38), c2=(249, 115, 22), ink=(185, 28, 28), fold=(254, 202, 202), dot=(239, 68, 68)),
}


def lerp(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def u(*pts):
    return [(x * U, y * U) for x, y in pts]


def draw(c1, c2, ink, fold, dot):
    grad = Image.new('RGB', (S, S))
    px = grad.load()
    for y in range(S):
        for x in range(S):
            px[x, y] = lerp(c1, c2, (x * .55 + y * .45) / (S - 1))
    tile = Image.new('L', (S, S), 0)
    ImageDraw.Draw(tile).rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.24), fill=255)
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    img.paste(grad, (0, 0), tile)

    # a soft light from the top left
    glow = Image.new('L', (S, S), 0)
    ImageDraw.Draw(glow).ellipse([-S * .35, -S * .45, S * .75, S * .55], fill=70)
    glow = glow.filter(ImageFilter.GaussianBlur(S * .08))
    light = Image.new('RGBA', (S, S), (255, 255, 255, 0))
    light.putalpha(Image.composite(glow, Image.new('L', (S, S), 0), tile))
    img = Image.alpha_composite(img, light)

    # the document's shadow, then the document with a folded corner
    x0, y0, x1, y1 = DOC
    shadow = Image.new('L', (S, S), 0)
    ImageDraw.Draw(shadow).rounded_rectangle(u((x0, y0 + .9), (x1, y1 + .9)), radius=2.2 * U, fill=90)
    shadow = shadow.filter(ImageFilter.GaussianBlur(U * .9))
    img = Image.alpha_composite(img, Image.merge('RGBA', [Image.new('L', (S, S), 20)] * 3 + [shadow]))
    doc = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(doc)
    d.rounded_rectangle(u((x0, y0), (x1, y1)), radius=2.2 * U, fill=255)
    d.polygon(u((x1 - FOLD, y0 - 1), (x1 + 1, y0 - 1), (x1 + 1, y0 + FOLD)), fill=0)
    img.paste(Image.new('RGBA', (S, S), 'white'), (0, 0), doc)
    d = ImageDraw.Draw(img)
    d.polygon(u((x1 - FOLD, y0), (x1 - FOLD, y0 + FOLD - .8), (x1 - FOLD + .8, y0 + FOLD), (x1, y0 + FOLD)), fill=fold)
    for a, b in LINES:
        d.line(u(a, b), fill=fold, width=int(1.35 * U))
        for p in (a, b):
            r = .675 * U
            d.ellipse([p[0] * U - r, p[1] * U - r, p[0] * U + r, p[1] * U + r], fill=fold)

    # the trace: earlier versions in the ink colour, the newest one green with a white ring
    d.line(u(*TRACE), fill=ink, width=int(1.9 * U), joint='curve')
    for x, y in TRACE[:-1]:
        r = 1.5 * U
        d.ellipse([x * U - r, y * U - r, x * U + r, y * U + r], fill=ink)
    x, y = TRACE[-1]
    for r, c in ((2.75 * U, 'white'), (2.0 * U, dot)):
        d.ellipse([x * U - r, y * U - r, x * U + r, y * U + r], fill=c)
    return img.resize((256, 256), Image.LANCZOS)


def main():
    static = Path(__file__).resolve().parent / 'static'
    for name, theme in THEMES.items():
        img = draw(**theme)
        img.save(static / name, sizes=SIZES)
        if name == 'icon.ico':
            img.save(static / 'logo-256.png')
        print(static / name)


if __name__ == '__main__':
    main()
