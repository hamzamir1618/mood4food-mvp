# Mood4Food — Design System

> Dense · Ornate · Old-World Menu · Maximalist Fine-Dining

---

## 1. Design Philosophy

This system targets a **rich, enclosing, low-negative-space** aesthetic — the feel of a leather-bound menu in a dimly lit fine-dining room. The palette avoids both flat black and bright white; every surface has warmth and depth.

**Three pillars:**

| Pillar | Role | Colors |
|---|---|---|
| **Espresso-ink base** | Rich dark surfaces that feel warm, not cold | `bg-deep`, `bg-elevated`, `bg-recessed` |
| **Gold / brass accent** | Universal premium connective tissue — borders, dividers, ornaments | `gold`, `gold-light`, `gold-muted` |
| **Cuisine accents** | Category-specific identity for pills, cards, icons | 9 distinct hues per cuisine |

---

## 2. Base Surfaces

Rich dark tones with deliberate warm undertones (brown/umber, never blue-gray).

| Token | Hex | Usage |
|---|---|---|
| `--bg-deep` | `#1B1411` | Primary page background — the "espresso ink" base |
| `--bg-elevated` | `#241C17` | Cards, modals, popovers — lifted one step |
| `--bg-recessed` | `#130F0C` | Input wells, sidebars, recessed areas — one step deeper |
| `--bg-warm-wash` | `#2A201A` | Hover states, active rows, subtle emphasis |

> **IMPORTANT:** These are **warm** near-blacks, not neutral gray. The undertone is umber/espresso — `hsl(20°, 25%, 8%)` territory. If you add a new surface shade, stay in the same warm brown hue family.

---

## 3. Text Tiers

Three tiers of text prominence, all warm-toned against the dark surfaces.

| Token | Hex | Contrast vs `bg-deep` | Usage |
|---|---|---|---|
| `--text-primary` | `#F0EDE8` | **15.6:1** (AAA) | Body text, headings, all primary readable content |
| `--text-secondary` | `#B8AFA5` | **8.4:1** (AAA) | Subtitles, metadata, supporting labels |
| `--text-tertiary` | `#7A7168` | **3.8:1** (AA-large) | Captions, timestamps, decorative labels — **≥18px or bold only** |
| `--text-on-gold` | `#1B1411` | **8.0:1** vs gold (AAA) | Dark text placed ON gold backgrounds (buttons, badges) |

> **WARNING:** `--text-tertiary` does **not** meet AA for normal-size text. Use it **only** for:
> - Text ≥ 18px (or ≥ 14px bold)
> - Non-essential decorative labels
> - Timestamps, hints, and captions that are not the only way to convey information

---

## 4. Gold / Brass Accent

The unifying premium thread — used for borders, dividers, highlights, and ornamental elements across all cuisines.

| Token | Hex | Contrast vs `bg-deep` | Usage |
|---|---|---|---|
| `--gold` | `#C9A84C` | **8.0:1** (AAA) | Primary accent — borders, active states, key highlights, icon fills |
| `--gold-light` | `#DFC478` | 10.7:1 vs `text-on-gold` (AAA) | Hover/glow states, brightened gold on interaction |
| `--gold-muted` | `#8A7A4A` | **4.3:1** (AA-large) | Subtle ornamental lines, background filigree, watermarks — **decorative only** |

### Gold Usage Rules

```
DO:   Gold for borders, dividers, separator lines, ornamental rules
DO:   Gold for icon fills, active navigation indicators
DO:   Gold for badge/pill backgrounds with dark text (#1B1411) on top
DO:   Gold-muted for background filigree and watermark patterns

DON'T: Gold for large filled backgrounds (overpowering, loses premium feel)
DON'T: Gold for body text (distracting, hard to read at length)
DON'T: Gold-muted for any readable text (fails AA for normal text)
```

---

## 5. Cuisine Accent Colors

