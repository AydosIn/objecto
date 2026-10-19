import io
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image

from museum.services import images
from museum.services.images import InvalidImage, process_upload

from .utils import make_image_file

GPS_IFD = 0x8825
ORIENTATION = 0x0112


def open_result(result):
    return Image.open(io.BytesIO(result.content))


class ProcessUploadTests(SimpleTestCase):
    def test_returns_jpeg(self):
        result = process_upload(make_image_file(format='PNG', name='mug.png'))
        self.assertEqual(result.mime_type, 'image/jpeg')
        self.assertEqual(open_result(result).format, 'JPEG')

    def test_large_image_shrinks_to_1600_keeping_proportions(self):
        result = process_upload(make_image_file(size=(4000, 3000)))
        self.assertEqual((result.width, result.height), (1600, 1200))
        self.assertEqual(open_result(result).size, (1600, 1200))

    def test_small_image_is_not_enlarged(self):
        result = process_upload(make_image_file(size=(640, 480)))
        self.assertEqual((result.width, result.height), (640, 480))

    def test_strips_exif_including_gps(self):
        source = Image.new('RGB', (100, 80), 'blue')
        exif = source.getexif()
        exif[0x010F] = 'Apple'  # camera make
        exif[GPS_IFD] = {2: (41.0, 18.0, 0.0), 4: (69.0, 16.0, 0.0)}  # latitude / longitude
        buffer = io.BytesIO()
        source.save(buffer, format='JPEG', exif=exif.tobytes())
        upload = SimpleUploadedFile('kitchen.jpg', buffer.getvalue())

        output = open_result(process_upload(upload))
        self.assertEqual(dict(output.getexif()), {})
        self.assertNotIn('exif', output.info)
        self.assertNotIn('xmp', output.info)

    def test_applies_phone_rotation_before_stripping_exif(self):
        # A portrait phone photo is often stored sideways with "rotate 90°" in EXIF.
        source = Image.new('RGB', (400, 300), 'green')
        exif = source.getexif()
        exif[ORIENTATION] = 6
        buffer = io.BytesIO()
        source.save(buffer, format='JPEG', exif=exif.tobytes())

        result = process_upload(SimpleUploadedFile('portrait.jpg', buffer.getvalue()))
        self.assertEqual((result.width, result.height), (300, 400))

    def test_transparent_png_gets_white_background(self):
        buffer = io.BytesIO()
        Image.new('RGBA', (20, 20), (0, 0, 0, 0)).save(buffer, format='PNG')
        result = process_upload(SimpleUploadedFile('sticker.png', buffer.getvalue()))
        self.assertGreater(open_result(result).getpixel((10, 10))[0], 245)

    def test_heic_is_accepted(self):
        result = process_upload(make_image_file(format='HEIF', name='IMG_0001.heic'))
        self.assertEqual(result.mime_type, 'image/jpeg')

    def test_webp_is_accepted(self):
        result = process_upload(make_image_file(format='WEBP', name='mug.webp'))
        self.assertEqual(result.mime_type, 'image/jpeg')

    def test_rejects_non_image(self):
        upload = SimpleUploadedFile('mug.jpg', b'definitely not a photo')
        with self.assertRaisesMessage(InvalidImage, "isn't an image"):
            process_upload(upload)

    def test_rejects_truncated_image(self):
        content = make_image_file(size=(200, 200)).read()
        upload = SimpleUploadedFile('broken.jpg', content[: len(content) // 2])
        with self.assertRaises(InvalidImage):
            process_upload(upload)

    def test_rejects_unsupported_format(self):
        with self.assertRaisesMessage(InvalidImage, 'JPEG, PNG, WebP or HEIC'):
            process_upload(make_image_file(format='GIF', name='mug.gif'))

    def test_rejects_files_over_the_size_limit(self):
        with mock.patch.object(images, 'MAX_UPLOAD_BYTES', 100):
            with self.assertRaisesMessage(InvalidImage, 'over 10 MB'):
                process_upload(make_image_file(size=(200, 200)))
