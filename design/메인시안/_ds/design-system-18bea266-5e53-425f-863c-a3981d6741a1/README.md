# 박상익출장음식 · Design System

> 야외행사 이동밥차 · 제물상차림 전문
> 현장에서 직접 정성껏 차려드립니다

A design system for **박상익출장음식** — a one‑person Korean traditional catering business specialising in **제물상차림** (ritual ancestral‑rites table setting) and **이동밥차** (mobile food‑truck) service for outdoor ceremonies, clan rituals, workplace 시무식/고사, and group meals.

---

## 1 · Brand at a glance

| | |
|---|---|
| **상호 (business name)** | 박상익출장음식 |
| **대표 (owner)** | 박상익 |
| **업종 (category)** | 출장요리 / 이동밥차 / 제물상차림 |
| **연락처** | 010‑5353‑3477 |
| **핵심 슬로건** | 현장에서 직접 정성껏 차려드립니다 |
| **타겟 (referral targets)** | ① 묘지제사·시제·문중행사 주관자<br>② 사업장 시무식·고사 담당자<br>③ 야외행사·단체식사 필요한 분 |
| **언어** | 한국어 (100%) |

This is **not** a trendy modern restaurant brand. The visual world should feel like the **제물상** itself: dignified, hand‑arranged, ritually significant. Sincere effort (**정성**) is the central brand value — not convenience, not speed, not novelty.

---

## 2 · Sources used to build this system

The user provided:

* `uploads/upload_assets-1779489969948.pptx` — a **BNI Members Weekly 40's** referral profile card created in PowerPoint (1 slide, by SANGICK PARK). Contains: business‑card text, one **제물상 photograph** (extracted to `assets/jemulsang-hero.jpg`), the BNI chapter logo, and a generic financial stock image (discarded).
* Stated direction (from `questions_v2` responses): traditional 명조체 fonts, sage/camel/cream color direction, white + red emblem visual style.

There is **no codebase, no Figma file, no existing website, and no prior brand mark.** Everything in this system was authored from scratch, anchored by the photo and the referral copy.

---

## 3 · Manifest — what's in this folder

```
박상익출장음식/
├── README.md                    ← you are here
├── SKILL.md                     ← agent skill entry point (Claude Code compatible)
├── colors_and_type.css          ← all CSS variables: palette, type scale, spacing, motion
│
├── assets/
│   ├── logo-seal.svg            ← square 인장 stamp mark (red lacquer)
│   ├── logo-wordmark.svg        ← horizontal seal + wordmark + descriptor
│   ├── logo-stacked.svg         ← vertical lockup (covers, slide titles)
│   ├── jemulsang-hero.jpg       ← THE hero photo, full resolution, rotated upright
│   ├── jemulsang-square.jpg     ← 1800×1800 crop centred on the table
│   └── jemulsang-banner.jpg     ← 2400×800 letterbox crop for banners
│
├── preview/                     ← Design System tab cards (one swatch / specimen per file)
│
├── ui_kits/
│   └── website/                 ← marketing site recreation (index.html + JSX components)
│
├── slides/                      ← presentation template (TitleSlide, IntroSlide, ServiceSlide, …)
│
└── uploads/                     ← original source PPTX + extracted media (kept for reference)
```

---

## 4 · Content Fundamentals — how copy is written

The owner is a **첫 단독 사업주 같은 느낌의 1인 가게** — a one‑person family business, not a corporation. Copy must sound like 박상익 himself talking, not marketing.

### Tone & register
* **격식 있되 따뜻하게.** Formal Korean (하십시오체 / 합쇼체) for headlines and offerings; semi‑polite (해요체) is acceptable for short labels. Never banmal (반말).
* **자기를 낮춤.** The brand speaks of *itself* humbly ("정성껏 차려드립니다") and of the customer's occasion respectfully ("뜻깊은 자리에"). Never "we are the best" or "premium" superlatives.
* **No "we" voice.** Korean small businesses rarely use 저희; prefer the third person of the business name itself ("**박상익출장음식은** 30년 경력의…") or just verb‑first sentences with implied subject.

