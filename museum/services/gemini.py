"""The only place that talks to Gemini. Views call generate_biography(); tests mock it.

One request per biography: photo + prompt in, JSON matching GeminiBiography out.
"""

import logging
from dataclasses import dataclass, field, fields

import httpx
from django.conf import settings
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, ValidationError

from museum.models import Exhibit, SystemPrompt
from museum.prompts import DEFAULT_SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 60  # usually ~10 s, but the odd call has taken 40+
MAX_ATTEMPTS = 2  # one automatic retry when the JSON is broken or incomplete
TEMPERATURE = 1.0  # high enough that "Regenerate" gives a different story


# --- What goes in and out -----------------------------------------------------------


@dataclass(frozen=True)
class BiographyHints:
    """Optional extra context. object_type is set when the user renames an object."""

    object_type: str = ''
    owner_name: str = ''
    about_me: str = ''


@dataclass(frozen=True)
class BiographyResult:
    object_type: str
    name: str
    title: str
    placard: str
    origin_story: str
    trauma: str
    rivals: list
    hopes_and_fears: str
    opinion_of_owner: str
    model_name: str
    # Token usage, for curiosity and cost estimates. Not stored on the Exhibit.
    usage: dict = field(default_factory=dict, compare=False)
    # The SystemPrompt version used, or None for the default prompt in code.
    prompt_version: SystemPrompt | None = None

    def as_model_fields(self):
        """The fields that map one-to-one onto Exhibit."""
        return {f.name: getattr(self, f.name) for f in fields(self) if f.name != 'usage'}


class BiographyError(Exception):
    """Base error. user_message is safe to show; str(error) is the detail for logs."""

    user_message = "it's being shy. try again in a sec."
    # Known only when Gemini actually answered (a refusal still costs tokens).
    usage = {}
    prompt_version = None


class NotAnObject(BiographyError):
    def __init__(self, reason, usage=None, prompt_version=None):
        super().__init__(f'Not an object: {reason}')
        self.user_message = (
            f"hmm, that doesn't look like an object we can interview. {reason}".strip()
        )
        self.usage = usage or {}
        self.prompt_version = prompt_version


class GenerationFailed(BiographyError):
    pass


# --- The JSON shape Gemini must return -----------------------------------------------


class GeminiRival(BaseModel):
    name: str
    reason: str


class GeminiBiography(BaseModel):
    is_object: bool
    rejection_reason: str = ''
    object_type: str = ''
    name: str = ''
    title: str = ''
    placard: str = ''
    origin_story: str = ''
    trauma: str = ''
    rivals: list[GeminiRival] = []
    hopes_and_fears: str = ''
    opinion_of_owner: str = ''


TEXT_FIELDS = (
    'object_type',
    'name',
    'title',
    'placard',
    'origin_story',
    'trauma',
    'hopes_and_fears',
    'opinion_of_owner',
)


# --- The call ------------------------------------------------------------------------


def generate_biography(
    image_bytes: bytes,
    mime_type: str,
    hints: BiographyHints,
    prompt: SystemPrompt | None = None,
) -> BiographyResult:
    """`prompt` overrides the active SystemPrompt (used to try a version before activating it)."""
    if not settings.GEMINI_API_KEY or not settings.GEMINI_MODEL:
        raise GenerationFailed('GEMINI_API_KEY or GEMINI_MODEL is not set in .env')

    if prompt is None:
        prompt = SystemPrompt.active()

    client = genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options=types.HttpOptions(timeout=TIMEOUT_SECONDS * 1000),
    )
    config = types.GenerateContentConfig(
        system_instruction=prompt.text if prompt else DEFAULT_SYSTEM_PROMPT,
        response_mime_type='application/json',
        response_schema=GeminiBiography,
        temperature=TEMPERATURE,
        # Creative writing doesn't need long reasoning; less thinking = faster and cheaper.
        thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW),
    )
    contents = [
        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        build_user_prompt(hints),
    ]

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL, contents=contents, config=config
            )
        except errors.APIError as error:
            raise GenerationFailed(f'Gemini API error {error.code}: {error.message}') from error
        except httpx.HTTPError as error:
            raise GenerationFailed(f'Network error talking to Gemini: {error!r}') from error

        biography = _parse(response)
        if biography is not None:
            break
        logger.warning('Gemini returned an unusable biography (attempt %s)', attempt)
    else:
        raise GenerationFailed(f'Gemini returned unusable JSON {MAX_ATTEMPTS} times')

    if not biography.is_object:
        raise NotAnObject(biography.rejection_reason, _usage(response), prompt)
    return _to_result(biography, _usage(response), prompt)


def _parse(response):
    """The parsed biography, or None if it's broken or missing fields."""
    biography = response.parsed
    if not isinstance(biography, GeminiBiography):
        # parsed is None when the JSON didn't match; try once more ourselves.
        try:
            biography = GeminiBiography.model_validate_json(response.text or '')
        except (ValidationError, ValueError):
            return None
    if biography.is_object:
        complete = all(getattr(biography, name).strip() for name in TEXT_FIELDS) and biography.rivals
        if not complete:
            return None
    return biography


def _to_result(biography, usage, prompt):
    def clip(name):
        # Never let a chatty model break a CharField limit.
        # The app's voice is lowercase; normalise once here rather than in every template.
        value = getattr(biography, name).strip().lower()
        max_length = Exhibit._meta.get_field(name).max_length
        return value[:max_length] if max_length else value

    return BiographyResult(
        **{name: clip(name) for name in TEXT_FIELDS},
        rivals=[
            {'name': rival.name.strip().lower(), 'reason': rival.reason.strip().lower()}
            for rival in biography.rivals[:2]
        ],
        model_name=settings.GEMINI_MODEL,
        usage=usage,
        prompt_version=prompt,
    )


def _usage(response):
    meta = response.usage_metadata
    if meta is None:
        return {}
    return {
        'input_tokens': meta.prompt_token_count or 0,
        'output_tokens': meta.candidates_token_count or 0,
        'thinking_tokens': meta.thoughts_token_count or 0,
    }
