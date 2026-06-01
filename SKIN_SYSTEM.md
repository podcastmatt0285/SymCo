# Wadsworth Skin System — Design Document

> **Last updated:** 2026-06-01  
> Any future Claude session implementing or extending skins should start here.
> This document is the single source of truth — no re-audit of the codebase is needed.

---

## Audit Summary

| Metric | Value |
|--------|-------|
| HTML-generating Python files | 26 |
| Total lines generating HTML | ~63,000 |
| Unique hex color values | 601+ |
| CSS variables in default.css | 69 |
| CSS classes across all 4 shells | 170+ |
| Inline `style=""` attributes | 6,655+ |
| Lines of CSS in shell `<style>` blocks | ~1,200 (to be extracted) |
| HTML routes | 100+ |
| Static file serving | ✅ Already wired (`app.py:554`) |

---

## Shell Functions — The Only Injection Points

Every HTML page in the game goes through exactly one of four shell functions.
Inject the two `<link>` tags into all four and every page is skinned.

| Function | File | Line | `<style>` block size | Pages |
|----------|------|------|----------------------|-------|
| `shell()` | `ux.py` | ~600 | 254 lines | All core game pages |
| `stats_shell()` | `stats_ux.py` | ~435 | 285 lines | All `/stats/*` pages |
| `admin_shell()` | `admins_ux.py` | ~73 | 380 lines | All `/admin/*` pages |
| `death_shell()` | `estate_ux.py` | ~44 | 280 lines | All `/estate/*` pages |

Three additional shell-like functions exist but **delegate** to `shell()` in `ux.py`:
- `districts_ux.py::shell()` — calls `ux.shell()`, no extra styles
- `p2p_ux.py::shell()` — calls `ux.shell()`, no extra styles
- `trusted_trade_ux.py::shell()` — calls `ux.shell()`, no extra styles

These three require no changes — they inherit the skin automatically once `ux.shell()` is patched.

---

## Static File Serving

**Already configured.** `app.py:554`:
```python
app.mount("/static", StaticFiles(directory="static"), name="static")
```

`/static/skins/` is already reachable. No new routes needed.

**Head injection pattern** (two tags, order matters — base first, skin second):
```html
<link rel="stylesheet" href="/static/skins/wadsworth-base.css?v=1">
<link rel="stylesheet" href="/static/skins/{skin_name}.css?v=1">
```

For `/admin/*` pages, add a third tag after the skin:
```html
<link rel="stylesheet" href="/static/skins/modules/admin.css?v=1">
```

Increment `?v=` on each deploy to bust browser cache.

---

## CSS Variable Taxonomy (69 variables)

All 69 variables are defined in `static/skins/default.css`.
Every skin file **must define all 69**. No skipping.

### Backgrounds (7)
| Variable | Default | Role |
|----------|---------|------|
| `--bg-page` | `#020617` | Main page background |
| `--bg-card` | `#0f172a` | Card / panel background |
| `--bg-card-2` | `#1e293b` | Nested containers, alt rows, modals |
| `--bg-input` | `#1e293b` | Form inputs, selects, textareas |
| `--bg-header` | `#0b1220` | Fixed top header bar |
| `--bg-ticker` | `#0a1628` | Fixed bottom live-price ticker |
| `--bg-overlay` | `rgba(0,0,0,0.6)` | Modal / drawer overlay |

### Borders (3)
| Variable | Default | Role |
|----------|---------|------|
| `--border` | `#1e293b` | Primary card / input borders |
| `--border-subtle` | `#334155` | Dividers, section separators |
| `--border-focus` | `#38bdf8` | Input focus ring |

### Text (7)
| Variable | Default | Role |
|----------|---------|------|
| `--text-primary` | `#e5e7eb` | Body text, general content |
| `--text-bright` | `#f1f5f9` | Emphasized values, stat numbers |
| `--text-secondary` | `#94a3b8` | Labels, column headers, captions |
| `--text-muted` | `#64748b` | Disabled, placeholder, de-emphasized |
| `--text-faint` | `#475569` | Metadata, timestamps, very subtle text |
| `--text-on-accent` | `#000000` | Text placed ON an accent-colored background |
| `--text-on-danger` | `#ffffff` | Text placed ON a danger-colored background |

