---
name: Object Biographies
description: Household objects tell their own life stories, one drenched colour slide at a time.
colors:
  grape: "#5b2bff"
  pink: "#ff2e7e"
  lime: "#c8f031"
  orange: "#ff6a13"
  pool: "#1fa2ff"
  butter: "#ffd43b"
  mint: "#2be0a0"
  midnight: "#111111"
  ink-white: "#ffffff"
  ink-black: "#111111"
  card: "#ffffff"
  card-ink: "#111111"
  card-ink-2: "rgba(17, 17, 17, 0.6)"
  card-line: "rgba(17, 17, 17, 0.12)"
  card-dark: "#1c1c1e"
  card-ink-dark: "#ffffff"
  card-ink-2-dark: "rgba(235, 235, 245, 0.6)"
  card-line-dark: "rgba(255, 255, 255, 0.12)"
  danger: "#e5133a"
  danger-dark: "#ff4d6a"
  success: "#19b35b"
  typing-grey: "#8e8e93"
  backdrop: "rgba(0, 0, 0, 0.45)"
typography:
  display:
    fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", system-ui, sans-serif'
    fontSize: "clamp(3.5rem, 21vw, 6rem)"
    fontWeight: 900
    lineHeight: 0.92
    letterSpacing: "-0.04em"
  headline:
    fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", system-ui, sans-serif'
    fontSize: "clamp(2.4rem, 12vw, 4rem)"
    fontWeight: 800
    lineHeight: 0.98
    letterSpacing: "-0.035em"
  title:
    fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", system-ui, sans-serif'
    fontSize: "28px"
    fontWeight: 900
    lineHeight: 1.05
    letterSpacing: "-0.035em"
  lead:
    fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", system-ui, sans-serif'
    fontSize: "clamp(1.25rem, 5vw, 1.65rem)"
    fontWeight: 600
    lineHeight: 1.32
    letterSpacing: "-0.02em"
  message:
    fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", system-ui, sans-serif'
    fontSize: "clamp(1.2rem, 4.8vw, 1.5rem)"
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: "-0.02em"
  body:
    fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", system-ui, sans-serif'
    fontSize: "17px"
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: "-0.015em"
  button:
    fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", system-ui, sans-serif'
    fontSize: "18px"
    fontWeight: 800
    letterSpacing: "-0.02em"
  tag:
    fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", system-ui, sans-serif'
    fontSize: "15px"
    fontWeight: 800
    letterSpacing: "-0.015em"
  label:
    fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", system-ui, sans-serif'
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.35
    letterSpacing: "-0.015em"
  field-label:
    fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", system-ui, sans-serif'
    fontSize: "13px"
    fontWeight: 600
    letterSpacing: "-0.015em"
rounded:
  capsule: "999px"
  circle: "50%"
  viewfinder: "34px"
  print: "30px"
  sheet: "28px"
  bubble: "26px"
  card: "22px"
  banner: "20px"
  notice: "18px"
  tile: "10px"
  tail: "8px"
  focus: "6px"
  segment: "2px"
spacing:
  tight: "8px"
  bar-inset: "12px"
  row: "12px"
  gutter: "20px"
  stack: "22px"
  block: "28px"
  split: "56px"