One distinct accent per cuisine category in the dataset. Each is chosen to:
1. **Evoke the cuisine's cultural palette** (terracotta for desi, jade for middle eastern, etc.)
2. **Harmonize with the espresso base + gold system** (warm undertones, no neon)
3. **Pass WCAG AA (≥4.5:1)** for normal text on both `bg-deep` and `bg-elevated`

| Category Key | Display Name | Hex | Inspiration | vs `bg-deep` | vs `bg-elevated` |
|---|---|---|---|---|---|
| `desi_traditional` | Desi | `#D4763C` | Tandoor / terracotta | **5.6:1** AA | **5.2:1** AA |
| `chinese_asian` | Chinese & Asian | `#E05858` | Lacquer red | **4.9:1** AA | **4.6:1** AA |
| `middle_eastern` | Middle Eastern | `#4AA882` | Jade / ceramic teal | **6.3:1** AA | **5.8:1** AA |
| `continental_upscale` | Continental | `#9B88C8` | Aubergine / lavender | **5.8:1** AA | **5.4:1** AA |
| `fast_food` | Fast Food | `#D4A023` | Mustard / golden crisp | **7.7:1** AAA | **7.1:1** AAA |
| `cafe_bakery` | Café & Bakery | `#C47A5A` | Cinnamon / rosewood | **5.4:1** AA | **5.0:1** AA |
| `pizza` | Pizza | `#D4624E` | Tomato / brick | **4.9:1** AA | **4.5:1** AA |
| `beverages` | Beverages | `#4A94B8` | Cerulean / cool teal | **5.4:1** AA | **5.0:1** AA |
| `other` | Other | `#8B8178` | Warm neutral stone | **4.8:1** AA | — |

### Cuisine Color Usage Rules

```
DO:   Use as category pill/chip background with dark text on top
DO:   Use as left-border or top-border accent on cuisine-specific cards
DO:   Use as icon/emoji tint for cuisine identifiers
DO:   Use as accent color for headings within cuisine-scoped views

DON'T: Mix multiple cuisine accents in one component (confusing)
DON'T: Use cuisine accents for general-purpose UI (buttons, links, errors)
DON'T: Use as large background fills — keep to small accent areas
```

---

## 6. Semantic / Status Colors

| Token | Hex | Contrast vs `bg-deep` | Usage |
|---|---|---|---|
| `--status-success` | `#5AAF6A` | **6.7:1** (AA) | Health score, confirmations, positive state |
| `--status-warning` | `#D4A023` | **7.7:1** (AAA) | Budget alerts, caution states, relaxation notices |
| `--status-error` | `#E05858` | **4.9:1** (AA) | Errors, destructive actions, failures |

> The score bars reuse these: `--score-health` = success green, `--score-budget` = warning amber, `--score-taste` = error red. They are semantically the same colors, just aliased.

---

## 7. Full WCAG AA Contrast Audit

All 33 text-on-background combinations that will actually be used in the UI:

### ✅ Pass AA or Better (30/33)