### Accent / Brand (9)
| Variable | Default | Role |
|----------|---------|------|
| `--accent` | `#38bdf8` | Primary — links, interactive, highlights |
| `--accent-dim` | `#0ea5e9` | Hover / pressed state of accent |
| `--accent-bg` | `rgba(56,189,248,0.08)` | Subtle accent tint on cards |
| `--accent-2` | `#f59e0b` | Secondary — warnings, alt buttons |
| `--accent-2-dim` | `#d97706` | Hover / pressed of accent-2 |
| `--accent-2-bg` | `rgba(245,158,11,0.08)` | Subtle accent-2 tint |
| `--accent-3` | `#a78bfa` | Tertiary — events, trophies, level badges |
| `--accent-3-dim` | `#7c3aed` | Hover / pressed of accent-3 |
| `--accent-3-bg` | `rgba(167,139,250,0.08)` | Subtle accent-3 tint |

### Semantic Colors (18)
| Variable | Default | Role |
|----------|---------|------|
| `--color-success` | `#22c55e` | Gains, positive values, online status |
| `--color-success-light` | `#4ade80` | Success highlights |
| `--color-success-dark` | `#16a34a` | Success pressed / dark variant |
| `--color-success-bg` | `rgba(34,197,94,0.08)` | Success card tint |
| `--color-danger` | `#ef4444` | Errors, losses, bans |
| `--color-danger-light` | `#f87171` | Error highlights |
| `--color-danger-dark` | `#dc2626` | Critical / permanent-action red |
| `--color-danger-xdark` | `#7f1d1d` | Danger button fill |
| `--color-danger-bg` | `rgba(239,68,68,0.08)` | Danger card tint |
| `--color-warning` | `#f59e0b` | Warnings, alerts (same as accent-2) |
| `--color-warning-light` | `#fbbf24` | Warning highlights |
| `--color-warning-bg` | `rgba(245,158,11,0.08)` | Warning card tint |
| `--color-gold` | `#d4af37` | Premium badge, medals, subscriber marker |
| `--color-gold-bg` | `rgba(212,175,55,0.10)` | Gold card tint |
| `--color-orange` | `#f97316` | Ask prices, orange-coded items |
| `--color-purple` | `#a78bfa` | Level badges (same as accent-3) |
| `--color-teal` | `#0d9488` | Teal-coded economy indicators |
| `--color-pink` | `#ec4899` | Pink event badges |

### Medals — Leaderboard Rank Badges (3)
| Variable | Default | Role |
|----------|---------|------|
| `--color-rank-1` | `#d4af37` | Gold — 1st place |
| `--color-rank-2` | `#c0c0c0` | Silver — 2nd place |
| `--color-rank-3` | `#cd7f32` | Bronze — 3rd place |

### Fonts (4)
| Variable | Default | Role |
|----------|---------|------|
| `--font-body` | `'JetBrains Mono', 'Courier New', monospace` | All page body text |
| `--font-serif` | `Georgia, serif` | Audio player, cert-card headings |
| `--font-cursive` | `'Caveat', cursive` | Decorative callouts |
| `--font-sans` | `'Segoe UI', system-ui, sans-serif` | Fallback sans-serif |

### Border Radius (7)
| Variable | Default | Role |
|----------|---------|------|
| `--radius-sm` | `3px` | Tight: badges, small tags |
| `--radius-md` | `4px` | Standard: buttons, inputs |
| `--radius-lg` | `8px` | Cards, panels |
| `--radius-xl` | `12px` | Large cards, modals |
| `--radius-2xl` | `20px` | Extra-large chips, profile cards |
| `--radius-pill` | `9999px` | Fully-rounded pill buttons / chips |
| `--radius-circle` | `50%` | Avatar circles |

### Z-Index Stacking (5)
| Variable | Default | Role |
|----------|---------|------|
| `--z-below` | `-1` | Behind normal flow (pseudo-elements) |
| `--z-base` | `100` | Search bars, filter overlays |
| `--z-audio` | `150` | Audio player bar (`#gs-bar`) |
| `--z-ticker` | `1000` | Fixed bottom ticker bar |
| `--z-modal` | `9999` | Modals, drawers, full-screen overlays |

### Shadows (4)
| Variable | Default | Role |
|----------|---------|------|
| `--shadow-sm` | `0 1px 4px rgba(0,0,0,0.6)` | Small element depth (knobs, tags) |
| `--shadow-md` | `0 4px 20px rgba(0,0,0,0.7)` | Panels, audio player |
| `--shadow-glow` | `0 8px 25px rgba(56,189,248,0.15)` | Card hover cyan glow |
| `--shadow-glow-danger` | `0 8px 25px rgba(239,68,68,0.15)` | Danger card glow |

