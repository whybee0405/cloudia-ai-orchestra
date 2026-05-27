"""All Pillow image operations. Never use Pillow directly in agents."""
import io
import logging
from PIL import Image, ImageDraw, ImageFont, ImageFilter

logger = logging.getLogger(__name__)


def resize_and_crop(image_bytes: bytes, width: int, height: int, format: str = "JPEG") -> bytes:
    """Resize image to exact dimensions, cropping from centre if aspect ratio differs."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    target_ratio = width / height
    src_ratio = img.width / img.height

    if src_ratio > target_ratio:
        new_h = img.height
        new_w = int(target_ratio * new_h)
        left = (img.width - new_w) // 2
        img = img.crop((left, 0, left + new_w, new_h))
    else:
        new_w = img.width
        new_h = int(new_w / target_ratio)
        top = (img.height - new_h) // 2
        img = img.crop((0, top, new_w, top + new_h))

    img = img.resize((width, height), Image.LANCZOS)
    return _to_bytes(img, format)


def resize_fit(image_bytes: bytes, width: int, height: int, format: str = "JPEG") -> bytes:
    """Resize to fit within dimensions, preserving aspect ratio. Pads with white."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img.thumbnail((width, height), Image.LANCZOS)
    canvas = Image.new("RGB", (width, height), (255, 255, 255))
    offset = ((width - img.width) // 2, (height - img.height) // 2)
    canvas.paste(img, offset)
    return _to_bytes(canvas, format)


def overlay_logo(
    image_bytes: bytes,
    logo_bytes: bytes,
    position: str = "bottom-right",
    opacity: float = 0.8,
    size_fraction: float = 0.10,
) -> bytes:
    """Overlay a logo onto an image at the specified corner."""
    base = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")

    logo_w = int(base.width * size_fraction)
    logo_h = int(logo.height * (logo_w / logo.width))
    logo = logo.resize((logo_w, logo_h), Image.LANCZOS)

    # Apply opacity
    r, g, b, a = logo.split()
    a = a.point(lambda x: int(x * opacity))
    logo = Image.merge("RGBA", (r, g, b, a))

    margin = 20
    positions = {
        "bottom-right": (base.width - logo_w - margin, base.height - logo_h - margin),
        "bottom-left":  (margin, base.height - logo_h - margin),
        "top-right":    (base.width - logo_w - margin, margin),
        "top-left":     (margin, margin),
    }
    pos = positions.get(position, positions["bottom-right"])
    base.paste(logo, pos, mask=logo)
    return _to_bytes(base.convert("RGB"), "JPEG")


def add_colour_banner(
    image_bytes: bytes,
    text: str,
    bg_colour: str = "#000000",
    text_colour: str = "#FFFFFF",
    banner_height_fraction: float = 0.12,
) -> bytes:
    """Add a solid colour banner at the bottom of the image with text."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    banner_h = int(img.height * banner_height_fraction)
    draw = ImageDraw.Draw(img)
    y0 = img.height - banner_h
    draw.rectangle([(0, y0), (img.width, img.height)], fill=bg_colour)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", size=banner_h // 2)
    except IOError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    tx = (img.width - (bbox[2] - bbox[0])) // 2
    ty = y0 + (banner_h - (bbox[3] - bbox[1])) // 2
    draw.text((tx, ty), text, fill=text_colour, font=font)
    return _to_bytes(img, "JPEG")


def convert_format(image_bytes: bytes, target_format: str) -> bytes:
    """Convert image to target format (JPEG, PNG, WEBP)."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return _to_bytes(img, target_format.upper())


def get_dimensions(image_bytes: bytes) -> tuple[int, int]:
    """Return (width, height) of image."""
    img = Image.open(io.BytesIO(image_bytes))
    return img.width, img.height


def _to_bytes(img: Image.Image, format: str = "JPEG", quality: int = 92) -> bytes:
    buf = io.BytesIO()
    fmt = "JPEG" if format.upper() in ("JPG", "JPEG") else format.upper()
    if fmt == "JPEG":
        img.save(buf, format=fmt, quality=quality, optimize=True)
    else:
        img.save(buf, format=fmt)
    return buf.getvalue()
