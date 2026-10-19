"""An exhibit's "aura": the colour its recap is drenched in.

The photo's main colour is snapped to one fixed ramp of seven fields (plus midnight for
black, white and grey objects), so every page uses the same colours and nothing is ad
hoc. It is worked out once, when the photo is uploaded, and stored on the exhibit.
"""

import colorsys
import io
from dataclasses import dataclass

from PIL import Image


@dataclass(frozen=True)
class Field:
    slug: str  # CSS class suffix: field--<slug>
    name: str  # what the aura is called on the summary card
    hex: str


# The ramp, in slide order. Ink colours live in main.css (.field--<slug>).
RAMP = (
    Field('grape', 'grape soda', '#5B2BFF'),
    Field('pink', 'hot pink', '#FF2E7E'),
    Field('lime', 'highlighter', '#C8F031'),
    Field('orange', 'traffic cone', '#FF6A13'),
    Field('pool', 'pool day', '#1FA2FF'),
    Field('butter', 'butter', '#FFD43B'),
    Field('mint', 'mint gum', '#2BE0A0'),
)
MIDNIGHT = Field('midnight', 'midnight', '#111111')
BY_SLUG = {field.slug: field for field in (*RAMP, MIDNIGHT)}

# A pixel only counts as a colour when it is both saturated and lit: in near-black
# pixels a tiny colour cast reads as high saturation.
MIN_SATURATION = 0.18
MIN_BRIGHTNESS = 0.22
# When neutral pixels (black, white, grey) fill this much of the very centre of the
# frame, the object itself is neutral, whatever colourful table it stands on.
NEUTRAL_OBJECT_SHARE = 0.6


def _hsv(rgb):
    return colorsys.rgb_to_hsv(*(c / 255 for c in rgb))


def _is_colour(rgb):
    _, s, v = _hsv(rgb)
    return s >= MIN_SATURATION and v >= MIN_BRIGHTNESS


def _colours(image, box):
    """The 8 main colours of one region, as (count, rgb) pairs, plus the pixel total."""
    colours = image.crop(box).resize((48, 48)).quantize(colors=8).convert('RGB').getcolors(48 * 48)
    return colours, sum(count for count, _ in colours)


def dominant_colour(image):
    """The object's main colour, as (r, g, b).

    The object is usually in the middle of the frame. If the very centre is mostly
    black, white or grey, the object itself is neutral, whatever colourful table it
    stands on. Otherwise any real colour covering at least 5% of the middle wins over
    a big neutral wall or table.
    """
    image = image.convert('RGB')
    w, h = image.size
    weight = lambda item: item[0] * (0.3 + _hsv(item[1])[2])  # noqa: E731

    core, core_total = _colours(image, (w * 0.3, h * 0.3, w * 0.7, h * 0.7))
    core_neutral = [item for item in core if not _is_colour(item[1])]
    if sum(count for count, _ in core_neutral) / core_total >= NEUTRAL_OBJECT_SHARE:
        return max(core_neutral, key=weight)[1]

    middle, total = _colours(image, (w * 0.15, h * 0.15, w * 0.85, h * 0.85))
    colourful = [item for item in middle if _is_colour(item[1]) and item[0] / total >= 0.05]
    return max(colourful or middle, key=weight)[1]


def nearest_field(rgb):
    if not _is_colour(rgb):
        return MIDNIGHT
    h = _hsv(rgb)[0]

    def hue_distance(field):
        fh = _hsv(tuple(int(field.hex[i : i + 2], 16) for i in (1, 3, 5)))[0]
        d = abs(h - fh)
        return min(d, 1 - d)

    return min(RAMP, key=hue_distance)


def aura_from_image(image):
    return nearest_field(dominant_colour(image))


def aura_from_bytes(content):
    """For uploads: the cleaned JPEG bytes, before they are stored anywhere."""
    with Image.open(io.BytesIO(content)) as image:
        return aura_from_image(image)


def aura_of(exhibit):
    """The exhibit's aura Field. Stored at upload; older exhibits get it worked out
    (from storage, so remote storage works too) and saved the first time they're shown."""
    if exhibit.aura in BY_SLUG:
        return BY_SLUG[exhibit.aura]
    try:
        with exhibit.image.open('rb') as stored, Image.open(stored) as image:
            aura = aura_from_image(image)
    except (OSError, ValueError):
        return RAMP[0]
    if exhibit.pk:
        type(exhibit).objects.filter(pk=exhibit.pk).update(aura=aura.slug)
    exhibit.aura = aura.slug
    return aura


def slide_fields(aura, count):
    """`count` fields for a recap, starting on the aura and never repeating a colour
    back to back. A midnight aura opens on midnight, then walks the ramp."""
    if aura not in RAMP:
        return [aura, *(RAMP[i % len(RAMP)] for i in range(count - 1))]
    start = RAMP.index(aura)
    return [RAMP[(start + i) % len(RAMP)] for i in range(count)]