### Transitions (3)
| Variable | Default | Role |
|----------|---------|------|
| `--dur-fast` | `0.15s` | Micro-interactions, hover flash |
| `--dur-normal` | `0.2s` | Standard hover / focus transitions |
| `--dur-slow` | `2s` | `lien-pulse`, scroll title animations |

### Gradients (6)
| Variable | Default | Role |
|----------|---------|------|
| `--grad-card` | `linear-gradient(135deg, var(--bg-card) 0%, var(--bg-card-2) 100%)` | Stats card backgrounds |
| `--grad-bar` | `linear-gradient(to top, var(--accent), var(--accent-dim))` | Mini progress bars |
| `--grad-cert` | `linear-gradient(135deg, #0a0a14 0%, #111827 100%)` | Estate cert-card body |
| `--grad-cert-border` | `linear-gradient(90deg, var(--border-subtle), var(--border), var(--border-subtle))` | Cert-card top border |
| `--grad-delete-zone` | `linear-gradient(135deg, #0a0a14 0%, #1a0a0a 100%)` | Estate delete-account zone |
| `--grad-audio-knob` | `linear-gradient(to bottom, #3d2b1f, #1a0f0a)` | Audio tuner knob |

### Audio Player — Mahogany Theme (5)
The in-game radio / music player uses a warm mahogany wood aesthetic, intentionally
distinct from the rest of the UI. Override these to re-theme the player.

| Variable | Default | Role |
|----------|---------|------|
| `--audio-bg-dark` | `#1a0f0a` | Tuner body background |
| `--audio-bg-mid` | `#3d2b1f` | Knob gradient midpoint |
| `--audio-accent` | `#b08d57` | Dial highlights, station name colour |
| `--audio-font` | `var(--font-serif)` | Station name / tuner readout font |
| `--audio-pastels-json` | `'["#FFB7B2","#FFDAC1",...]'` | 15-colour pastel array cycled per station (consumed by JS, not CSS — see note below) |

**Audio pastels note:** The music player rotates through 15 pastel colours in JavaScript.
They are stored as a JSON string in `--audio-pastels-json` so skins can override the
palette. The JS reads it via `getComputedStyle(root).getPropertyValue('--audio-pastels-json')`.
Full default array: `#FFB7B2 #FFDAC1 #E2F0CB #B5EAD7 #C7CEEA #FF9AA2 #F8BBD0 #E1BEE7 #D1C4E9 #BBDEFB #C8E6C9 #F0F4C3 #FFF9C4 #FFE0B2 #F5F5DC`

---

## Admin Module Override

The admin panel uses **red** as its primary accent instead of cyan, so staff
immediately know they are in the admin area regardless of their chosen skin.

This is handled by `static/skins/modules/admin.css` — loaded as a **third**
`<link>` tag after the player's skin, but **only** by `admin_shell()`.
It overrides `--accent`, `--accent-dim`, `--accent-bg`, `--border-focus`,
and `--shadow-glow` to red values.

**Skin authors do not need to account for this.** The override is automatic.

---

## Animations and Keyframes

These live in `wadsworth-base.css` (extracted from `ux.py shell()`).
They reference CSS variables for colours but are not themselves variables.

```css
@keyframes lien-pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.6; }
}
.lien-critical {
  animation: lien-pulse var(--dur-slow) ease-in-out infinite;
  color: var(--color-danger-dark);
}

@keyframes gs-scroll-title {
  0%, 15%  { transform: translateX(0); }
  85%, 100%{ transform: translateX(var(--gs-se, 0px)); }
}
```

---

## CSS Classes — Master List for `wadsworth-base.css`

`wadsworth-base.css` (to be created in Phase 2) must contain all 170+ component
classes currently scattered across the 4 shell `<style>` blocks, converted to use
`var()` instead of hardcoded hex.

### Layout
`body` `a` `* (box-sizing)` `.container` `.grid` `.grid-2` `.grid-3`

### Header & Navigation
`.header` `.brand` `.brand img` `.header-right` `.balance`  
`.nav` `.nav a` `.nav a:hover` `.nav a.active` `.nav::-webkit-scrollbar`