| Foreground | Background | Ratio | Grade | Context |
|---|---|---|---|---|
| `#F0EDE8` | `#1B1411` | 15.6:1 | AAA | Body text on main bg |
| `#F0EDE8` | `#241C17` | 14.4:1 | AAA | Body text on cards |
| `#F0EDE8` | `#130F0C` | 16.3:1 | AAA | Body text on recessed |
| `#F0EDE8` | `#2A201A` | 13.6:1 | AAA | Body text on hover/active |
| `#B8AFA5` | `#1B1411` | 8.4:1 | AAA | Secondary text on main bg |
| `#B8AFA5` | `#241C17` | 7.8:1 | AAA | Secondary text on cards |
| `#C9A84C` | `#1B1411` | 8.0:1 | AAA | Gold accent on main bg |
| `#C9A84C` | `#241C17` | 7.3:1 | AAA | Gold accent on cards |
| `#1B1411` | `#C9A84C` | 8.0:1 | AAA | Dark text on gold |
| `#1B1411` | `#DFC478` | 10.7:1 | AAA | Dark text on gold-light |
| `#D4763C` | `#1B1411` | 5.6:1 | AA | Desi accent |
| `#E05858` | `#1B1411` | 4.9:1 | AA | Chinese accent |
| `#4AA882` | `#1B1411` | 6.3:1 | AA | Middle Eastern accent |
| `#9B88C8` | `#1B1411` | 5.8:1 | AA | Continental accent |
| `#D4A023` | `#1B1411` | 7.7:1 | AAA | Fast food accent |
| `#C47A5A` | `#1B1411` | 5.4:1 | AA | Café accent |
| `#D4624E` | `#1B1411` | 4.9:1 | AA | Pizza accent |
| `#4A94B8` | `#1B1411` | 5.4:1 | AA | Beverages accent |
| `#8B8178` | `#1B1411` | 4.8:1 | AA | Other accent |
| All 8 cuisine accents | `#241C17` | ≥4.5:1 | AA | On elevated cards |
| `#5AAF6A` | `#1B1411` | 6.7:1 | AA | Success/health |
| `#D4A023` | `#1B1411` | 7.7:1 | AAA | Warning/budget |
| `#E05858` | `#1B1411` | 4.9:1 | AA | Error/taste |

### ⚠️ AA-Large Only (3/33) — Intentionally Decorative

| Foreground | Background | Ratio | Context | Constraint |
|---|---|---|---|---|
| `#7A7168` | `#1B1411` | 3.8:1 | Tertiary text / captions | ≥18px or ≥14px bold only |
| `#7A7168` | `#241C17` | 3.5:1 | Tertiary text on cards | ≥18px or ≥14px bold only |
| `#8A7A4A` | `#1B1411` | 4.3:1 | Muted gold ornaments | Decorative only, never text |

### ❌ Failures: 0

---

## 8. CSS Custom Properties

```css
:root {
  /* ── Base surfaces ── */
  --bg-deep:       #1B1411;
  --bg-elevated:   #241C17;
  --bg-recessed:   #130F0C;
  --bg-warm-wash:  #2A201A;

  /* ── Text tiers ── */
  --text-primary:   #F0EDE8;
  --text-secondary: #B8AFA5;
  --text-tertiary:  #7A7168;
  --text-on-gold:   #1B1411;

  /* ── Gold / brass accent ── */
  --gold:          #C9A84C;
  --gold-light:    #DFC478;
  --gold-muted:    #8A7A4A;

  /* ── Cuisine accents ── */
  --cuisine-desi:         #D4763C;
  --cuisine-chinese:      #E05858;
  --cuisine-mideast:      #4AA882;
  --cuisine-continental:  #9B88C8;
  --cuisine-fastfood:     #D4A023;
  --cuisine-cafe:         #C47A5A;
  --cuisine-pizza:        #D4624E;
  --cuisine-beverages:    #4A94B8;
  --cuisine-other:        #8B8178;

  /* ── Semantic / status ── */
  --status-success: #5AAF6A;
  --status-warning: #D4A023;
  --status-error:   #E05858;

  /* ── Score aliases (same colors, semantic names) ── */
  --score-health:  var(--status-success);
  --score-budget:  var(--status-warning);
  --score-taste:   var(--status-error);
}
```

---

