"""Draws the installer's wizard pictures from the app logo (desktop_watch/static/logo-256.png, made by
make_icon.py): the tall banner on the Welcome / Finish pages and the small logo at the top right of the
other pages, each at 100% and 200% scale. Needs Pillow."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
LOGO = HERE.parent / 'desktop_watch' / 'static' / 'logo-256.png'
C1, C2 = (79, 70, 229), (6, 182, 212)


def lerp(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def font(size, bold=True, cjk=False):
    names = ('msyhbd.ttc', 'msyh.ttc') if cjk else ('segoeuib.ttf', 'msyhbd.ttc') if bold else ('segoeui.ttf', 'msyh.ttc')
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def banner(scale):
    w, h = 164 * scale, 314 * scale
    img = Image.new('RGB', (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            px[x, y] = lerp(C1, C2, min(1, (y * .8 + x * .4) / h))
    # soft light and a faint dotted texture, like the app's empty states
    glow = Image.new('L', (w, h), 0)
    ImageDraw.Draw(glow).ellipse([-w * .6, -h * .25, w * 1.1, h * .45], fill=60)
    img.paste((255, 255, 255), (0, 0), glow.filter(ImageFilter.GaussianBlur(28 * scale)))
    d = ImageDraw.Draw(img)
    step = 12 * scale
    for y in range(step // 2, h, step):
        for x in range(step // 2, w, step):
            r = .9 * scale
            d.ellipse([x - r, y - r, x + r, y + r], fill=lerp(lerp(C1, C2, min(1, (y * .8 + x * .4) / h)), (255, 255, 255), .16))
    logo = Image.open(LOGO).convert('RGBA').resize((76 * scale, 76 * scale), Image.LANCZOS)
    shadow = Image.new('L', (w, h), 0)
    lx, ly = (w - logo.width) // 2, int(h * .24)
    ImageDraw.Draw(shadow).rounded_rectangle([lx, ly + 6 * scale, lx + logo.width, ly + logo.height + 6 * scale], radius=18 * scale, fill=110)
    img.paste((30, 27, 90), (0, 0), shadow.filter(ImageFilter.GaussianBlur(8 * scale)))
    img.paste(logo, (lx, ly), logo)
    for text, size, y, bold in (('DeskTrace', 21, .24 * h + 96 * scale, True), ('桌迹', 14, .24 * h + 126 * scale, False)):
        f = font(size * scale, bold, cjk=text == '桌迹')
        tw = d.textlength(text, font=f)
        d.text(((w - tw) / 2, y), text, font=f, fill='white')
    f = font(9 * scale, False)
    for i, line in enumerate(('Every version of your files,', 'one click away.')):
        tw = d.textlength(line, font=f)
        d.text(((w - tw) / 2, h - (44 - i * 14) * scale), line, font=f, fill=(235, 240, 255))
    return img


def small(scale):
    s = 55 * scale
    img = Image.new('RGB', (s, s), 'white')
    logo = Image.open(LOGO).convert('RGBA').resize((s - 6 * scale, s - 6 * scale), Image.LANCZOS)
    img.paste(logo, (3 * scale, 3 * scale), logo)
    return img


if __name__ == '__main__':
    for scale in (1, 2):
        banner(scale).save(HERE / f'wizard-large-{scale}x.bmp')
        small(scale).save(HERE / f'wizard-small-{scale}x.bmp')
    print('wizard images written to', HERE)