### Cards & Panels
`.card` `.card:hover` `.card-header` `.card-title` `.card-value`  
`.card-subtitle` `.card-icon`  
`.cert-card` `.cert-card::before` `.cert-header` `.cert-title`  
`.cert-badge` `.cert-badge-idle` `.cert-badge-voluntary`  
`.link-card` `.link-card:hover` `.link-card .lc-icon` `.link-card .lc-title` `.link-card .lc-desc`  
`.link-grid`

### Buttons (11 variants)
`.btn` `.btn-blue` `.btn-orange` `.btn-red` `.btn-gold`  
`.btn-danger` `.btn-danger:hover` `.btn-secondary` `.btn-secondary:hover`  
`.btn-primary` `.btn-primary:hover`  
`.btn-yellow` `.btn-yellow:hover` `.btn-green` `.btn-green:hover`  
`.btn-gray` `.btn-gray:hover`

### Badges & Tags
`.badge` `.badge-gold` `.badge-silver` `.badge-bronze`  
`.badge-blue` `.badge-green` `.badge-gray` `.badge-red` `.badge-yellow`

### Stats & Data
`.stat-row` `.stat-row:last-child` `.stat-label` `.stat-value`  
`.stat-value.positive` `.stat-value.negative`  
`.stat-grid` `.stat-box`  
`.page-title` `.page-subtitle`

### Tables
`.table-wrap` `.table` `.table th` `.table th:hover` `.table td`  
`.table tr:hover`

### Forms & Inputs
`input` `select` `textarea` `input:focus` `select:focus` `textarea:focus`  
`.search-box` `.search-box:focus`  
`.form-row` `.form-row > *` `.form-row .btn` `.form-label`

### Filters & Tabs
`.filter-tabs` `.filter-tab` `.filter-tab:hover` `.filter-tab.active`  
`.tabs` `.tabs a` `.tabs a:hover` `.tabs a.active`

### Charts & Visualisation
`.chart-container` `.mini-chart` `.mini-chart-bar` `.progress` `.progress-bar`

### Transactions & Ledger
`.transaction-item` `.transaction-item:hover`  
`.transaction-desc` `.transaction-time` `.transaction-amount`

### Player & Admin Rows
`.player-list-item` `.player-list-item:hover` `.player-name` `.player-worth`  
`.detail-row` `.detail-row .label` `.detail-row .value`  
`.chat-msg-row` `.cm-name` `.cm-time` `.cm-text`

### Estate-Specific
`.heir-slot` `.heir-slot-empty` `.heir-number`  
`.delete-zone` `.delete-zone h3`  
`.inheritance-alert` `.rank-1` `.rank-2` `.rank-3`

### Notifications & Alerts
`.flash` `.flash-success` `.flash-error` `.alert` `.alert-success`

### Lien Status
`.lien-critical` (animation applied here)  
`.status-critical` `.status-warning` `.status-ok`
*(these replace Python status-color dicts — see Python Status Colors section)*

### Ticker
`.ticker` `#tkViewport` `.ticker-controls` `.ticker-btn` `.ticker-btn:hover` `.ticker-btn.active`

### Misc
`.divider` `.detail-section` `.detail-title` `.recipe-item` `.recipe-arrow` `.terrain-tag`

### Responsive (media queries — in base, not skin)
`@media (max-width: 640px)` `@media (max-width: 480px)` `@media (min-width: 640px)`

---

## Python Status Color Dicts

Several Python files compute `style="color: {hex}"` dynamically via dicts.
These must be converted from hex values to CSS class names — the CSS then applies
`var()` colors.

### Pattern (apply everywhere a status dict exists)

```python
# Before:
lien_colors = {"critical": "#dc2626", "warning": "#f59e0b", "ok": "#64748b"}
color = lien_colors[status]
html = f'<span style="color:{color};">{label}</span>'

# After:
html = f'<span class="status-{status}">{label}</span>'
```

```css
/* In wadsworth-base.css: */
.status-critical { color: var(--color-danger-dark); }
.status-warning  { color: var(--color-warning); }
.status-ok       { color: var(--text-muted); }
```

### Known files containing status-color dicts to convert
- `ux.py` — lien status (critical / warning / ok)
- `admins_ux.py` — player status (banned, muted, online, suspended)
- `stats_ux.py` — economy health indicators
- `districts_ux.py` — district status
- `counties_ux.py` — county health

---

## SVG / Icon Fill Colors

SVG `fill=` attributes are hardcoded inline. These need to become CSS class-based.