## 9. Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│  MOOD4FOOD COLOR SYSTEM                                      │
├──────────────┬──────────────────────────────────────────────┤
│  Surfaces    │  #1B1411  #241C17  #130F0C  #2A201A         │
│  Text        │  #F0EDE8  #B8AFA5  #7A7168                  │
│  Gold        │  #C9A84C  #DFC478  #8A7A4A                  │
├──────────────┼──────────────────────────────────────────────┤
│  Desi        │  #D4763C  Tandoor terracotta                 │
│  Chinese     │  #E05858  Lacquer red                        │
│  Mid-East    │  #4AA882  Jade ceramic                       │
│  Continental │  #9B88C8  Aubergine lavender                 │
│  Fast Food   │  #D4A023  Mustard gold                       │
│  Café        │  #C47A5A  Cinnamon rosewood                  │
│  Pizza       │  #D4624E  Tomato brick                       │
│  Beverages   │  #4A94B8  Cerulean teal                      │
│  Other       │  #8B8178  Warm stone                         │
├──────────────┼──────────────────────────────────────────────┤
│  Status      │  #5AAF6A  #D4A023  #E05858                  │
└──────────────┴──────────────────────────────────────────────┘
```

---

## 10. Typography System

Two tiers of typography create a clear hierarchy: one legible workhorse for everything functional, and cuisine-specific display faces that bring character to dish names and headers without sacrificing readability.

### Tier 1 — Workhorse: Source Serif 4

| Property | Value |
|---|---|
| **Font** | Source Serif 4 (Variable, wght 200–900) |
| **Package** | `@fontsource-variable/source-serif-4` |
| **CSS** | `'Source Serif 4 Variable', 'Source Serif 4', Georgia, serif` |
| **Role** | ALL functional UI text — body copy, prices, buttons, navigation, form labels, metadata, scores, toasts, modals |

**Why Source Serif 4?**
- Designed by Frank Grießhammer at Adobe — a refined, highly-legible transitional serif with excellent x-height
- Feels editorial and premium (not generic tech-startup sans-serif), consistent with the old-world menu aesthetic
- Variable weight axis allows fine-grained typographic hierarchy (light captions → bold headings) within one family
- Superb screen rendering at small sizes — critical for prices, nutritional info, and metadata
- Not a display face — it deliberately stays out of the way and lets the cuisine fonts shine on dish names

> **Logo/Brand exception:** The Mood4Food wordmark and brand elements use **Outfit Variable** (the previously-installed sans-serif). Outfit is used ONLY for the logo lockup and small UI accent labels where a geometric sans reads better than a serif.

### Tier 2 — Cuisine Display Fonts

Used **exclusively** for dish names and cuisine-specific section headers. Never for body text, prices, buttons, or metadata.

| Cuisine | Font | Weight | Inspiration | Why this font |
|---|---|---|---|---|
| `desi_traditional` | **Cinzel** | 700 | Roman inscriptional capitals | Evokes formality and antiquity — the old-world gravitas of Mughal-era dining without resorting to pseudo-Devanagari or Nastaliq mimicry |
| `chinese_asian` | **Noto Serif** (Variable) | 600 | High-contrast transitional serif | Legitimate, tasteful, high-contrast — explicitly avoids the brush-script cliché that plagues every Chinese restaurant menu |
| `middle_eastern` | **Cinzel Decorative** | 400 | Ottoman-court formality | The decorative variant of Cinzel — ornamental serifs add the flourish that distinguishes Middle Eastern elegance from Desi formality, without using literal Arabic script mimicry |
| `continental_upscale` | **Playfair Display** (Variable) | 700 | Didone / Bodoni tradition | The canonical fine-dining typeface — high-contrast hairline serifs signal luxury. Used by every serious European restaurant menu for a reason |
| `fast_food` | **Bebas Neue** | 400 | Bold condensed grotesque | Punchy, contemporary, space-efficient — communicates fast-food energy without being cartoonish. Works at large sizes for burger and fry names |
| `cafe_bakery` | **Fraunces** (Variable) | 500 | Warm old-style soft serif | "Wonky" soft-serif with optical-size axis — feels handcrafted and bakery-warm without crossing into novelty script territory |
| `pizza` | **Bebas Neue** | 400 | (shared with fast_food) | Pizza shares fast food's bold, direct typographic voice — both are casual, punchy categories |
| `beverages` | **Fraunces** (Variable) | 400 | (shared with café) | Beverages share café/bakery's warm, inviting tone — both are leisure/comfort categories |
| `other` | **Source Serif 4** (Variable) | 600 | (falls back to workhorse) | Uncategorized items use the workhorse at a heavier weight — no category = no display font |

### Pairing Table — Real Dish Names from Dataset

Each row shows the exact font pairing: **Tier 2 display** for the dish name, **Tier 1 workhorse** for supporting text.

| Cuisine | Dish Name (Display Font) | Supporting Text (Workhorse) |
|---|---|---|
| **Desi** | _Cinzel 700:_ **Chicken Karahi** | _Source Serif 4 400:_ A rich, aromatic karahi with tender chicken — Rs. 850 |
| **Desi** | _Cinzel 700:_ **Seekh Kebab Platter** | _Source Serif 4 400:_ Charcoal-grilled minced lamb kebabs — Rs. 620 |
| **Chinese/Asian** | _Noto Serif 600:_ **Spicy & Sour Chicken Tom Yum Gai** | _Source Serif 4 400:_ Thai-inspired sour broth with chicken — Rs. 1,075 |
| **Chinese/Asian** | _Noto Serif 600:_ **Steamed Rice with Spring Rolls** | _Source Serif 4 400:_ Jasmine rice alongside crispy vegetable rolls — Rs. 480 |
| **Middle Eastern** | _Cinzel Decorative 400:_ **Baba Ganoush** | _Source Serif 4 400:_ Smoky roasted aubergine dip with tahini — Rs. 550 |
| **Middle Eastern** | _Cinzel Decorative 400:_ **Hummus** | _Source Serif 4 400:_ Classic chickpea purée with olive oil drizzle — Rs. 450 |
| **Continental** | _Playfair Display 700:_ **Single Scoop Gelato** | _Source Serif 4 400:_ Artisanal Italian gelato — Rs. 350 |
| **Continental** | _Playfair Display 700:_ **Caeser Salad** | _Source Serif 4 400:_ Romaine, parmesan, croutons, anchovy dressing — Rs. 780 |
| **Fast Food** | _Bebas Neue 400:_ **AFGHAN CHICKEN TIKKA BURGER** | _Source Serif 4 400:_ Grilled tikka patty with special sauce — Rs. 330 |
| **Fast Food** | _Bebas Neue 400:_ **BEEF SAUSAGES BURGER** | _Source Serif 4 400:_ Double beef sausage with cheese — Rs. 380 |
| **Café/Bakery** | _Fraunces 500:_ **Cappuccino** | _Source Serif 4 400:_ Double-shot espresso with steamed milk foam — Rs. 480 |
| **Café/Bakery** | _Fraunces 500:_ **Praline** | _Source Serif 4 400:_ Belgian praline chocolate pastry — Rs. 320 |
| **Pizza** | _Bebas Neue 400:_ **CROWN CRUST PIZZA** | _Source Serif 4 400:_ Signature stuffed-crust with premium toppings — Rs. 1,200 |
| **Beverages** | _Fraunces 400:_ **Kiwi Delight** | _Source Serif 4 400:_ Fresh kiwi blended with ice — Rs. 350 |
| **Other** | _Source Serif 4 600:_ **Red Lentil Soup** | _Source Serif 4 400:_ Classic Turkish-style lentil soup — Rs. 420 |

### CSS Custom Properties — Typography

```css
:root {
  /* ── Tier 1: Workhorse ── */
  --font-body: 'Source Serif 4 Variable', 'Source Serif 4', Georgia, serif;
  --font-brand: 'Outfit Variable', 'Outfit', sans-serif;

  /* ── Tier 2: Cuisine display ── */
  --font-cuisine-desi:         'Cinzel', 'Source Serif 4 Variable', serif;
  --font-cuisine-chinese:      'Noto Serif Variable', 'Noto Serif', serif;
  --font-cuisine-mideast:      'Cinzel Decorative', 'Cinzel', serif;
  --font-cuisine-continental:  'Playfair Display Variable', 'Playfair Display', serif;
  --font-cuisine-fastfood:     'Bebas Neue', 'Impact', sans-serif;
  --font-cuisine-cafe:         'Fraunces Variable', 'Fraunces', serif;
  --font-cuisine-pizza:        'Bebas Neue', 'Impact', sans-serif;
  --font-cuisine-beverages:    'Fraunces Variable', 'Fraunces', serif;
  --font-cuisine-other:        var(--font-body);
}
```

### Typography Usage Rules

```
DO:   Use --font-body for ALL functional text (prices, buttons, nav, body, form labels, metadata)
DO:   Use --font-cuisine-* ONLY for dish names and cuisine section headers
DO:   Use --font-brand ONLY for the Mood4Food logo/wordmark and small brand accent labels
DO:   Fall back to --font-body when a cuisine category is missing or "other"