### Casing & punctuation
* Korean has no casing. **Don't introduce ALL CAPS Latin** anywhere — it reads as a Western interruption. Latin (e.g. "BNI") appears only in proper nouns.
* Use the **middle dot (·)** to separate list items inline: `이동밥차 · 제물상차림 · 야외행사`. This is far more 한식다운 than commas or slashes.
* Phone numbers: separate with middle dots or hyphens, never spaces: `010·5353·3477` or `010-5353-3477`.
* For ritual occasions, use the **★** star bullet sparingly — it was used in the original referral card and reads as warmly handmade.

### Vibe — words that fit / don't fit
**✅ Use freely:** 정성, 직접, 현장, 따뜻한, 손수, 뜻깊은, 모십니다, 차려드립니다, 30년 경력, 단체, 야외, 전문, 묘지제사, 시제, 문중행사, 시무식, 고사.
**🚫 Avoid:** 프리미엄, 럭셔리, 트렌디, 힙한, MZ, 솔루션, 플랫폼, 라이프스타일, 큐레이션. Avoid English loanwords whenever a 한자어 alternative exists.

### Emoji
**No emoji.** This is a ritual‑catering brand; emoji break the dignified tone instantly. The only decorative glyph allowed is **★** (referral star) and **·** (middle dot). Use unicode symbols sparingly: 「 」 for quoted dish names, ［ ］ for categories.

### Sample copy

> **Hero**
> 현장에서 직접 정성껏 차려드립니다
>
> 묘지제사 · 시제 · 문중행사부터 사업장 고사, 야외 단체식사까지
> 30년 손맛으로 모십니다.

> **Service card**
> ［제물상차림］
> 정성스레 차린 제물상을 묘지·문중·자택까지 직접 배송·진설해 드립니다.
> 사진의 24기 정식 차림 기준 · 별도 협의 가능

> **CTA**
> 전화로 문의 · 010‑5353‑3477
> *(SMS·카톡 가능, 평일 오전 8시–오후 8시)*

---

## 5 · Visual Foundations

> The whole brand should feel like a single sheet of **한지** laid on a wood table, with a **주칠 목기** placed on top. Restraint. Hand‑arrangement. A red stamp in one corner.

### 5.1 Color
Six core hues sampled from the 제물상 photograph itself. Cream paper, ink, two greens (the only colors NOT in the photo — borrowed from 단청 eaves to give the brand life), wood, and lacquer red.

| Role | Token | Hex | Usage |
|---|---|---|---|
| 한지 cream | `--hanji-100` | `#fbf7ef` | Default page bg |
| 먹 ink charcoal | `--ink-700` | `#2c2924` | Body text |
| 단청 pine | `--pine-700` | `#2e4a36` | Primary accent / CTAs |
| 애엽 sage | `--sage-500` | `#6b8458` | Secondary, supportive |
| 목재 wood | `--wood-500` | `#a8794a` | Tertiary warmth, dividers |
| 주칠 lacquer | `--jujube-700` | `#8b1d1d` | **Seal stamps, sacred emphasis only** |

**Critical rule:** 주칠 red is the *sacred* color. Never use it for ordinary CTAs, links, or decoration. It is reserved for the seal mark and for marking ritual/ceremonial items (제물상 service tier, 시무식 references). When red appears, it should feel like a stamp pressed into paper.

### 5.2 Typography
A **Myeongjo‑first** system — serif everywhere, sans only for UI controls and small labels.

| Family | Role | Notes |
|---|---|---|
| **Gowun Batang** | Display, H1, brand wordmark | Classical, almost carved‑stone weight at 700 |
| **Noto Serif KR** | H2–H4, body, longform | Modern Myeongjo, highly legible at body sizes |
| **Pretendard** | Buttons, captions, form labels, phone numbers, small UI | The only sans in the system |
| Noto Sans KR | Fallback for Pretendard | Loaded as a backstop |