Known fills requiring conversion:
```
fill="#22c55e"  → class="svg-success"  → fill: var(--color-success)
fill="#ef4444"  → class="svg-danger"   → fill: var(--color-danger)
fill="#475569"  → class="svg-muted"    → fill: var(--text-faint)
fill="#64748b"  → class="svg-muted2"   → fill: var(--text-muted)
fill="#607098"  → class="svg-series"   → fill: var(--accent-3-dim)
fill="#e2e8f0"  → class="svg-light"    → fill: var(--text-secondary)
fill="#000000"  → class="svg-dark"     → fill: var(--text-on-accent)
```

This is a Phase 3 task (low priority — skins work without it, but chart/icon colours
won't respond to skin changes until it's done).

---

## Implementation Plan

### Phase 1 — Plumbing (1 session)
Goal: skin selection works end-to-end. No visual change for players yet.

1. `auth.py` — add `skin = Column(String(64), default="default", nullable=False)` to `Player`
2. `ux.py` `shell()` — add `skin: str = "default"` param; inject two `<link>` tags
3. `stats_ux.py` `stats_shell()` — same injection
4. `admins_ux.py` `admin_shell()` — inject base + skin + `modules/admin.css`
5. `estate_ux.py` `death_shell()` — same as step 2
6. All call sites that invoke a shell function — pass `skin=player.skin` (player obj already in scope on all pages)
7. `settings_ux.py` — add skin picker `<select>` populated by `glob("static/skins/*.css")` excluding `wadsworth-base.css` and anything in `modules/`; POST saves `player.skin`
8. `static/skins/default.css` ✅ already created (69 variables)
9. `static/skins/modules/admin.css` ✅ already created

**Verification:** DevTools shows two `<link>` tags on every page → `default.css` vars resolve → page looks identical to today.

---

### Phase 2 — CSS Consolidation (2–3 sessions)
Goal: extract 1,200 lines of duplicated shell CSS into `wadsworth-base.css`
using `var()` throughout. Shells become `<link>` tags only — no more `<style>` blocks.

1. Diff the 4 shell `<style>` blocks to identify overlapping vs. shell-specific classes
2. All shared classes → `static/skins/wadsworth-base.css` with `var()` colors
3. Shell-specific classes → `static/skins/modules/{module}.css` (admin already done)
4. Delete `<style>` blocks from all 4 shell functions
5. Estate cert-card and delete-zone use `--grad-cert` / `--grad-delete-zone` variables
6. Stats mini-chart bars use `--grad-bar`
7. Card hover uses `--shadow-glow`
8. All animations use `--dur-slow` / `--dur-normal`

**Expected result:** 1,200 shell CSS lines → 0, all in static files, skin variables control all colours.

---

### Phase 3 — Inline Style Remediation (many sessions)
Goal: convert 6,655 `style="color:#XXXXX"` attributes to CSS classes.
**Not required for skins to work** — Phase 2 is sufficient. Phase 3 improves
skin fidelity so inline-styled elements also respond to theme changes.

Priority order (file size × color frequency):
1. `ux.py` (largest, most colors)
2. `admins_ux.py`
3. `stats_ux.py`
4. `estate_ux.py`, `counties_ux.py`, `tutorial_ux.py`
5. All remaining `*_ux.py` files

Strategy per file:
- Grep all `style="color:#XXXXXX"` patterns
- Map each to a variable: `color:#38bdf8` → `class="text-accent"` → `color: var(--accent)`
- Python status dicts → CSS class approach (see §Python Status Colors)
- SVG fills → `class="svg-*"` approach (see §SVG Colors)

---

### Phase 4 — Skin Creation (ongoing, can begin during Phase 3)
One skin = one file in `static/skins/` defining all 69 `:root` variables.
See skin template below.

**Subscriber gating:** pro skins have a `Tier: pro` comment in their header.
The settings skin picker reads `player.subscriber` and hides/greys pro skins if false.

---

## Skin Template

Copy to `static/skins/your_skin_name.css`. Change values only. No component CSS.