DON'T: Use cuisine display fonts for prices, descriptions, or metadata
DON'T: Mix multiple cuisine display fonts in one card (the category determines ONE font)
DON'T: Use Bebas Neue at small sizes — it's designed for display (≥24px)
DON'T: Set Cinzel Decorative in body copy — it's decorative capitals only
```

---

## 11. A Note on Ethnic/Novelty Font Avoidance

> **This section is included as honest documentation for the FYP report.**

A common shortcut in food-app design is to use "ethnic" novelty fonts — brush-script typefaces marketed as "Chinese," faux-Arabic ornamental faces, or Devanagari-imitating Latin fonts — to signal cuisine identity. We deliberately avoided this for three reasons:

1. **Typographic integrity.** Novelty fonts that mimic another script's letterforms in Latin characters (e.g., "wonton font," "faux-kufic") are typographic costumes — they don't carry the cultural weight they gesture toward, and they compromise legibility. A legitimate high-quality serif like Noto Serif signals "Chinese restaurant" through *context* (the dish name, the cuisine pill, the accent color), not through letterform cosplay.

2. **Respect and accuracy.** Using pseudo-Arabic or pseudo-Devanagari Latin fonts reduces entire writing systems to decorative exoticism. The categories in our dataset — desi, middle eastern, chinese/asian — represent real culinary traditions. Treating their visual identity with actual typographic quality (Cinzel's Roman inscriptional gravity for Mughal-era formality, Playfair's Didone elegance for Continental fine dining) is more respectful and more effective than costume fonts.

3. **Visual cohesion.** Novelty fonts clash with the gold/espresso design system. Our cuisine display fonts were chosen to harmonize with the warm, premium base palette — they all share old-world seriousness (Cinzel, Playfair, Noto Serif) or contemporary craft warmth (Fraunces, Bebas Neue). A brush-script "Chinese" font would visually fight the wax-seal logo and gold-bordered cards.

**The result:** Each cuisine has a distinct typographic voice that communicates its character through *quality* rather than *mimicry* — Mughal formality through inscriptional capitals, Ottoman elegance through decorative serifs, fine-dining luxury through Didone hairlines, casual energy through bold condensed type, and bakery warmth through soft wonky serifs.

---

## 12. Ornamental Elements

Reusable SVG and CSS-based decorations that support the dense, maximalist mood. All are vector or CSS-generated — **zero raster texture images**.

### 12.1 Corner Flourishes

Calligraphic scroll brackets placed at card corners. One SVG definition, CSS-transformed for all four positions.

| Property | Value |
|---|---|
| **Component** | `CornerFlourish` (`ornaments/CornerFlourish.jsx`) |
| **Rendering** | Inline SVG, `currentColor` fill/stroke |
| **Props** | `size` (px, default 36), `position` ('tl'/'tr'/'bl'/'br'), `className` |
| **Typical color** | `var(--gold-muted)` at 50% opacity, brightens on hover |

### 12.2 Section Dividers

Ornamental horizontal rules with central motifs. Three variants:

| Variant | Motif | Best for |
|---|---|---|
| `diamond` (default) | Thin rules → dot → nested diamond → dot → thin rules | Primary section breaks (winner/runners-up) |
| `flourish` | Thin rules → symmetrical scroll curls → center dot | Subsection breaks, between card groups |
| `simple` | Thin rules → center dot | Lightweight separators inside cards |

**Component:** `SectionDivider` (`ornaments/SectionDivider.jsx`)
**Props:** `variant` ('diamond'/'flourish'/'simple'), `className`

### 12.3 Background Textures

| Texture | Implementation | Size | Usage |
|---|---|---|---|
| **Linen/noise** | SVG `<feTurbulence>` filter as data URI | ~290 bytes inline | Page background, hero sections, featured cards |
| **Crosshatch** | Pure CSS `repeating-linear-gradient` | 0 bytes (no images) | Recessed panels, input wells, sidebar backgrounds |

Applied via CSS utility classes:
- `.ornament-texture-linen` — subtle fractal noise overlay (opacity 0.03)
- `.ornament-texture-linen--strong` — stronger variant (opacity 0.06) for hero/large surfaces
- `.ornament-texture-crosshatch` — fine 45° gold crosshatch (opacity 0.025)

### 12.4 Filigree Scallop Edge

A repeating scallop/arch pattern in gold, applied as a decorative top or bottom edge.

| Property | Value |
|---|---|
| **Implementation** | SVG data URI in CSS `::before` pseudo-element |
| **Tile size** | 24×6px, repeating horizontally |
| **Size** | ~180 bytes inline |

CSS classes:
- `.ornament-filigree-edge` — scallop on top edge
- `.ornament-filigree-edge--bottom` — scallop on bottom edge
- `.ornament-filigree-edge--both` — both edges

### 12.5 Card Frame

Composite component that wraps children with the gold border, four corner flourishes, and linen texture.

**Component:** `CardFrame` (`ornaments/CardFrame.jsx`)
**Props:** `showCorners` (bool), `cornerSize` (px), `accentColor` (CSS value), `className`

### Performance Summary

| Element | Format | Bytes | Network requests |
|---|---|---|---|
| Corner flourish (×4) | Inline SVG | ~350 bytes/ea | 0 |
| Section divider | Inline SVG | ~250–400 bytes | 0 |
| Linen texture | SVG data URI | ~290 bytes | 0 |
| Crosshatch texture | CSS gradients | 0 bytes | 0 |
| Filigree scallop | SVG data URI | ~180 bytes | 0 |
| **Total raster images** | — | **0** | **0** |

### Ornament Usage Rules

```
DO:   Use corner flourishes on featured/winner cards — the ornament signals importance
DO:   Use diamond dividers between major sections, simple dividers within cards
DO:   Use linen texture on the page body and hero sections for tactile depth
DO:   Use filigree edges on section headers to frame content areas
DO:   Keep flourish opacity low (0.3–0.5) — they should be felt, not stared at

DON'T: Put corner flourishes on every card — overuse kills the signal
DON'T: Use the strong linen texture on small elements (overwhelming)
DON'T: Combine crosshatch AND linen on the same surface (muddy)
DON'T: Use filigree edges on cards (too much with the corner flourishes)
DON'T: Animate the ornaments — they're static printed-menu elements
```

### Files

| File | Purpose |
|---|---|
| `ornaments/CornerFlourish.jsx` | SVG corner scroll bracket |
| `ornaments/SectionDivider.jsx` | 3 divider variants (diamond, flourish, simple) |
| `ornaments/CardFrame.jsx` | Composite frame (border + corners + texture) |
| `ornaments/ornaments.css` | Textures, positioning, filigree edges |
| `ornaments/index.js` | Barrel export |