components:
  button-capsule:
    backgroundColor: "{colors.ink-white}"
    textColor: "{colors.grape}"
    typography: "{typography.button}"
    rounded: "{rounded.capsule}"
    padding: "0 28px"
    height: "56px"
  button-capsule-light-field:
    backgroundColor: "{colors.ink-black}"
    textColor: "{colors.pink}"
    typography: "{typography.button}"
    rounded: "{rounded.capsule}"
    padding: "0 28px"
    height: "56px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.ink-white}"
    typography: "{typography.button}"
    rounded: "{rounded.capsule}"
    padding: "0 28px"
    height: "56px"
  button-ghost-tinted:
    backgroundColor: "color-mix(in srgb, #ffffff 13%, transparent)"
    textColor: "{colors.ink-white}"
    typography: "{typography.button}"
    rounded: "{rounded.capsule}"
    padding: "0 28px"
    height: "56px"
  button-danger:
    backgroundColor: "{colors.danger}"
    textColor: "{colors.ink-white}"
    typography: "{typography.button}"
    rounded: "{rounded.capsule}"
    padding: "0 28px"
    height: "56px"
  button-round:
    backgroundColor: "{colors.ink-white}"
    textColor: "{colors.grape}"
    rounded: "{rounded.circle}"
    size: "38px"
  button-round-quiet:
    backgroundColor: "color-mix(in srgb, #ffffff 16%, transparent)"
    textColor: "{colors.ink-white}"
    rounded: "{rounded.circle}"
    size: "38px"
  app-bar:
    backgroundColor: "color-mix(in srgb, #5b2bff 55%, rgba(255, 255, 255, 0.25))"
    textColor: "{colors.ink-white}"
    rounded: "{rounded.capsule}"
    height: "52px"
    padding: "0 7px 0 14px"
  chip-soft:
    backgroundColor: "color-mix(in srgb, #ffffff 13%, transparent)"
    textColor: "{colors.ink-white}"
    typography: "{typography.tag}"
    rounded: "{rounded.capsule}"
    padding: "7px 14px"
  chip:
    backgroundColor: "{colors.ink-white}"
    textColor: "{colors.grape}"
    typography: "{typography.tag}"
    rounded: "{rounded.capsule}"
    padding: "7px 14px"
  card-grouped:
    backgroundColor: "{colors.card}"
    textColor: "{colors.card-ink}"
    rounded: "{rounded.card}"
  card-row:
    textColor: "{colors.card-ink}"
    typography: "{typography.body}"
    padding: "12px 18px"
    height: "52px"
  field-label:
    textColor: "{colors.card-ink-2}"
    typography: "{typography.field-label}"
  glyph-tile:
    backgroundColor: "{colors.grape}"
    textColor: "{colors.ink-white}"
    rounded: "{rounded.tile}"
    size: "32px"
  progress-segment:
    backgroundColor: "{colors.ink-white}"
    rounded: "{rounded.segment}"
    height: "4px"
  print:
    backgroundColor: "{colors.ink-white}"
    rounded: "{rounded.print}"
    padding: "7px"
    width: "min(68vw, 340px)"
  bubble:
    backgroundColor: "{colors.ink-white}"
    textColor: "{colors.ink-black}"
    typography: "{typography.message}"
    rounded: "{rounded.bubble}"
    padding: "14px 18px"
  vs-badge:
    backgroundColor: "{colors.ink-black}"
    textColor: "{colors.lime}"
    rounded: "{rounded.tile}"
    padding: "3px 10px"
  placard:
    backgroundColor: "{colors.orange}"
    textColor: "{colors.ink-black}"
    rounded: "{rounded.print}"
    padding: "20px"
    width: "440px"
  banner:
    backgroundColor: "color-mix(in srgb, #ffffff 82%, transparent)"
    textColor: "{colors.card-ink}"
    rounded: "{rounded.banner}"
    padding: "13px 16px"
  sheet:
    backgroundColor: "{colors.card}"
    textColor: "{colors.card-ink}"
    rounded: "{rounded.sheet}"
    padding: "18px 20px 26px"
  alert:
    backgroundColor: "{colors.card}"
    textColor: "{colors.card-ink}"
    rounded: "{rounded.sheet}"
    padding: "24px 20px 20px"
    width: "min(320px, calc(100% - 40px))"
  viewfinder:
    backgroundColor: "color-mix(in srgb, #ffffff 8%, #111111)"
    rounded: "{rounded.viewfinder}"
    height: "clamp(280px, 50svh, 560px)"
  shutter:
    backgroundColor: "{colors.ink-white}"
    rounded: "{rounded.circle}"
    size: "84px"
---

# Design System: Object Biographies

## Overview

**Creative North Star: "The Recap"**

Every screen is one drenched colour taken from a closed ramp of eight, each colour carrying its own ink, and each screen says one thing. An object's story plays as a run of full-height colour slides: its name, where it came from, its trauma, its beef, its hopes and fears, a text message to its owner, and a closing summary card. It reads like a year-in-review recap or a Stories reel. The type does the talking. Heavy, lowercase, tightly tracked SF Pro is set big enough to fill a phone. The chrome around it borrows directly from iOS: a Liquid Glass bar, Stories progress segments, grouped white cards, bottom sheets and centred alerts. Because the chrome is familiar, it stays out of the object's way.

Density is deliberately low. A screen holds one statement, one supporting line, and at most one physical thing: a photo print, a message bubble or a placard. Forms and dialogs are the one change of material. They sit on iOS grouped-card white, or near-black in dark mode, and that card material is the only surface that follows the system colour scheme. The colour fields stay the same in light and dark.

