import os
from functools import cache

IMAGE_DIR = os.path.dirname(__file__)


def load_named_image(name: str):
    return _load_named_image_file(name).copy()


@cache
def _load_named_image_file(name: str):
    from PIL import Image

    image_path = os.path.join(IMAGE_DIR, f"{name}.png")
    return Image.open(image_path).convert("1").convert("L")


def draw_pending_discs(image, n: int):
    from PIL import ImageDraw

    draw = ImageDraw.Draw(image)
    for i in range(min(n, 25)):
        x = (8 * i) + 3
        y = 114
        draw.ellipse(((x, y), (x + 4, y + 4)), width=2)
