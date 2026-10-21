"""An exhibit as a PDF to keep, print or send: a cover in its aura colour, then the story.

    page 1: aura colour, name, title, the photo as a print, the placard
    page 2+: every section, each headed in its recap slide's colour

Pure Python (fpdf2), so it runs on Vercel with no system libraries. The font is Inter
(SIL Open Font License, museum/fonts/OFL.txt), latin glyphs only: characters it can't
draw, like emoji, are left out rather than printed as empty boxes.
"""

import io
from functools import cache
from pathlib import Path

from fontTools.ttLib import TTFont
from fpdf import FPDF
from fpdf.enums import MethodReturnValue
from PIL import Image

from .aura import RAMP, slide_fields

FONT_DIR = Path(__file__).resolve().parent.parent / 'fonts'
# fpdf2 knows styles, not weights: B is semibold here and I is black (the big name).
FONTS = {'': 'Inter-Regular.ttf', 'B': 'Inter-SemiBold.ttf', 'I': 'Inter-Black.ttf'}
# Fields whose ink is white in main.css; every other field takes near-black ink.
WHITE_INK = {'grape', 'midnight'}
INK = (17, 17, 17)

MARGIN = 18  # mm
LINE = 6.2  # mm per line of body text


@cache
def _drawable():
    """Every character the font has a glyph for."""
    return frozenset(TTFont(FONT_DIR / FONTS['']).getBestCmap())


def clean(text):
    """Lowercase (the app's voice), only characters the font can draw, no stray spaces."""
    drawable = _drawable()
    text = ''.join(c for c in text.lower() if c == '\n' or ord(c) in drawable)
    return '\n'.join(' '.join(line.split()) for line in text.splitlines()).strip()


def _rgb(hex_colour):
    hex_colour = hex_colour.lstrip('#')
    return tuple(int(hex_colour[i : i + 2], 16) for i in (0, 2, 4))


def _ink(field):
    return (255, 255, 255) if field.slug in WHITE_INK else INK


class StoryPDF(FPDF):
    def __init__(self, site_url):
        super().__init__(format='A4')
        self.site_url = site_url
        for style, filename in FONTS.items():
            self.add_font('Inter', style, FONT_DIR / filename)
        self.set_margins(MARGIN, MARGIN, MARGIN)
        self.set_creator('object biographies')

    def multi_cell(self, *args, align='L', **kwargs):
        # fpdf2 justifies by default, which stretches short lines; the app is ragged-right.
        return super().multi_cell(*args, align=align, **kwargs)

    @property
    def text_width(self):
        return self.w - 2 * MARGIN

    def footer(self):
        # The cover is all colour, no footer.
        if self.page_no() == 1:
            return
        self.set_y(-14)
        self.set_font('Inter', '', 9)
        self.set_text_color(120, 120, 120)
        host = self.site_url.split('://')[-1]
        self.cell(0, 5, f'written down at object biographies · {host}', align='C', link=self.site_url)

    def text_height(self, text, width, line_height):
        return self.multi_cell(width, line_height, text, dry_run=True,
                               output=MethodReturnValue.HEIGHT)

    def fit_font_size(self, text, width, start, smallest):
        """The biggest size from `start` down at which `text` fits on one line."""
        size = start
        while size > smallest:
            self.set_font_size(size)
            if self.get_string_width(text) <= width:
                break
            size -= 2
        self.set_font_size(size)
        return size

    def keep_room(self, height):
        """Start a new page unless `height` mm still fits on this one."""
        if self.get_y() + height > self.page_break_trigger:
            self.add_page()


def build_pdf(exhibit, image_bytes, aura, site_url, opinion_heading='what it thinks of you'):
    """The exhibit's PDF, as bytes. `aura` is its Field (services/aura.py)."""
    pdf = StoryPDF(site_url)
    pdf.set_title(f'{clean(exhibit.name)}, the {clean(exhibit.object_type)}')
    _cover(pdf, exhibit, image_bytes, aura)
    _story(pdf, exhibit, aura, opinion_heading)
    return bytes(pdf.output())


# --- Page 1: the cover ---------------------------------------------------------------


