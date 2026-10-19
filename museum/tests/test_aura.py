import io

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from PIL import Image

from museum.services.aura import MIDNIGHT, RAMP, dominant_colour, nearest_field, slide_fields

from .utils import TempMediaMixin, make_exhibit

User = get_user_model()


def photo(colour, background=None, size=(120, 120)):
    """A square of `colour`, optionally on a bigger `background`."""
    image = Image.new('RGB', size, background or colour)
    if background:
        image.paste(Image.new('RGB', (40, 40), colour), (40, 40))
    return image


class AuraTests(SimpleTestCase):
    def test_saturated_colours_snap_to_the_nearest_ramp_field(self):
        cases = {
            (255, 30, 120): 'pink',
            (255, 110, 20): 'orange',
            (30, 160, 255): 'pool',
            (90, 40, 255): 'grape',
            (200, 240, 50): 'lime',
        }
        for rgb, slug in cases.items():
            with self.subTest(rgb=rgb):
                self.assertEqual(nearest_field(rgb).slug, slug)

    def test_grey_objects_get_midnight(self):
        for rgb in [(240, 240, 240), (128, 128, 128), (15, 15, 15)]:
            with self.subTest(rgb=rgb):
                self.assertIs(nearest_field(rgb), MIDNIGHT)

    def test_a_small_bright_object_beats_a_big_dull_background(self):
        image = photo((255, 40, 120), background=(200, 195, 185))
        self.assertEqual(nearest_field(dominant_colour(image)).slug, 'pink')

    def test_slide_fields_start_at_the_aura_and_never_repeat_back_to_back(self):
        lime = RAMP[2]
        fields = slide_fields(lime, len(RAMP))
        self.assertEqual(fields[0], lime)
        self.assertEqual(len(set(fields)), len(RAMP))
        for a, b in zip(fields, fields[1:]):
            self.assertNotEqual(a, b)


class RecapPageColourTests(TempMediaMixin, TestCase):
    def test_exhibit_page_is_drenched_in_its_photos_aura(self):
        owner = User.objects.create_user(email='gerald@mail.com', password='s3cret-mug')
        buffer = io.BytesIO()
        photo((30, 160, 255)).save(buffer, format='JPEG')
        exhibit = make_exhibit(owner, image=SimpleUploadedFile('blue.jpg', buffer.getvalue()))
        self.client.force_login(owner)

        response = self.client.get(exhibit.get_absolute_url())
        self.assertEqual(response.context['aura'].slug, 'pool')
        self.assertContains(response, 'class="field--pool"')
        self.assertContains(response, 'aura: pool day')