```css
/*
 * Wadsworth Skin: YOUR SKIN NAME
 * Author: YOUR NAME
 * Description: ONE LINE DESCRIPTION
 * Tier: free | pro
 *
 * Rules:
 *  - Define ALL 69 variables. No skipping.
 *  - No component CSS — variables only.
 *  - Test pages: / · /market · /businesses · /inventory · /stats/leaderboard
 *                /stats/economy · /estate · /admin · settings skin picker
 *  - WCAG AA contrast: all text ≥ 4.5:1 against its background.
 *  - --text-on-accent must be readable on --accent background.
 *  - --color-success and --color-danger must be visually distinguishable.
 *  - --audio-* can keep the mahogany defaults unless the skin explicitly re-themes the player.
 */

:root {

  /* ── Backgrounds ─────────────────────────────────────────────────────────── */
  --bg-page:         #020617;
  --bg-card:         #0f172a;
  --bg-card-2:       #1e293b;
  --bg-input:        #1e293b;
  --bg-header:       #0b1220;
  --bg-ticker:       #0a1628;
  --bg-overlay:      rgba(0,0,0,0.6);

  /* ── Borders ─────────────────────────────────────────────────────────────── */
  --border:          #1e293b;
  --border-subtle:   #334155;
  --border-focus:    #38bdf8;

  /* ── Text ────────────────────────────────────────────────────────────────── */
  --text-primary:    #e5e7eb;
  --text-bright:     #f1f5f9;
  --text-secondary:  #94a3b8;
  --text-muted:      #64748b;
  --text-faint:      #475569;
  --text-on-accent:  #000000;
  --text-on-danger:  #ffffff;

  /* ── Accent / Brand ──────────────────────────────────────────────────────── */
  --accent:          #38bdf8;
  --accent-dim:      #0ea5e9;
  --accent-bg:       rgba(56,189,248,0.08);
  --accent-2:        #f59e0b;
  --accent-2-dim:    #d97706;
  --accent-2-bg:     rgba(245,158,11,0.08);
  --accent-3:        #a78bfa;
  --accent-3-dim:    #7c3aed;
  --accent-3-bg:     rgba(167,139,250,0.08);

  /* ── Semantic ────────────────────────────────────────────────────────────── */
  --color-success:        #22c55e;
  --color-success-light:  #4ade80;
  --color-success-dark:   #16a34a;
  --color-success-bg:     rgba(34,197,94,0.08);
  --color-danger:         #ef4444;
  --color-danger-light:   #f87171;
  --color-danger-dark:    #dc2626;
  --color-danger-xdark:   #7f1d1d;
  --color-danger-bg:      rgba(239,68,68,0.08);
  --color-warning:        #f59e0b;
  --color-warning-light:  #fbbf24;
  --color-warning-bg:     rgba(245,158,11,0.08);
  --color-gold:           #d4af37;
  --color-gold-bg:        rgba(212,175,55,0.10);
  --color-orange:         #f97316;
  --color-purple:         #a78bfa;
  --color-teal:           #0d9488;
  --color-pink:           #ec4899;

  /* ── Medals ──────────────────────────────────────────────────────────────── */
  --color-rank-1:    #d4af37;
  --color-rank-2:    #c0c0c0;
  --color-rank-3:    #cd7f32;

  /* ── Fonts ───────────────────────────────────────────────────────────────── */
  --font-body:     'JetBrains Mono', 'Courier New', monospace;
  --font-serif:    Georgia, serif;
  --font-cursive:  'Caveat', cursive;
  --font-sans:     'Segoe UI', system-ui, sans-serif;

  /* ── Border Radius ───────────────────────────────────────────────────────── */
  --radius-sm:     3px;
  --radius-md:     4px;
  --radius-lg:     8px;
  --radius-xl:     12px;
  --radius-2xl:    20px;
  --radius-pill:   9999px;
  --radius-circle: 50%;

  /* ── Z-Index ─────────────────────────────────────────────────────────────── */
  --z-below:    -1;
  --z-base:     100;
  --z-audio:    150;
  --z-ticker:   1000;
  --z-modal:    9999;

  /* ── Shadows ─────────────────────────────────────────────────────────────── */
  --shadow-sm:          0 1px 4px rgba(0,0,0,0.6);
  --shadow-md:          0 4px 20px rgba(0,0,0,0.7);
  --shadow-glow:        0 8px 25px rgba(56,189,248,0.15);
  --shadow-glow-danger: 0 8px 25px rgba(239,68,68,0.15);

  /* ── Transitions ─────────────────────────────────────────────────────────── */
  --dur-fast:   0.15s;
  --dur-normal: 0.2s;
  --dur-slow:   2s;

  /* ── Gradients ───────────────────────────────────────────────────────────── */
  --grad-card:        linear-gradient(135deg, var(--bg-card) 0%, var(--bg-card-2) 100%);
  --grad-bar:         linear-gradient(to top, var(--accent), var(--accent-dim));
  --grad-cert:        linear-gradient(135deg, #0a0a14 0%, #111827 100%);
  --grad-cert-border: linear-gradient(90deg, var(--border-subtle), var(--border), var(--border-subtle));
  --grad-delete-zone: linear-gradient(135deg, #0a0a14 0%, #1a0a0a 100%);
  --grad-audio-knob:  linear-gradient(to bottom, #3d2b1f, #1a0f0a);

  /* ── Audio Player (Mahogany) ─────────────────────────────────────────────── */
  --audio-bg-dark:       #1a0f0a;
  --audio-bg-mid:        #3d2b1f;
  --audio-accent:        #b08d57;
  --audio-font:          var(--font-serif);
  --audio-pastels-json:  '["#FFB7B2","#FFDAC1","#E2F0CB","#B5EAD7","#C7CEEA","#FF9AA2","#F8BBD0","#E1BEE7","#D1C4E9","#BBDEFB","#C8E6C9","#F0F4C3","#FFF9C4","#FFE0B2","#F5F5DC"]';

}
```