def _cover(pdf, exhibit, image_bytes, aura):
    pdf.set_auto_page_break(False)
    pdf.add_page()
    width = pdf.text_width

    pdf.set_fill_color(*_rgb(aura.hex))
    pdf.rect(0, 0, pdf.w, pdf.h, style='F')
    pdf.set_text_color(*_ink(aura))

    pdf.set_xy(MARGIN, MARGIN)
    pdf.set_font('Inter', 'B', 10)
    pdf.cell(0, 5, 'object biographies', new_x='LMARGIN', new_y='NEXT')

    pdf.ln(8)
    name = clean(exhibit.name)
    pdf.set_font('Inter', 'I')
    size = pdf.fit_font_size(name, width, start=64, smallest=34)
    pdf.multi_cell(width, size * 0.4, name, new_x='LMARGIN', new_y='NEXT')
    pdf.ln(2)
    pdf.set_font('Inter', 'B', 17)
    pdf.multi_cell(width, 8, clean(exhibit.title), new_x='LMARGIN', new_y='NEXT')
    top = pdf.get_y() + 8

    # The placard and the facts line sit at the bottom; the photo gets the room between.
    placard = f'“{clean(exhibit.placard)}”'
    pdf.set_font('Inter', 'B', 15)
    placard_top = pdf.h - MARGIN - 12 - pdf.text_height(placard, width, 7.5)
    _print(pdf, image_bytes, top, placard_top - 10)

    pdf.set_xy(MARGIN, placard_top)
    pdf.multi_cell(width, 7.5, placard)
    pdf.set_xy(MARGIN, pdf.h - MARGIN - 5)
    pdf.set_font('Inter', '', 10)
    since = f'{exhibit.created_at:%d %b %Y}'.lstrip('0').lower()
    pdf.cell(0, 5, f"aura: {aura.name}  ·  it's a {clean(exhibit.object_type)}  ·  "
                   f'in the museum since {since}')


def _print(pdf, image_bytes, top, bottom):
    """The photo on a white rounded card, centred, as big as the space allows."""
    pad = 4
    with Image.open(io.BytesIO(image_bytes)) as image:
        ratio = image.width / image.height
    w = min(min(pdf.text_width, 150) - 2 * pad, (bottom - top - 2 * pad) * ratio)
    h = w / ratio
    x = (pdf.w - w) / 2
    y = top + (bottom - top - h) / 2
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(x - pad, y - pad, w + 2 * pad, h + 2 * pad, style='F',
             round_corners=True, corner_radius=4)
    pdf.image(io.BytesIO(image_bytes), x=x, y=y, w=w, h=h)


# --- Page 2+: the story --------------------------------------------------------------


def _story(pdf, exhibit, aura, opinion_heading):
    pdf.set_auto_page_break(True, margin=22)
    pdf.add_page()
    # The same colour per section as the recap slides.
    fields = slide_fields(aura, len(RAMP))

    _section(pdf, 'where it came from', fields[1], exhibit.origin_story)
    _section(pdf, 'the trauma', fields[2], exhibit.trauma)
    if exhibit.rivals:
        _heading(pdf, 'the beef', fields[3])
        for rival in exhibit.rivals:
            pdf.keep_room(LINE * 3)
            pdf.set_font('Inter', 'B', 13)
            pdf.multi_cell(pdf.text_width, 7, f'vs {clean(rival["name"])}',
                           new_x='LMARGIN', new_y='NEXT')
            pdf.set_font('Inter', '', 12)
            pdf.multi_cell(pdf.text_width, LINE, clean(rival['reason']),
                           new_x='LMARGIN', new_y='NEXT')
            pdf.ln(3)
        pdf.ln(5)
    _section(pdf, 'hopes and fears', fields[4], exhibit.hopes_and_fears)
    _bubble(pdf, opinion_heading, fields[5], exhibit)


def _heading(pdf, label, field):
    """A pill in the section's colour. Moves to a new page if not even the
    heading and the first lines would fit, so a heading never ends a page."""
    pdf.keep_room(10 + LINE * 3)
    pdf.set_font('Inter', 'B', 11)
    w = pdf.get_string_width(label) + 8
    pdf.set_fill_color(*_rgb(field.hex))
    pdf.rect(pdf.get_x(), pdf.get_y(), w, 7, style='F', round_corners=True, corner_radius=3.5)
    pdf.set_text_color(*_ink(field))
    pdf.cell(w, 7, label, align='C', new_x='LMARGIN', new_y='NEXT')
    pdf.set_text_color(*INK)
    pdf.ln(3)


def _section(pdf, label, field, text):
    _heading(pdf, label, field)
    pdf.set_font('Inter', '', 12)
    pdf.multi_cell(pdf.text_width, LINE, clean(text), new_x='LMARGIN', new_y='NEXT')
    pdf.ln(8)


def _bubble(pdf, label, field, exhibit):
    """What it thinks of its owner, as a text bubble in the section's colour."""
    pad = 5
    text = clean(exhibit.opinion_of_owner)
    pdf.set_font('Inter', '', 12)
    width = pdf.text_width - 2 * pad
    height = pdf.text_height(text, width, LINE) + 2 * pad
    _heading(pdf, label, field)
    pdf.keep_room(height + 8)

    pdf.set_font('Inter', 'B', 10)
    pdf.cell(0, 5, f'{clean(exhibit.name)}:', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(1)
    top = pdf.get_y()
    pdf.set_fill_color(*_rgb(field.hex))
    pdf.rect(MARGIN, top, pdf.text_width, height, style='F', round_corners=True, corner_radius=5)
    pdf.set_text_color(*_ink(field))
    pdf.set_font('Inter', '', 12)
    pdf.set_xy(MARGIN + pad, top + pad)
    pdf.multi_cell(width, LINE, text)
    pdf.set_text_color(*INK)
