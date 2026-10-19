# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primarily a portfolio piece: classmates, recruiters and friends looking at what the builder (Aydos) made while learning Django, usually on an iPhone, sometimes on a Mac. The look and feel matter more than heavy daily use. Secondary: the builder and friends actually photographing things around the house for a laugh.

## Product Purpose

You photograph one household object (a mug, a chair, a sock); Gemini identifies it and writes its fictional life story: name and title, origin story, a defining trauma, rivals, hopes and fears, and its opinion of you. Each story is saved as an exhibit in your private museum. Success: someone picks up their phone, snaps an object, and laughs at what it says about them within about 15 seconds.

## Positioning

The objects in your home have opinions about you, and the app lets them speak, specifically about what is visible in the photo (chips, stains, labels, surroundings), not generic jokes.

## Operating Context

Used one-handed on a phone, standing in a kitchen or bedroom, pointing the camera at an object; a generation takes about 10 seconds. Stories are reread and shown to friends in person or as screenshots.

## Capabilities and Constraints

- Django 5.2 server-rendered templates, plain CSS and vanilla JS, no frontend framework and no build step.
- Accounts (email + password), profile with optional display name and "about me" used in the opinion.
- Upload (camera or library, JPEG/PNG/WebP/HEIC, 10 MB), regenerate, rename (fix a wrong identification), delete.
- Museum grid of all exhibits is planned (Phase 7) but not built yet.
- Daily generation limit is planned (Phase 8).
- Must be installable to the iPhone home screen (web app manifest, icon, standalone display).
- Admin pages (/admin/) keep Django's default admin look; out of scope for the public redesign.

## Brand Commitments

- Name: Object Biographies.
- Voice: lowercase, texting-style, like a group chat ("ok who's next", "reroll the story"); an occasional emoji; casual but never cringe slang.
- The user explicitly wants an iOS / Apple-device feel with a Gen Z, casual, simple vibe, with transitions and moving parts, and it must not look AI-generated or templated.

## Evidence on Hand

- Real biographies come from Gemini at runtime; there are no testimonials, user counts, press or reviews, and none may be invented.
- Sample photos available locally for demos: macOS "/Library/User Pictures" (turntable, guitar, piano, drum, violin, etc.).

## Product Principles

1. The objects talk; the interface stays out of their way.
2. Fast and one-handed: snap, wait about 10 seconds, laugh.
3. Every story is about this exact object, never a generic joke.
4. Private by default: your museum is yours.

## Accessibility & Inclusion

Respect reduced motion (every animation has a calm fallback), keep text contrast readable in light and dark mode, and keep everything usable by keyboard and screen reader.
