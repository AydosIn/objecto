"""Turn an uploaded photo into a small, clean JPEG that is safe to store and send to Gemini.

    validate (size, real image, allowed format)
    → rotate upright → flatten transparency → shrink to 1600 px → re-encode without metadata
"""

import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_DIMENSION = 1600
JPEG_QUALITY = 85

# Pillow format names. MPO is how Pillow reads many phone-camera JPEGs.
ALLOWED_FORMATS = {'JPEG', 'MPO', 'PNG', 'WEBP', 'HEIF'}


class InvalidImage(Exception):
    """The upload can't be used. The message is safe to show to the user."""


@dataclass(frozen=True)
class ProcessedImage:
    content: bytes
    mime_type: str
    width: int
    height: int


def process_upload(upload) -> ProcessedImage:
    """Validate and clean an uploaded file (anything with .size, .read() and .seek())."""
    if upload.size > MAX_UPLOAD_BYTES:
        raise InvalidImage('That photo is over 10 MB. Try a smaller one.')

    # verify() checks the file is a real, undamaged image without decoding all of it.
    # It leaves the image unusable, so the file is opened a second time below.
    try:
        upload.seek(0)
        with Image.open(upload) as probe:
            probe.verify()
            image_format = probe.format
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError, ValueError):
        raise InvalidImage("That file isn't an image we can read.")

    if image_format not in ALLOWED_FORMATS:
        raise InvalidImage('Please upload a JPEG, PNG, WebP or HEIC photo.')

    try:
        upload.seek(0)
        with Image.open(upload) as image:
            # Phones store "rotate me" in EXIF instead of rotating the pixels.
            # Apply it now, because the EXIF data is about to be thrown away.
            image = ImageOps.exif_transpose(image)
            image = _to_rgb(image)
            image.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)
            # Drop every bit of metadata (EXIF, GPS location, XMP, camera model...).
            image.info = {}

            output = io.BytesIO()
            image.save(output, format='JPEG', quality=JPEG_QUALITY, optimize=True)
    except (Image.DecompressionBombError, OSError, ValueError):
        raise InvalidImage("That file isn't an image we can read.")

    return ProcessedImage(
        content=output.getvalue(),
        mime_type='image/jpeg',
        width=image.width,
        height=image.height,
    )


def _to_rgb(image):
    """JPEG has no transparency: put transparent images on a white background."""
    if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
        image = image.convert('RGBA')
        background = Image.new('RGB', image.size, (255, 255, 255))
        background.paste(image, mask=image.getchannel('A'))
        return background
    return image.convert('RGB')