---

## Skin Author Checklist

- [ ] All 69 variables defined
- [ ] Filename: `a-z`, `0-9`, `_` only — no spaces, no uppercase
- [ ] `Tier:` comment set to `free` or `pro`
- [ ] No component CSS — variables only
- [ ] Tested on: `/` · `/market` · `/businesses` · `/inventory` · `/stats/leaderboard` · `/stats/economy` · `/estate` · `/admin` · settings skin picker
- [ ] All text ≥ 4.5:1 contrast against background (WCAG AA)
- [ ] `--text-on-accent` is readable on `--accent`
- [ ] `--color-success` and `--color-danger` are visually distinct
- [ ] `--color-rank-1/2/3` read as gold / silver / bronze (or equivalent prestige order)
- [ ] Audio player: either leave mahogany defaults or override all 5 `--audio-*` vars
- [ ] Shadow glows: if changing `--accent`, update `--shadow-glow` to match its rgba
- [ ] Gradient vars referencing hardcoded hex (cert, delete-zone, audio-knob) updated if doing a light theme

---

## Files Changed Per Phase

### Phase 1 (plumbing)
- `auth.py` — add `skin` column to `Player`
- `ux.py` — patch `shell()` signature + inject `<link>` tags
- `stats_ux.py` — patch `stats_shell()`
- `admins_ux.py` — patch `admin_shell()` (3 tags: base + skin + modules/admin.css)
- `estate_ux.py` — patch `death_shell()`
- `settings_ux.py` — skin picker UI + save endpoint
- `static/skins/default.css` ✅ done
- `static/skins/modules/admin.css` ✅ done

### Phase 2 (CSS consolidation)
- `static/skins/wadsworth-base.css` ← NEW (~1,400 lines)
- `static/skins/modules/estate.css` ← NEW (cert-card, delete-zone, heir-slot)
- `static/skins/modules/stats.css` ← NEW (mini-chart, transaction, recipe)
- `ux.py` — delete `<style>` block from `shell()`
- `stats_ux.py` — delete `<style>` block from `stats_shell()`
- `admins_ux.py` — delete `<style>` block from `admin_shell()`
- `estate_ux.py` — delete `<style>` block from `death_shell()`

### Phase 3 (inline style remediation — incremental, one file at a time)
All 26 `*_ux.py` files — inline `style="color:#..."` → CSS class

### Phase 4 (new skins — no Python changes)
`static/skins/<skin_name>.css` ← NEW per skin

---

## Open Questions

- **Skin display names** — should human-readable names (e.g. "Deep Space") be parsed
  from the CSS comment header, or stored in a separate `skins_manifest.json`?
- **Subscriber gate UX** — does the picker hide pro skins entirely when `subscriber == False`,
  or show them greyed out with a lock icon (better for marketing)?
- **Admin skin access** — should admins see all skins regardless of subscription?
- **Live preview** — JS swaps `<link href>` client-side before saving (one line) vs.
  save-and-reload (simpler). Live preview is strongly preferred UX.
- **Cache busting** — manual `?v=N` increment on deploy, or hash-based fingerprinting?
- **Light theme support** — `--grad-cert`, `--grad-delete-zone`, `--grad-audio-knob` contain
  hardcoded dark hex values. Light-theme skins must override these. Add a note to checklist.
