from types import SimpleNamespace
from unittest import mock

import httpx
from django.test import SimpleTestCase, TestCase, override_settings
from google.genai import errors

from museum.models import SystemPrompt
from museum.prompts import DEFAULT_SYSTEM_PROMPT, build_user_prompt
from museum.services.gemini import (
    BiographyHints,
    GeminiBiography,
    GenerationFailed,
    NotAnObject,
    generate_biography,
)

GOOD = {
    'is_object': True,
    'object_type': 'ceramic mug',
    'name': 'Gerald',
    'title': 'Mug of the Third Shelf',
    'placard': 'Survived three moves and one terrible latte.',
    'origin_story': 'Born in a kiln.',
    'trauma': 'The Great Microwave Incident.',
    'rivals': [{'name': 'The Dishwasher', 'reason': 'It knows what it did.'}],
    'hopes_and_fears': 'Hopes for tea. Fears the floor.',
    'opinion_of_owner': 'Means well. Rinses poorly.',
}


def fake_response(data=None, text=None):
    """Looks like a google-genai response. parsed is set only for valid data, like the SDK."""
    parsed = None
    if data is not None:
        try:
            parsed = GeminiBiography.model_validate(data)
        except ValueError:
            pass
    usage = SimpleNamespace(prompt_token_count=1700, candidates_token_count=480, thoughts_token_count=0)
    return SimpleNamespace(parsed=parsed, text=text or '', usage_metadata=usage)


@override_settings(GEMINI_API_KEY='test-key', GEMINI_MODEL='gemini-test-flash')
class GenerateBiographyTests(TestCase):
    def setUp(self):
        patcher = mock.patch('museum.services.gemini.genai.Client')
        self.client_class = patcher.start()
        self.addCleanup(patcher.stop)
        self.generate = self.client_class.return_value.models.generate_content

    def call(self, hints=BiographyHints()):
        return generate_biography(b'jpeg-bytes', 'image/jpeg', hints)

    def test_success(self):
        self.generate.return_value = fake_response(GOOD)
        result = self.call()

        self.assertEqual(result.name, 'gerald')
        # Everything comes back in the app's lowercase voice.
        self.assertEqual(result.rivals, [{'name': 'the dishwasher', 'reason': 'it knows what it did.'}])
        self.assertEqual(result.model_name, 'gemini-test-flash')
        self.assertEqual(result.usage['input_tokens'], 1700)
        self.assertNotIn('usage', result.as_model_fields())

    def test_sends_photo_prompt_and_schema(self):
        self.generate.return_value = fake_response(GOOD)
        self.call(BiographyHints(owner_name='Aydos'))

        self.client_class.assert_called_once()
        self.assertEqual(self.client_class.call_args.kwargs['api_key'], 'test-key')
        kwargs = self.generate.call_args.kwargs
        self.assertEqual(kwargs['model'], 'gemini-test-flash')
        self.assertEqual(kwargs['config'].system_instruction, SystemPrompt.active().text)
        self.assertIs(kwargs['config'].response_schema, GeminiBiography)
        image_part, prompt = kwargs['contents']
        self.assertEqual(image_part.inline_data.data, b'jpeg-bytes')
        self.assertEqual(image_part.inline_data.mime_type, 'image/jpeg')
        self.assertIn('Aydos', prompt)

    def test_not_an_object(self):
        self.generate.return_value = fake_response(
            {'is_object': False, 'rejection_reason': 'That is a person.'}
        )
        with self.assertRaises(NotAnObject) as caught:
            self.call()
        self.assertIn('That is a person.', caught.exception.user_message)

    def test_falls_back_to_text_when_parsed_is_missing(self):
        response = fake_response(text=GeminiBiography.model_validate(GOOD).model_dump_json())
        self.generate.return_value = response
        self.assertEqual(self.call().name, 'gerald')

    def test_retries_once_when_biography_is_incomplete(self):
        self.generate.side_effect = [fake_response({**GOOD, 'trauma': ''}), fake_response(GOOD)]
        with self.assertLogs('museum.services.gemini', 'WARNING'):
            self.assertEqual(self.call().trauma, 'the great microwave incident.')
        self.assertEqual(self.generate.call_count, 2)

    def test_gives_up_after_two_broken_responses(self):
        self.generate.return_value = fake_response(text='{"is_object": tr')
        with self.assertLogs('museum.services.gemini', 'WARNING') as logs:
            with self.assertRaises(GenerationFailed):
                self.call()
        self.assertEqual(len(logs.records), 2)
        self.assertEqual(self.generate.call_count, 2)

    def test_api_error(self):
        self.generate.side_effect = errors.ClientError(
            429, {'error': {'message': 'Quota exceeded', 'status': 'RESOURCE_EXHAUSTED'}}
        )
        with self.assertRaises(GenerationFailed) as caught:
            self.call()
        self.assertIn('429', str(caught.exception))
        self.assertIn('shy', caught.exception.user_message)

    def test_timeout(self):
        self.generate.side_effect = httpx.ReadTimeout('timed out')
        with self.assertRaises(GenerationFailed):
            self.call()

    def test_long_fields_are_clipped_and_rivals_capped(self):
        rivals = [{'name': f'Rival {n}', 'reason': 'Because.'} for n in range(4)]
        self.generate.return_value = fake_response({**GOOD, 'name': 'G' * 500, 'rivals': rivals})
        result = self.call()
        self.assertEqual(len(result.name), 100)
        self.assertEqual(len(result.rivals), 2)

    @override_settings(GEMINI_API_KEY='')
    def test_missing_key_fails_without_calling_gemini(self):
        with self.assertRaises(GenerationFailed):
            self.call()
        self.client_class.assert_not_called()

    def system_instruction(self):
        return self.generate.call_args.kwargs['config'].system_instruction

    def test_uses_the_active_prompt_from_the_database(self):
        SystemPrompt.objects.update(is_active=False)
        active = SystemPrompt.objects.create(label='Noir', text='Write like a noir detective.', is_active=True)
        self.generate.return_value = fake_response(GOOD)
        result = self.call()
        self.assertEqual(self.system_instruction(), 'Write like a noir detective.')
        self.assertEqual(result.prompt_version, active)
        self.assertEqual(result.as_model_fields()['prompt_version'], active)

    def test_falls_back_to_code_prompt_when_none_is_active(self):
        SystemPrompt.objects.update(is_active=False)
        self.generate.return_value = fake_response(GOOD)
        result = self.call()
        self.assertEqual(self.system_instruction(), DEFAULT_SYSTEM_PROMPT)
        self.assertIsNone(result.prompt_version)

    def test_explicit_prompt_overrides_the_active_one(self):
        draft = SystemPrompt.objects.create(label='Draft', text='Write like Shakespeare.')
        self.generate.return_value = fake_response(GOOD)
        result = generate_biography(b'jpeg-bytes', 'image/jpeg', BiographyHints(), prompt=draft)
        self.assertEqual(self.system_instruction(), 'Write like Shakespeare.')
        self.assertEqual(result.prompt_version, draft)


class PromptTests(SimpleTestCase):
    def test_no_hints(self):
        self.assertEqual(build_user_prompt(BiographyHints()), 'Here is the object. Write its biography.')

    def test_all_hints(self):
        prompt = build_user_prompt(
            BiographyHints(object_type='vase', owner_name='Aydos', about_me='I love tea.')
        )
        self.assertIn('The owner says this object is: vase', prompt)
        self.assertIn("The owner's name: Aydos", prompt)
        self.assertIn('<about_me>\nI love tea.\n</about_me>', prompt)