**Tracking discipline.** Hangul at display sizes wants very tight tracking (`-0.04em`). Hangul at micro sizes (labels) wants generously wide tracking (`0.32em–0.42em`) — this evokes classical 한지 documents.

`word-break: keep-all` is set globally so Korean phrases never split mid‑word at line breaks.

### 5.3 Spacing & rhythm
Standard 4px scale (`4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 128`). Generous vertical breathing room at the section level — this is a contemplative brand. Inside cards, density can be relatively tight because Myeongjo body text needs the air to be at the *paragraph* level, not the line level.

### 5.4 Backgrounds
* **Default:** flat `--hanji-100` cream. No gradients on body backgrounds, ever.
* **Hero / cover moments:** full‑bleed `jemulsang-hero.jpg` with a soft dark overlay (`rgba(20,17,13,0.45)`) so cream type sits on top.
* **Section breaks:** subtle hand‑drawn 한지 textures are allowed (sparse fiber noise at 4–6% opacity). Drawn as inline SVG `<feTurbulence>` filters, not bitmap textures.
* **No repeating patterns.** No tiled wallpapers, no parallax. Single, intentional, photographic moments only.

### 5.5 Borders
* **Default:** `1px solid var(--border)` — a near‑invisible warm‑ink line.
* **Classical rules:** the brand uses the `<hr class="rule">` and `<hr class="rule-double">` patterns to separate dense sections, evoking a 한지 document. The double rule (two parallel hairlines) is the strongest divider in the system.
* No dashed borders. No dotted borders. No colored borders other than `--border` or `--rule`.

### 5.6 Corner radii
Mostly **square** (`0–4px`). Cards use `--radius-md` (6px). Pills/tags exist (`--radius-pill`) but are used sparingly. **Never** use `border-radius: 16px+` on large surfaces — it makes the brand feel like a SaaS app.

### 5.7 Shadows
Three quiet levels (`--shadow-sm/md/lg`). All shadows use warm ink (`rgba(45,41,36,…)`) — never neutral gray. The intent is "paper resting on wood," never "floating UI."

### 5.8 Animation
* **Easing:** `cubic-bezier(0.22, 0.61, 0.36, 1)` — a slow, restrained out‑curve. No bounces, no springs, no overshoot.
* **Durations:** `140 / 220 / 420ms`. Anything above 500ms feels like a slideshow transition, not UI.
* **Hover state:** opacity 0.85 OR a one‑level darker brand token. Never scale > 1.02. Never color‑shift to a new hue.
* **Press state:** translate Y by 1px OR opacity 0.7. No shrink animation.
* The brand should feel like ink soaking into paper, not like rubber buttons.

### 5.9 Transparency & blur
Use very rarely. The single sanctioned use is **hero photo overlays** (dark ink `rgba(20,17,13,0.40–0.55)`). Frosted glass (`backdrop-filter: blur`) is **not** part of this brand.

### 5.10 Cards
A "card" is a sheet of paper, not a chip. Default card:
* Background `--bg-surface` (`#ffffff`)
* `1px solid var(--border)`
* `--shadow-sm`
* Radius `--radius-md` (6px)
* Padding `--space-6` to `--space-8`

A "featured" card adds the double rule at top, like a 한지 letter heading.

### 5.11 Photography vibe
Warm, slightly under‑exposed, daylight, food‑in‑real‑rooms. No studio glam. No top‑down flat‑lay food‑mag style. The reference photograph is the standard: real wood, real tablecloth, real bowls, with the equipment of life (kettle, incense holder) included rather than cropped out.

---

## 6 · Iconography

