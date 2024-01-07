import os
from functools import cache

IMAGE_DIR = os.path.dirname(__file__)


@cache
def load_named_image(name: str):
    from PIL import Image

    image_path = os.path.join(IMAGE_DIR, f"{name}.png")
    return Image.open(image_path).convert("1").convert("L")
