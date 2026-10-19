import time

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from museum.models import SystemPrompt
from museum.services.gemini import BiographyError, BiographyHints, generate_biography
from museum.services.images import InvalidImage, process_upload


class Command(BaseCommand):
    help = 'Send a photo to Gemini and print the biography. Nothing is saved. Uses a real API call.'

    def add_arguments(self, parser):
        parser.add_argument('photo', help='Path to an image file')
        parser.add_argument('--object-type', default='', help='Pretend the user renamed it to this')
        parser.add_argument('--owner-name', default='')
        parser.add_argument('--about-me', default='')
        parser.add_argument(
            '--prompt', type=int, help='Try this SystemPrompt version (e.g. 3) instead of the active one'
        )

    def handle(self, *args, **options):
        try:
            with open(options['photo'], 'rb') as handle:
                photo = process_upload(File(handle))
        except (OSError, InvalidImage) as error:
            raise CommandError(error)

        hints = BiographyHints(
            object_type=options['object_type'],
            owner_name=options['owner_name'],
            about_me=options['about_me'],
        )
        prompt = None
        if options['prompt']:
            try:
                prompt = SystemPrompt.objects.get(pk=options['prompt'])
            except SystemPrompt.DoesNotExist:
                raise CommandError(f"There is no system prompt v{options['prompt']}.")
        used = prompt or SystemPrompt.active() or 'default prompt in code'

        self.stdout.write(f'Interviewing a {photo.width}x{photo.height} photo with {used}...\n')
        started = time.monotonic()
        try:
            bio = generate_biography(photo.content, photo.mime_type, hints, prompt=prompt)
        except BiographyError as error:
            raise CommandError(f'{error}\nUser would see: {error.user_message}')
        elapsed = time.monotonic() - started

        heading = self.style.MIGRATE_HEADING
        self.stdout.write(heading(f'{bio.name}, {bio.title}') + f'  ({bio.object_type})')
        self.stdout.write(f'"{bio.placard}"\n')
        for label, text in [
            ('Origin story', bio.origin_story),
            ('Defining trauma', bio.trauma),
            ('Hopes & fears', bio.hopes_and_fears),
            ('Opinion of you', bio.opinion_of_owner),
        ]:
            self.stdout.write(heading(label))
            self.stdout.write(text + '\n')
        self.stdout.write(heading('Rivals'))
        for rival in bio.rivals:
            self.stdout.write(f"- {rival['name']}: {rival['reason']}")

        words = sum(len(text.split()) for text in bio.as_model_fields().values() if isinstance(text, str))
        usage = ', '.join(f'{key.replace("_", " ")}: {value}' for key, value in bio.usage.items())
        self.stdout.write(
            self.style.SUCCESS(f'\n{bio.model_name} · {elapsed:.1f}s · ~{words} words · {usage}')
        )