### Primary approach: **Lucide**
The system uses **[Lucide Icons](https://lucide.dev)** (line, 1.5px stroke, rounded caps) via CDN. Lucide's restrained line style harmonises with the Myeongjo type — both are *drawn* rather than *filled*.

```html
<script src="https://unpkg.com/lucide@latest"></script>
<i data-lucide="phone"></i>
<script>lucide.createIcons();</script>
```

**Icon set used by this brand** (always thin / line style, color `currentColor` taking `--ink-700` or `--pine-700`):

| Concept | Lucide name |
|---|---|
| Phone / contact | `phone`, `phone-call` |
| Calendar / booking | `calendar`, `calendar-check` |
| Location / 현장 | `map-pin`, `tent` |
| Group / 단체 | `users` |
| Time / hours | `clock` |
| Truck / 이동밥차 | `truck` |
| Flame / 고사·향 | `flame` |
| Leaf / 나물 | `leaf` |
| Star / referral | `star` (filled, 주칠 red — the only filled icon allowed) |
| Document / 견적서 | `file-text` |
| Check / 확인 | `check`, `check-circle` |
| Chevron / next | `chevron-right`, `chevron-down` |
| Mail | `mail` |
| External | `arrow-up-right` |

### Substitution flag
> ⚠️ **Lucide is a substitution.** The brand has no existing icon system. Lucide was chosen as the closest line‑drawn match to the Myeongjo type. If the owner has an iconographer or prefers a different family (e.g. Phosphor Regular, custom hand‑drawn), swap globally.

### Hangul / unicode glyphs used as iconography
* **★** — referral / star‑moment headlines (used in the original BNI card)
* **·** — middle dot, the primary in‑line separator
* **「 」** — Korean quotation brackets for named dishes
* **［ ］** — bracketed labels for service categories
* **▣ ▶ ◆** — used very sparingly as section markers in slides

### Emoji
**Disallowed.** The dignified, ritualistic tone of the brand collapses immediately under emoji. Always substitute with the Lucide icon or Korean bracket equivalents above.

### Logos & marks
* `logo-seal.svg` — primary mark, 인장 / Korean stamp aesthetic. Use whenever a single emblem is needed (favicon, profile photo, signature corner).
* `logo-wordmark.svg` — horizontal lockup for headers, business cards, email footers.
* `logo-stacked.svg` — vertical lockup for poster covers, slide title cards, social profile banners.

---

## 7 · Products covered

The brand is small. Two surfaces matter:

1. **Marketing website** — `ui_kits/website/` — the recreation we're building for this design system. Single‑page hi‑fi clickable prototype covering: hero, services (이동밥차 · 제물상차림 · 단체식사), how‑it‑works, gallery, testimonials, contact.
2. **Slide template** — `slides/` — based on the BNI referral profile format, but rebuilt with this brand. Useful for the owner to reuse at networking groups, sales pitches, or family/clan event briefings. Covers: TitleSlide, IntroSlide, ServiceSlide, GallerySlide, ReferralSlide, ContactSlide.

A mobile app, ordering platform, or printed menu **are not** part of this scope. If the owner later wants these, the system already contains everything needed (palette, type, components) to extend.

---

## 8 · How to use this system

For an agent (Claude Code, Claude on the web, etc.):

1. Read this README in full.
2. Open `colors_and_type.css` and `@import` it into any new HTML you create.
3. When you need a brand mark: copy the appropriate `assets/logo-*.svg` and embed/reference it.
4. When you need imagery: prefer the photographs in `assets/`. Do **not** generate new imagery via SVG illustration.
5. When you need icons: load Lucide via CDN as shown in §6.
6. Use UI kit components in `ui_kits/website/` as the canonical hi‑fi reference for buttons, cards, sections, and layout.
7. When in doubt about tone, re‑read §4. When in doubt about visuals, re‑read §5. When in doubt about either, look at `assets/jemulsang-hero.jpg` and ask: *would this design feel at home on the same table as that?*
