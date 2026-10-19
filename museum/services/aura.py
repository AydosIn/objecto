"""An exhibit's "aura": the colour its recap is drenched in.

The photo's dominant colour is snapped to one fixed ramp of eight fields, so every
page uses the same colours and nothing is ad hoc. The recap's slides then walk the
ramp starting from the aura.
"""

import colorsys
from dataclasses import dataclass
from functools import lru_cache

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

# Below this saturation a photo is basically white, grey or black.
GREY_SATURATION = 0.18


def _hsv(hex_colour):
    r, g, b = (int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hsv(r, g, b)


def dominant_colour(image):
    """The object's main colour, as (r, g, b).

    Looks at the middle of the frame (where the object usually is) and prefers
    any real colour covering at least 5% of it over a big neutral wall or table.
    """
    width, height = image.size
    centre = image.convert('RGB').crop(
        (width * 0.15, height * 0.15, width * 0.85, height * 0.85)
    )
    small = centre.resize((48, 48))
    colours = small.quantize(colors=8).convert('RGB').getcolors(48 * 48)
    total = sum(count for count, _ in colours)

    def hsv(rgb):
        return colorsys.rgb_to_hsv(*(c / 255 for c in rgb))

    colourful = [
        (count, rgb)
        for count, rgb in colours
        if hsv(rgb)[1] >= GREY_SATURATION and count / total >= 0.05
    ]
    candidates = colourful or colours
    return max(candidates, key=lambda item: item[0] * (0.3 + hsv(item[1])[2]))[1]


def nearest_field(rgb):
    h, s, _ = colorsys.rgb_to_hsv(*(c / 255 for c in rgb))
    if s < GREY_SATURATION:
        return MIDNIGHT

    def hue_distance(field):
        fh = _hsv(field.hex)[0]
        d = abs(h - fh)
        return min(d, 1 - d)

    return min(RAMP, key=hue_distance)


@lru_cache(maxsize=512)
def _aura_for_file(path):
    with Image.open(path) as image:
        return nearest_field(dominant_colour(image))


def aura_for(image_field):
    """The exhibit photo's aura Field. Cached per file (exhibit photos never change)."""
    try:
        return _aura_for_file(image_field.path)
    except (OSError, ValueError):
        return RAMP[0]


def slide_fields(aura, count):
    """`count` fields for a recap: the aura first, then the ramp in order, never the
    same colour twice in a row."""
    start = RAMP.index(aura) if aura in RAMP else 0
    return [RAMP[(start + i) % len(RAMP)] for i in range(count)]
