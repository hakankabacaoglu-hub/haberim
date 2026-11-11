"""Draw the app icons into site/ (run at build time on GitHub Actions)."""
from pathlib import Path

from PIL import Image, ImageDraw

SITE = Path(__file__).resolve().parent.parent / "site"


def icon(size, name):
    im = Image.new("RGB", (size, size), "#0f1115")
    d = ImageDraw.Draw(im)
    pad = size * 0.2
    d.rounded_rectangle([pad, pad, size - pad, pad + size * 0.14], radius=size * 0.04, fill="#f5a524")
    for i in range(3):
        y = pad + size * 0.24 + i * size * 0.13
        right = size - pad if i < 2 else size * 0.62
        d.rounded_rectangle([pad, y, right, y + size * 0.07], radius=size * 0.03, fill="#e9ebef")
    im.save(SITE / name)


icon(180, "apple-touch-icon.png")
icon(192, "icon-192.png")
icon(512, "icon-512.png")
