# Object Biographies — Product Requirements Document

**Status:** Draft v1
**Owner:** Aydos
**Date:** 2026-10-18

---

## 1. Summary

Object Biographies is a web app where you photograph an everyday object (a chair, a mug, a sock) and the app writes its fictional life story: where it came from, its trauma, its rivals, and its honest opinion of you. Each biography is saved as an exhibit in your personal **Museum**, a gallery of your household's secret lives.

The project is a Django practice build. v1 covers the core loop (photo → identification → biography → museum) and user accounts.

## 2. Goals and non-goals

### Goals (v1)
- A user can sign up, log in and keep a private museum.
- A user can upload or take a photo and get a funny, specific biography in under ~15 seconds.
- Biographies feel like they're about *this* object (color, wear, setting in the photo), not a generic mug.
- Practice the Django fundamentals: models, auth, forms, file uploads, templates, static files, service layers, tests, settings and secrets.

### Non-goals (v1)
- Public museum links (one exhibit can be shared, see §6.7; a whole museum can't).
- Cross-object lore (objects that reference each other as rivals or friends).
- Native mobile app or SPA framework.
- Payments, social features, comments, likes.
- Production-scale infrastructure (cloud storage, task queues, CDN).

These are listed as candidates in §12, Future scope.

## 3. Target user

Someone who wants a quick laugh and a collection to scroll through and show friends in person. Mostly on a phone, standing in their kitchen, pointing the camera at a kettle.

## 4. User stories

| # | As a… | I want to… | So that… |
|---|-------|-----------|----------|
| U1 | visitor | sign up with email and password | I get my own museum |
| U2 | user | log in and out | my museum stays private |
| U3 | user | take a photo with my phone camera or upload an image | I can add an object |
| U4 | user | get a biography generated for that object | I can read its secret life |
| U5 | user | see my museum as a grid of exhibits | I can browse my collection |
| U6 | user | open an exhibit and read the full biography | I can enjoy and reread it |
| U7 | user | regenerate a biography I don't like | I can get a better story |
| U8 | user | rename an object if the AI misidentified it | the story is about the right thing |
| U9 | user | delete an exhibit | I can curate my museum |
| U10 | user | optionally write a short "about me" | the object's opinion of me can be more personal |
| U11 | user | send an exhibit to friends on Telegram, Messages or anywhere else | they can laugh at it too |
| U12 | user | download an exhibit as a PDF | I can keep, print or send the story as a file |

## 5. Core user flow

```
Landing page ──► Sign up / Log in ──► My Museum (grid)
                                         │
                                         ▼
                                 "Add an object" page
                          (camera capture or file upload)
                                         │
                                         ▼
                        Loading state: "Interviewing your mug…"
                                         │
                                         ▼
                        Exhibit detail page (photo + biography)
                     [Regenerate] [Rename object] [Delete] [Back to museum]
```

## 6. Functional requirements

### 6.1 Accounts
- FR-1: Sign up, log in, log out and password reset use Django's built-in `django.contrib.auth`. Users log in with **email + password**: a custom `accounts.User` model with email as the login field and no username. Emails are stored lowercased and matched case-insensitively.
- FR-2: Every museum and exhibit view requires login (`LoginRequiredMixin` / `@login_required`).
- FR-3: Users can only see, edit or delete their own exhibits. Requesting someone else's exhibit returns 404, not 403, so its existence isn't revealed.
- FR-4: A profile page has an optional display name and an optional "about me" (max 300 chars) that goes into the prompt.

### 6.2 Photo capture and upload
- FR-5: The upload form uses `<input type="file" accept="image/*">` with no `capture` attribute, so phones offer both "Take Photo" and "Photo Library", and desktops open a file picker. (`capture` would force the camera and hide the library.)
- FR-6: Accepted formats: JPEG, PNG, WebP, HEIC (via `pillow-heif`). Max upload 10 MB. Every upload is stored as a re-encoded JPEG.
- FR-7: The server validates that the file really is an image (Pillow `verify()`), not just that it has the right extension.
- FR-8: Before storage and before sending to Gemini, the image is resized so its longest side is at most 1600 px, and EXIF data is stripped (it may contain GPS location).
- FR-9: The client shows an image preview before submitting (vanilla JS `URL.createObjectURL`).

### 6.3 Object recognition and biography generation
- FR-10: One Gemini multimodal call per biography. The image and prompt go in; structured JSON comes out (see §8).
- FR-11: If Gemini can't find a clear single object (blurry, a person, a landscape), it returns `is_object: false` with a reason, and the user sees a friendly "That doesn't look like an object we can interview. Try again." message. No exhibit is saved.
- FR-12: Photos of people are refused: the app writes biographies of objects, not humans.
- FR-13: The biography contains these sections:
  - **Name & title** (e.g. "Gerald, Mug of the Third Shelf")
  - **Origin story**: where it was made and how it got here
  - **Defining trauma**: one formative bad experience
  - **Rivals**: one or two invented nemeses (the dishwasher, the cat, the newer mug)
  - **Hopes & fears**
  - **Opinion of you**: a short, cheeky but never cruel judgment of the owner
  - **Museum placard**: a one-line summary for the gallery card
- FR-14: The prompt instructs the model to use visible details from the photo (chips, stains, color, surroundings) so stories feel specific.
- FR-15: Tone is PG-13: playful, dramatic, absurd. No slurs, sexual content, or genuinely hurtful remarks about the user.
- FR-16: **Regenerate** produces a new biography for the same photo and object name. Only the latest version is kept in v1.
- FR-17: **Rename** lets the user correct the object type (e.g. "it's a vase, not a mug") and regenerates using the corrected name as a hint.

### 6.4 Museum
- FR-18: The museum page shows a responsive grid of exhibit cards: thumbnail, object name, placard line, date added. Newest first.
- FR-19: Paginated at 24 per page (Django `Paginator`).
- FR-20: Empty state: "Your museum is empty. Your objects are waiting to be heard." plus an "Add an object" button.
- FR-21: The exhibit detail page shows the full photo and every biography section.
- FR-22: Delete asks for confirmation and removes both the database row and the image file.

### 6.5 Limits
- FR-23: Each user gets 5 interviews per day (a new exhibit, a reroll or a rename each count as one), to protect the API budget. "Today" is the calendar day in Uzbekistan time (Asia/Tashkent). Only calls Gemini answered count (stories and "not an object" refusals); failures on Google's side don't. Staff accounts are not limited. The upload page shows what's left as five dots; at zero it says to come back tomorrow, and the limit is checked before Gemini is called. `DAILY_GENERATION_LIMIT` in settings. Paid extra interviews (credits + Stripe) are a later phase.

### 6.6 Admin
- FR-24: Django admin at `/admin/` (staff only) lists users, profiles, exhibits (with image thumbnails, search and filters) and generation logs.
- FR-25: The system prompt is edited in the admin (Museum → System prompts), not in code. Every text edit is saved as a new version; exactly one version is active (enforced by a database constraint) and is used for every new biography. Versions can be activated with an admin action; the active one can't be deleted. Each exhibit records the prompt version that wrote it. With no active version, the default prompt in `museum/prompts.py` is used. `try_biography --prompt N` tries a version before activating it.

### 6.7 Sharing
- FR-26: Exhibits are private until the owner makes a link (the "share or save as pdf" sheet on the exhibit page). The link is `/s/<token>/` with a random 22-character token, readable by anyone who has it, without logging in. It shows that one exhibit's story (including the opinion of its owner) and nothing else: no owner name or email, no buttons to change it.
- FR-27: The owner can delete the link. The old link (page, photo and PDF) is a 404 from then on; sharing again makes a new link. Staff can turn links off in the admin.
- FR-28: The sheet sends the link to Telegram, Messages (SMS), the phone's own share sheet (any installed app), or copies it. Link previews get a title, the placard and the photo (Open Graph tags; the photo is served at a stable address, `/s/<token>/photo.jpg`).
- FR-29: Every exhibit can be downloaded as a PDF, by its owner always and by visitors while it is shared: a cover in its aura colour with the name, title, photo and placard, then every section. On phones that can share files, "send the pdf" hands the file to the share sheet.
- FR-30: Shared pages, photos and PDFs send `X-Robots-Tag: noindex, nofollow`: a link is for the people it was sent to, not for search engines.

## 7. Non-functional requirements

| Area | Requirement |
|------|-------------|
| Performance | Generation completes in ≤15 s at p90; page loads ≤1 s locally |
| Mobile | Usable at 360 px wide; camera capture works on iOS Safari and Android Chrome |
| Security | CSRF on all forms; API key only in `.env`, never committed; user-scoped querysets everywhere; uploaded files never executed or served from a guessable path outside `MEDIA_ROOT` |
| Privacy | EXIF stripped; images are only sent to Gemini and nowhere else |
| Reliability | A Gemini timeout or error shows a retry message; no half-saved exhibits |
| Accessibility | Images have alt text (the object name); forms have labels; good color contrast |
| Testability | Gemini client is wrapped in a service so tests can mock it; no real API calls in tests |

## 8. AI design (Gemini)

### 8.1 SDK and model
- SDK: the official `google-genai` Python package.
- Model: a current **Gemini Flash** multimodal model (fast and cheap), set by `GEMINI_MODEL` in settings so it's easy to swap. Pick the latest stable Flash model at build time.
- Key: `GEMINI_API_KEY` loaded from `.env` via `django-environ` or `python-dotenv`.

### 8.2 Structured output
Use Gemini's JSON mode with a response schema, so the output parses straight into the model fields:

```json
{
  "is_object": true,
  "rejection_reason": null,
  "object_type": "ceramic mug",
  "name": "Gerald",
  "title": "Mug of the Third Shelf",
  "placard": "Survived three moves and one terrible latte.",
  "origin_story": "…",
  "trauma": "…",
  "rivals": [{"name": "The Dishwasher", "reason": "…"}],
  "hopes_and_fears": "…",
  "opinion_of_owner": "…"
}
```

### 8.3 Prompt outline
- **System:** "You are the curator of a museum of household objects' secret lives. Write a dramatic, funny, specific biography…" plus tone rules (FR-15) and the people refusal (FR-12).
- **User content:** the image, plus optional hints: corrected object name (FR-17), owner display name and "about me" (FR-4).
- Length target: 250–400 words across all sections.
- Temperature around 1.0 for variety, so regenerate actually produces something different.

### 8.4 Service layer
`museum/services/gemini.py` exposes one function:

```python
def generate_biography(image_bytes: bytes, mime_type: str, hints: BiographyHints) -> BiographyResult: ...
```

Views call this function and never touch the SDK directly. Tests mock it.

## 9. Technical design

### 9.1 Stack
- **Backend:** Python 3.12 (installed with `uv`), Django 5.2 LTS
- **Database:** SQLite (v1)
- **Frontend:** Django templates + plain HTML, CSS and vanilla JavaScript. No frameworks, no build step.
- **Images:** Pillow (validation, resize, EXIF strip)
- **Storage:** local `MEDIA_ROOT` in v1
- **AI:** Google Gemini via `google-genai`

### 9.2 Project layout
```
object-biographies/
├── manage.py
├── .env.example
├── requirements.txt
├── config/                 # settings, urls, wsgi
├── accounts/               # signup, profile (display name, about me)
├── museum/                 # Exhibit model, views, templates
│   ├── services/
│   │   ├── gemini.py       # Gemini call + schema
│   │   └── images.py       # validate, resize, strip EXIF
│   ├── templates/museum/
│   └── tests/
├── templates/              # base.html, auth templates
└── static/
    ├── css/main.css
    └── js/upload.js        # preview, loading state
```

### 9.3 Data model

**Profile** (one-to-one with `User`)
| Field | Type |
|-------|------|
| user | OneToOne → User |
| display_name | CharField(50), blank |
| about_me | TextField(300), blank |

**Exhibit**
| Field | Type | Notes |
|-------|------|-------|
| owner | FK → User | indexed; every query filters on it |
| image | ImageField | `upload_to="exhibits/%Y/%m/"`, UUID filename |
| object_type | CharField(100) | from AI or user rename |
| name | CharField(100) | e.g. "Gerald" |
| title | CharField(200) | |
| placard | CharField(255) | |
| origin_story | TextField | |
| trauma | TextField | |
| rivals | JSONField | list of `{name, reason}` |
| hopes_and_fears | TextField | |
| opinion_of_owner | TextField | |
| model_name | CharField(100) | which Gemini model wrote it |
| created_at / updated_at | DateTimeField | |

**GenerationLog** (for the daily limit)
| Field | Type |
|-------|------|
| user | FK → User |
| created_at | DateTimeField, indexed |
| success | BooleanField |

### 9.4 URLs
| URL | View | Method |
|-----|------|--------|
| `/` | Landing (redirects to museum if logged in) | GET |
| `/accounts/signup/` | Sign up | GET/POST |
| `/accounts/login/`, `/accounts/logout/` | Django auth | GET/POST |
| `/accounts/profile/` | Edit profile | GET/POST |
| `/museum/` | Museum grid | GET |
| `/museum/new/` | Upload + generate | GET/POST |
| `/museum/<id>/` | Exhibit detail | GET |
| `/museum/<id>/regenerate/` | Regenerate | POST |
| `/museum/<id>/rename/` | Rename + regenerate | POST |
| `/museum/<id>/delete/` | Delete (confirm page) | GET/POST |
| `/museum/<id>/share/`, `/museum/<id>/unshare/` | Make or delete the public link | POST |
| `/museum/<id>/pdf/` | The owner's PDF | GET |
| `/s/<token>/` | Shared exhibit (public) | GET |
| `/s/<token>/photo.jpg`, `/s/<token>/story.pdf` | Its photo and PDF (public) | GET |

### 9.5 Request handling
v1 calls Gemini synchronously inside the POST request. It's simple and fine for a single user locally. The JS shows a loading overlay ("Interviewing your object…") and disables the submit button so the user can't double-submit. Moving to a background task queue is future scope.

## 10. Error handling

| Case | Behavior |
|------|----------|
| Not an image / too large | Form error, nothing saved |
| No clear object or a person in the photo | Friendly rejection message, nothing saved |
| Gemini timeout or 5xx | "The object is being shy. Try again." Nothing saved; logged |
| Malformed JSON from Gemini | One automatic retry, then the same error message |
| Daily limit reached | Message saying when the limit resets |
| Missing `GEMINI_API_KEY` | Clear error at startup in development |

## 11. Milestones

| # | Milestone | Done when |
|---|-----------|-----------|
| M1 | Project setup | Django project runs, `.env` loading works, base template and CSS exist |
| M2 | Accounts | Sign up, log in, log out and profile all work, with tests |
| M3 | Upload pipeline | Image validated, resized, EXIF stripped, stored; preview JS works |
| M4 | Gemini service | `generate_biography` returns parsed results; covered by mocked tests |
| M5 | Exhibits | Create, detail, regenerate, rename, delete, with ownership tests |
| M6 | Museum grid | Responsive grid, pagination, empty state |
| M7 | Polish | Loading states, error messages, daily limit, mobile camera check on a real phone |

## 12. Future scope (not v1)
- **Cross-object lore:** new biographies reference existing exhibits as rivals, friends or exes; a "relationships" view.
- **Public museum links:** share a whole museum, not just one exhibit; a designed preview image instead of the photo.
- **Biography history:** keep old versions when regenerating.
- **Themes / genres:** noir, Shakespearean, nature documentary narrator.
- **Voice narration** of biographies (TTS).
- **Rooms:** group exhibits by kitchen, bedroom, office.
- **Deployment:** Postgres, S3-compatible storage, background tasks (Celery or Django-Q), a hosted demo.

## 13. Success metrics (personal project)
- The full loop works end-to-end on a phone.
- At least 8 of 10 test photos produce a biography that clearly references a visible detail of the object.
- The test suite passes without network access.
- Museum of 20+ exhibits loads quickly and looks good.

## 14. Open questions
1. ~~Login with username or email?~~ **Decided:** email + password (see FR-1).
2. ~~Daily limit?~~ **Decided:** 5 per day (see FR-23).
3. Keep uploaded photos forever, or auto-delete images after N days for privacy?
4. Should "Opinion of you" use the about-me text by default, or should that be a toggle per generation?