Motion is part of the identity. Arrivals spring past their mark and settle, exits are quick, and colour changes ease out. On the landing page, the next colour wipes in as a circle from wherever the visitor tapped, and each piece of chrome changes colour as the circle reaches it. With reduced motion, all the colour stays and all the travel goes.

**Key Characteristics:**
- One drenched field per screen from an eight-colour ramp; each field brings its own ink.
- Giant heavy lowercase type, left-aligned, tracked tighter as it grows.
- Actions invert the field: ink-filled capsules and circles with field-coloured labels.
- iOS materials: a glass app bar and banners, grouped white cards, bottom sheets, centred alerts.
- Object photos are physical prints: a white border, big rounded corners, a slight tilt and a deep soft shadow.
- Springy arrivals with about 16% overshoot, fast eased exits, circular colour wipes.
- No square corners anywhere; the smallest radius is the 2px on progress segments.

## Colors

The palette is a closed ramp of eight flat fields: seven saturated hues plus midnight. Each field is paired with a black or white ink, and one neutral card material handles forms and dialogs. Display names are the project's own aura names.

### Primary
- **Grape Soda** (#5b2bff): the house field. Default body field, browser and status-bar theme colour, manifest background, app icon ground, login page, and the landing recap's opening slide. White ink (#ffffff); secondary ink is white at 84%.

### Secondary
The rest of the ramp, in its fixed order. An exhibit's recap starts at its aura (the photo's dominant hue, snapped to the nearest field) and walks forward through this order, so no two slides in a row share a colour.
- **Hot Pink** (#ff2e7e): sign-up page; the landing recap's counting slide. Black ink; secondary ink black at 80%.
- **Highlighter** (#c8f031): the landing recap's beef slide. Black ink; secondary at 76%.
- **Traffic Cone** (#ff6a13): the landing recap's opinion slide; the rename action's tile. Black ink; secondary at 80%.
- **Pool Day** (#1fa2ff): the whole password-reset flow; the share action's tile. Black ink; secondary at 80%.
- **Butter** (#ffd43b): appears only as a recap slide or an aura. Black ink; secondary at 76%.
- **Mint Gum** (#2be0a0): profile page and the password-saved page; the "add another" action's tile. Black ink; secondary at 76%.

### Tertiary
- **System Red** (#e5133a): destructive actions only. Delete capsule fill (always with a white label, in both modes), danger row text and tile, field errors, error banner icon, log out. On dark cards, red text lifts to **Soft Red** (#ff4d6a); red fills stay #e5133a.
- **Done Green** (#19b35b): the check icon on success banners, nothing else.

### Neutral
- **Midnight** (#111111): the eighth field. Upload camera, delete confirmation, the interview (loading) screen, landing's "how it works" band and final slide, and the closing card slide of every recap. It is also the aura given to low-saturation photos (white, grey and black objects). White ink; secondary white at 78%.
- **Ink White** (#ffffff) and **Ink Black** (#111111): the only two inks. Secondary ink is always the field's own ink at reduced opacity, never a third colour.
- **Card** (#ffffff, dark mode **Card Dark** #1c1c1e): iOS grouped material behind forms, sheets, alerts, banners and row actions.
- **Card Ink** (#111111 / #ffffff), **Card Ink 2** (rgba(17, 17, 17, 0.6) / rgba(235, 235, 245, 0.6)) and **Card Line** (rgba(17, 17, 17, 0.12) / rgba(255, 255, 255, 0.12)): card text; field labels and placeholders; 0.5px hairlines between rows.
- **Typing Grey** (#8e8e93): the three typing-indicator dots.
- **Backdrop** (rgba(0, 0, 0, 0.45)): the dim behind sheets and alerts, with a 4px blur.

### Named Rules
**The Paired Ink Rule.** A field never appears without its ink. Colour comes from a field class that sets the field, its ink and its secondary ink together, never from a bare background. Every tint on a field is that field's own ink mixed in at 8–35%, never a new colour.

**The One Field Rule.** One field drenches each screen, and the page, glass bar, progress segments and dock all take it. A second field appears only as an object sitting on the first (the placard, a row tile, the aura swatch) or during the 700ms of a colour wipe.

**The Closed Ramp Rule.** No colour exists outside the eight fields, the card material and system red and green. Photo colour never enters the UI directly; it is snapped to the nearest ramp hue first.

## Typography

**Display Font:** SF Pro Display, via the Apple system stack (with Helvetica Neue and system-ui as fallbacks)
**Body Font:** SF Pro Text, the same stack
**Label/Mono Font:** none; one family does everything. No webfont is loaded.

**Character:** a single family carries the whole hierarchy through weight and size alone. 900 shouts, 800 headings and actions, 600 supporting lines. Everything is lowercase and tracked tighter as it grows, so the screen reads like an iPhone talking in a group chat.

### Hierarchy
- **Display** (900, clamp(3.5rem, 21vw, 6rem), 0.92, -0.04em, balanced): the one statement on a slide or page head ("this is gerald.", "welcome back.", the object's name). On the opening slide it arrives word by word.
- **Headline** (800, clamp(2.4rem, 12vw, 4rem), 0.98, -0.035em, balanced): slide section titles ("the beef", "where it came from"), rival names, the upload heading, how-it-works steps.
- **Title** (900, 28px, 1.05, -0.035em): sheet titles. Siblings at the same weight: the placard name (30px, line-height 1) and the alert title (24px, -0.03em).
- **Lead** (600, clamp(1.25rem, 5vw, 1.65rem), 1.32, -0.02em, max 32ch, secondary ink, pretty wrapping): the supporting line under every statement, and the story paragraphs.
- **Message** (600, clamp(1.2rem, 4.8vw, 1.5rem), 1.35, -0.02em): the object's text-message bubble.
- **Body** (400, 17px, 1.4, -0.015em): base text. Inputs stay at 17px so iOS never zooms on focus.
- **Button** (800, 18px, -0.02em): capsule labels.
- **Tag** (800, 15px): chips. The story head and the brand use 16–17px at 800; bar links use 16px at 700.
- **Label** (400, 15px, 1.35, secondary ink): small print, hints, accepted file types.
- **Field Label** (600, 13px, card ink 2, lowercase): the label above each input in a grouped card.
- The interview screen has its own line (900, clamp(2.4rem, 11vw, 4.5rem), 0.95, -0.04em, max 13ch, centred). Counting numbers use tabular figures.

### Named Rules
**The Lowercase Rule.** Everything the reader sees is lowercase: the brand, buttons, labels, and the model's generated text, which templates lowercase before rendering. Field labels and form help also force lowercase. No uppercase, no title case, no small caps.

**The Tighten-As-It-Grows Rule.** Tracking runs from -0.015em at body size to -0.02em for lead, message and buttons, -0.035em for headlines and titles, and -0.04em at display size. Only the "vs" badge sits at 0. Positive letter-spacing is never used.

**The One Statement Rule.** Each slide or page head carries exactly one display or headline statement, left-aligned and balanced. Supporting copy steps straight down to Lead, with nothing in between.

## Layout

Mobile first and single-column. A fixed glass bar floats 10px below the top safe area. It is 52px tall, inset 12px from each side, and at most 924px wide (the column plus 24px). Below it, the progress segments (bar top + 62px), the story head (bar top + 78px) and all slide content share one 900px column with a 20px gutter. Pages use a 1100px frame with bar top + 86px of top padding and 48px at the bottom. Account forms narrow to 480px, and recaps run flush to the edges.

Slides are at least one full small-viewport height (100svh), with content centred vertically. Top padding is bar top + 132px to clear the chrome; bottom padding is 64px, or 150px on landing to clear the dock. The exhibit recap scroll-snaps slide by slide (proximity). The landing recap locks to a single 100svh stage and stacks its slides in place.

Rhythm: 8px between chips, banners and thread parts; 12px between rows and between stacked buttons; 22px between elements on a slide (and above a button row); 26px between rivals; 28px below page heads and before a second card; 40px between how-it-works steps.

Breakpoints: at **640px** the bottom sheet becomes a centred 480px card with all corners rounded and no grabber. At **820px** the opening slide splits: text on the left, and the print in a 360px second column with a 56px gap, spanning four rows. How-it-works becomes three columns at the same point. Other caps: banners 420px, placard and the actions card 440px, camera 520px, bubble 560px.

**The One Column Rule.** The bar, progress segments, story head and slide content share the same 900px column and left edge, so the chrome and the statement line up at every width.

## Elevation & Depth

A hybrid system. The fields are flat; depth comes from three sources. Floating chrome uses glass (backdrop blur over a translucent field). Physical things (prints, cards, bubbles, the placard) cast soft black drop shadows. Forms and dialogs switch to the card material. Shadows are never coloured and never hard-offset, and fields never get borders.

### Shadow Vocabulary
- **Glass bar** (`box-shadow: inset 0 0 0 0.5px color-mix(in srgb, var(--ink) 22%, transparent), 0 8px 24px rgba(0, 0, 0, 0.12)`, with `backdrop-filter: blur(22px) saturate(170%)`): the app bar only.
- **Banner glass** (`box-shadow: 0 12px 32px rgba(0, 0, 0, 0.18)`, with `backdrop-filter: blur(24px) saturate(180%)` over card at 82%): flash messages.
- **Card** (`box-shadow: 0 18px 40px rgba(0, 0, 0, 0.14)`): grouped cards on a field. Inside a sheet it becomes a hairline, `inset 0 0 0 1px` in card line.
- **Bubble** (`box-shadow: 0 12px 30px rgba(0, 0, 0, 0.12)`): the object's message.
- **Print** (`box-shadow: 0 22px 50px rgba(0, 0, 0, 0.28), 0 4px 10px rgba(0, 0, 0, 0.12)`): photo prints, which have a contact shadow plus a lift shadow.
- **Interview photo** (`box-shadow: 0 20px 44px rgba(0, 0, 0, 0.3)`): the bobbing photo on the loading screen.
- **Placard** (`box-shadow: 0 30px 60px rgba(0, 0, 0, 0.4)`): the summary card on midnight; the deepest shadow in the system.
- **Ink ring** (`box-shadow: 0 0 0 2px var(--ink)`): around the story-head avatar and the aura swatch. The placard photo uses a white ring (`0 0 0 4px #fff`).

### Named Rules
**The Physical Object Rule.** Big shadows (0.28–0.4 opacity, 44–60px blur) belong only to things meant to feel like objects on a table: prints, the placard and the interview photo. UI material stays at 0.12–0.18.

**The Glass Is Chrome Rule.** Backdrop blur belongs to floating chrome: the app bar, banners and the modal backdrop. Content surfaces (cards, sheets, alerts, bubbles) are opaque.

## Shapes

Everything is rounded, from 2px progress segments to full capsules, and nothing has a square corner. There are three families:
- **Capsules and circles** for anything tappable (999px, 50%).
- **Large soft rectangles** for surfaces: card 22px, bubble 26px with an 8px tail corner at the bottom left, sheets and alerts 28px, print and placard 30px, viewfinder 34px.
- **Small 10px tiles** for row icons and the "vs" badge.

Inner radii follow the outer ones: a print's photo is 23px inside a 30px frame with a 7px white border.

Rotation is part of the form language. Prints sit at -5deg, the placard's photo at -4deg, the placard at -1.5deg, and the "vs" badge at -6deg. Entrances start further rotated and spring back to these resting angles. The viewfinder is framed by four 38px corner brackets: a 4px ink stroke with a 14px outer radius, inset 22px, and drawing in to 30px on hover or focus. On phones, sheets round only their top corners (28px) and carry a 40×5px grabber.

## Components

### Buttons
Fat iOS capsules that invert the field.
- **Shape:** full capsule (999px), at least 56px tall, padding 0 28px, Button type.
- **Primary:** ink fill with a field-coloured label: a white capsule on grape and midnight, a black capsule on the six light fields. The block variant runs full width. Button rows stack in a 12px grid, 22px below the form.
- **Hover / Focus:** grows to scale(1.02) on hover. Press shrinks to scale(0.95) in 0.1s, and release springs back over 0.3s. Disabled is 45% opacity with no transform. Focus is the global ring: 3px solid ink, 3px offset, 6px radius.
- **Ghost:** on pages, transparent with a 2.5px inset ink ring. In the landing dock it drops the ring for an ink 13% tint and shrinks to its content. Inside sheets and alerts it becomes a card-ink 9% tint.
- **Danger:** System Red fill with a white label, in both modes.
- **On cards:** inside sheets and alerts, capsules take card ink on card: black on white, white on #1c1c1e.
- **Round:** a 38px ink circle with a field-coloured glyph or initial (16px, 800), pressing to scale(0.88). The quiet variant is an ink 16% tint. Used for add, the profile initial, and the landing pause/play.

### Chips
- **Style:** the soft chip is an ink 13% tint with an ink label (Tag type), padding 7px 14px, as a capsule. It carries the 14px aura swatch: the snapped field colour inside a 2px ink ring.
- **State:** a solid variant (ink fill, field label) is defined in the stylesheet but is not rendered by any current template.

### Cards / Containers
- **Corner Style:** 22px for grouped cards; 30px for the placard.
- **Background:** the card material for grouped cards; the exhibit's first field for the placard, which sits on midnight.
- **Shadow Strategy:** Card shadow on fields, a hairline inset inside sheets, and the Placard shadow for the placard (see Elevation & Depth).
- **Border:** none. Rows are separated by 0.5px card-line hairlines inset 18px from the left, in the iOS style. The placard's facts sit under a 2px ink-22% rule.
- **Internal Padding:** rows are at least 52px tall, padding 12px 18px, gap 12px. The placard has 20px padding and an 18px gap. Stacked cards sit 16px apart.
- **Row action:** a whole-row button or link at weight 700, tinting card ink 6% on hover and press over 0.15s. It has a leading 32px tile (10px radius, ramp-colour fill, 18px icon at 2.4 stroke) and a trailing chevron at 35% opacity. Danger rows use red text and a red tile.
- **Placard:** the summary card. An 84px photo (20px radius, -4deg, white ring), the name in Title type at 30px, the one-line quote at 22px/700/1.25 (balanced), then a facts list: labels in secondary ink at 600, values at 800, right-aligned.

### Inputs / Fields
- **Style:** a label-above-input row inside a grouped card. The input has no border and no background, uses 17px Body type, and its caret is in card ink. The Field Label sits above; placeholders are card ink 2.
- **Focus:** the whole row tints card ink 5%. The input itself shows no ring.
- **Error / Disabled:** field errors are 14px/600 red text inside the row. Form-level errors sit in a separate card-material notice (18px radius, 14px 16px padding, red alert icon), 14px above the card. Help text is 14px lowercase secondary ink below the card. Upload errors are red text on a 16px-radius card notice.

### Navigation
- **Style:** the glass app bar. A fixed 52px capsule: field at 55% over white at 25%, blur 22px saturate 170%, a 0.5px ink hairline and a soft 8px/24px shadow.
- **Content:** on the left, the 30px brand mark and the name in lowercase at 17px/800, truncating. On the right, signed-in visitors get an ink round "+" and a quiet round initial. Signed-out visitors get a "log in" text link at 16px/700; on landing it moves into the dock.
- **States:** the bar recolours with the page field (background over 0.5s, ink over 0.3s, eased out). The phone's status bar follows the current field.

### Story Progress and Story Head
The Stories grammar that marks every recap.
- **Segments:** one per slide. Each is a 4px bar (2px radius) inside a 14px tap target, with 4px gaps; the track is ink 28% and the fill is ink. On landing, the current segment fills linearly over the 4.6s slide and pauses with the stage. On the exhibit page the segments are static, filled up to the current slide.
- **Story head:** a 32px round photo with a 2px ink ring, the name at 16px/800, and a note (the object type, or "example") at 600 in secondary ink. It stays on screen, so any screenshot still says whose story it is.

### Slides
The unit of the recap. A full-height field with a 22px content grid in the shared column.
- **Arrival:** display headings rise word by word (from 0.5em down, rotated 4deg). Reveal blocks rise from 36px below at 0.96 scale. Items stagger 60ms apart in reading order and spring over 0.9s.
- **Landing:** the stage autoplays every 4.6s. Tapping the right 70% goes forward and the left 30% goes back; a sideways swipe over 50px changes slide; holding for 220ms pauses. Each change wipes the next field in as a circle (700ms, eased out) from the tap point, or from the lower right by default. Autoplay pauses off-screen and in hidden tabs.
- **Exhibit:** vertical scroll or tap to advance. The page field crossfades (0.5s) as each slide crosses the middle of the viewport.

### Print
The object's photo as a physical print: a 7px white border, 30px radius, square, min(68vw, 340px) wide (360px in the split layout), resting at -5deg with the Print shadow. It arrives from -16deg at 0.7 scale. The exhibit's hero print continues the upload preview through a 0.6s shared-element page transition.

### Rivals
"The beef." Each rival is a Headline-size name led by a "vs" badge: ink fill, field text, 18px/900, 10px radius, -6deg. The reason follows in Lead. Rivals slide in alternately from ±70px with ±3deg of rotation, and the badge slams down from 2.4× scale at -24deg.

### Thread
The object texts its owner. A sender row (26px round photo, name at 14px/700 in secondary ink) sits above a typing indicator and the message, which share one spot. Three 9px grey dots bounce for 1.3s and leave; then the bubble lands at 1.45s from 0.6 scale with a 0.8s spring, growing from its bottom-left tail. The bubble is always white with #111111 text on any field and in any mode: 26px radius with an 8px tail corner, 14px 18px padding, max 560px.

### Banners
Flash messages styled as iOS notifications. Glass card pills sit just under the bar: max 420px, 20px radius, 15px/600, with a green check or red alert icon. They drop in from above with a 0.7s spring. Success banners leave on their own after 4.5s (plus 0.6s for each one after the first); error banners stay until tapped.

### Sheets and Alerts
Built on the native dialog element over the dimmed, blurred backdrop; tapping outside dismisses. Links that open a dialog keep their URL as a no-script fallback.
- **Sheet:** bottom-anchored with 28px top corners and a grabber. It slides up with a 0.55s spring. The body has a 16px gap and a Title.
- **Alert:** centred, 320px wide, 28px radius, centred text. A 24px/900 title and secondary text sit above stacked block buttons 10px apart. It scales down into place from 1.08 over 0.3s, eased out.

### Camera
The upload page.
- **Viewfinder:** midnight with 8% ink mixed in, 34px radius, clamp(280px, 50svh, 560px) tall, with the four corner brackets. The prompt is 20px/800 with a 44px camera icon. A chosen photo "develops" over 1.1s from an 18px blur, desaturated and brightened.
- **Shutter:** an 84px ring (5px ink border) around a 64px ink disc that presses to 0.82 in 0.08s and springs back. The label is 17px/800.

### Interview
The loading screen while a story is written. A full-screen overlay cycles through the seven hue fields every 1.7s, each with a new line that springs in from 40px below at 0.9 scale. The object's photo (150px, 6px white border, 28px radius) bobs between -6deg and 4deg over 2.4s, with the typing dots underneath.

### Dock
Landing's action bar, fixed to the bottom and safe-area aware. The field fades up behind it through a mask (solid to 55%, clear above). The primary capsule flexes to 340px max, and the tinted ghost sits beside it.

### Brand Mark and Icons
- **Mark:** a speech bubble with two eyes. The bubble is in ink and the eyes are in the field colour; the eyes blink every 6s. The app icon is the same mark in white on grape.
- **Icons:** inline SVG on a 24-unit grid, drawn at 22px with a 2px round stroke and no fill.

## Do's and Don'ts

### Do:
- **Do** set colour with a field class so the field, its ink and its secondary ink arrive together; tint with the field's own ink at 8% (viewfinder), 13% (soft chip, dock ghost), 16% (quiet round), 22% (hairlines) or 28% (progress track).
- **Do** walk the ramp in order (grape, pink, lime, orange, pool, butter, mint) starting from the exhibit's aura, and end every recap on midnight.
- **Do** give each screen one display-size statement: heavy, lowercase, left-aligned and balanced, with one Lead line under it.
- **Do** build actions as ink-filled capsules (56px) and circles (38px) with field-coloured labels that press to 0.95 and 0.88.
- **Do** put forms, sheets and alerts on the card material (#ffffff, or #1c1c1e in dark mode), with labels above inputs and 0.5px hairlines inset 18px.
- **Do** spring arrivals past their mark (about 16% overshoot) and use the ease-out curve for exits, fades and colour changes; stagger reveals 60ms apart.
- **Do** give every animation a reduced-motion state: no travel, no autoplay, 0.15s fades, and every colour change kept.
- **Do** treat object photos as prints: a white border, a large radius, a slight tilt and a deep soft shadow.

### Don't:
- **Don't** set a field colour without its ink, and don't put white ink on the six light fields (pink, lime, orange, pool, butter, mint).
- **Don't** introduce colours outside the ramp, the card material and system red and green; don't sample photo colours straight into the UI.
- **Don't** add gradients or textures to a field; the only gradient is the dock's mask, which fades the field into itself.
- **Don't** use uppercase, title case or positive letter-spacing.
- **Don't** centre the display statements on slides and page heads; only the interview line and the alert centre their big type.
- **Don't** use square corners or hard offset shadows; shadows are soft, black and fall downward.
- **Don't** put backdrop blur on content surfaces; glass is for the bar, the banners and the modal backdrop.
- **Don't** change the fields for dark mode; only the card material changes.
