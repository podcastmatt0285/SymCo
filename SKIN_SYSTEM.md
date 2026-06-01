# Wadsworth Skin System — Design Document

## Overview

This document maps the full architecture for adding a subscriber-selectable skin system
to Wadsworth. It is written to be self-contained: a future Claude session reading only
this file should be able to implement or extend any phase without re-auditing the codebase.

---

## Audit Summary (June 2026)

| Metric | Value |
|--------|-------|
| HTML-generating Python files | 26 |
| Total lines generating HTML | ~63,000 |
| Unique hex color values | 600+ |
| Core palette colors (real distinct roles) | ~30 |
| Inline `style=""` attributes | 6,655+ |
| Duplicate shell functions | 4 |
| Duplicated CSS across shells | ~1,200 lines |
| HTML routes | 100+ |

### The four shell functions (every page goes through one of these)

| Function | File | CSS lines | Pages served |
|----------|------|-----------|--------------|
| `shell()` | ux.py ~600 | 254 | All core game pages |
| `stats_shell()` | stats_ux.py ~462 | 285 | All /stats/* pages |
| `admin_shell()` | admins_ux.py ~105 | 380 | All /admin/* pages |
| `death_shell()` | estate_ux.py ~71 | 280 | /estate/* pages |

These are the **only four injection points** needed to skin every page in the game.
Every HTML route ultimately calls one of them.

---

## CSS Variable Taxonomy

The 600+ hex colors collapse into ~32 logical roles.
Every skin must define all 32 variables on `:root`.

### Backgrounds

| Variable | Default (dark) | Role |
|----------|---------------|------|
| `--bg-page` | `#020617` | Main page background |
| `--bg-card` | `#0f172a` | Card / panel background |
| `--bg-card-2` | `#1e293b` | Nested containers, table rows, modals |
| `--bg-input` | `#1e293b` | Form inputs, selects, textareas |
| `--bg-header` | `#0b1220` | Fixed header bar |
| `--bg-ticker` | `#0a1628` | Fixed bottom ticker bar |
| `--bg-overlay` | `rgba(0,0,0,0.6)` | Modal overlays |

### Borders & Dividers

| Variable | Default | Role |
|----------|---------|------|
| `--border` | `#1e293b` | Primary card/input borders |
| `--border-subtle` | `#334155` | Dividers, section separators |
| `--border-focus` | `#38bdf8` | Input focus ring |

### Text

| Variable | Default | Role |
|----------|---------|------|
| `--text-primary` | `#e5e7eb` | Body text, general content |
| `--text-secondary` | `#94a3b8` | Labels, column headers, captions |
| `--text-muted` | `#64748b` | Disabled, placeholder, de-emphasised |
| `--text-faint` | `#475569` | Very subtle text, metadata |
| `--text-on-accent` | `#000000` | Text on accent-colored buttons |

### Accent / Brand

| Variable | Default | Role |
|----------|---------|------|
| `--accent` | `#38bdf8` | Primary accent — links, interactive elements, highlights |
| `--accent-dim` | `#0ea5e9` | Pressed/hover state of accent |
| `--accent-bg` | `rgba(56,189,248,0.08)` | Subtle accent tint on cards |
| `--accent-2` | `#f59e0b` | Secondary accent — secondary buttons, warnings |
| `--accent-2-dim` | `#d97706` | Pressed/hover of accent-2 |
| `--accent-3` | `#a78bfa` | Tertiary accent — events, trophies, level badges |

### Semantic (status colors — used in Python dicts too, see §Python Status Colors)

| Variable | Default | Role |
|----------|---------|------|
| `--color-success` | `#22c55e` | Gains, positive values, online status |
| `--color-success-light` | `#4ade80` | Success highlights |
| `--color-success-bg` | `rgba(34,197,94,0.08)` | Success tint |
| `--color-danger` | `#ef4444` | Errors, losses, bans |
| `--color-danger-light` | `#f87171` | Error highlights |
| `--color-danger-dark` | `#dc2626` | Critical status, permanent actions |
| `--color-danger-bg` | `rgba(239,68,68,0.08)` | Danger tint |
| `--color-warning` | `#f59e0b` | Warnings, alerts (same as --accent-2) |
| `--color-warning-light` | `#fbbf24` | Warning highlights |
| `--color-gold` | `#d4af37` | Premium, medals, subscriber badge |
| `--color-orange` | `#f97316` | Ask prices, orange-coded items |

---

## Python Status Color Dicts

Several Python files build `style="color: {computed_value}"` dynamically.
These must be updated alongside the CSS to reference CSS variable names via
a helper that maps status → CSS class instead of status → hex color.

### Known status dicts to convert

**ux.py** — lien status:
```python
# Current:
lien_colors = {"critical": "#dc2626", "warning": "#f59e0b", "ok": "#64748b"}
# Target: emit class name instead and let CSS handle color
lien_classes = {"critical": "status-critical", "warning": "status-warning", "ok": "status-ok"}
```

**admins_ux.py** — player status indicators (banned, muted, online, etc.)

**stats_ux.py** — economy health indicators

The pattern for all of them:
- Before: `f'<span style="color:{color};">'`
- After: `f'<span class="status-{key}">'`
- CSS: `.status-critical { color: var(--color-danger-dark); }` etc.

---

## Implementation Plan

### Phase 1 — Foundation (1 session, ~3 hours)
Goal: skin selection works end-to-end for the default dark theme.
No visual change for players yet — just the plumbing.

**Files changed:**
1. `auth.py` — add `skin = Column(String(64), default="default", nullable=False)` to `Player`
2. Create `/home/user/SymCo/static/skins/` directory
3. Create `static/skins/default.css` — 32 CSS variable definitions only (see template below)
4. Create `static/skins/wadsworth-base.css` — all component styles converted to use `var()` (extracted from the 4 shell `<style>` blocks, de-duplicated)
5. `ux.py` `shell()` — accept optional `skin: str = "default"` param, inject two `<link>` tags: `wadsworth-base.css` then `{skin}.css`
6. `stats_ux.py` `stats_shell()` — same injection
7. `admins_ux.py` `admin_shell()` — same injection
8. `estate_ux.py` `death_shell()` — same injection
9. `settings_ux.py` — add skin picker `<select>` populated from `glob("static/skins/*.css")` excluding `wadsworth-base.css`; POST saves to `player.skin`
10. Every call site that calls `shell(title, body, balance, player_id)` passes `skin=player.skin` — most already have the player object

**Verification:** load any page → DevTools shows two new `<link>` tags → `default.css` vars resolve → page looks identical to today.

---

### Phase 2 — Shell CSS Consolidation (2–3 sessions)
Goal: the 1,200 lines of duplicated CSS across the 4 shells are replaced by
`wadsworth-base.css` that uses `var()` throughout.

**Process per shell:**
1. Diff the 4 shell `<style>` blocks to find unique-to-that-shell classes
2. Shared classes go into `wadsworth-base.css` with `var()` colors
3. Shell-specific classes go into `static/skins/modules/{module}.css` loaded only by that shell
4. Remove the `<style>` block from the shell function entirely

**Expected result:** 1,200 inline CSS lines → 0 per shell, all in static files.

---

### Phase 3 — Inline Style Remediation (many sessions, lowest priority)
Goal: convert the 6,655 `style="color:#XXXXX"` inline attributes to CSS classes.

**Priority order** (by file size × color frequency):
1. `ux.py` — largest file, most colors
2. `admins_ux.py` — second most color use
3. `stats_ux.py`
4. `estate_ux.py`, `counties_ux.py`, `tutorial_ux.py`
5. All remaining `*_ux.py` files

**Strategy per file:**
- Grep all `style="color:#XXXXXX"` patterns in the file
- For each, decide: does this color map to one of the 32 variables?
  - Yes → replace with a semantic class (`.text-success`, `.text-danger`, `.text-accent`, etc.)
  - No → it's a one-off; leave as inline until a pattern emerges
- Python status color dicts → CSS class approach (see §Python Status Colors above)

**Note:** Phase 3 is not required for skins to work. Skins function correctly after Phase 2.
Phase 3 improves skin fidelity — without it, inline-style colors won't respond to skin changes.
The game is fully usable and skinable without completing Phase 3.

---

### Phase 4 — Skin Creation (ongoing, can begin during Phase 3)
Goal: create actual non-default skin CSS files.

One skin = one file in `static/skins/` that redefines all 32 `:root` variables.
Nothing else — no component CSS, no overrides — just variables.
See the Skin Template section below.

Skins proposed for Wadsworth Pro subscribers (see ADMIN_TODO.md):
- Subscriber-only skins unlocked when `player.subscriber == True`
- The picker filters visible skins based on subscription status
- Skin files can be named with a `pro_` prefix to make gating easy

---

## Serving Static Files

Add to `ux.py` (or `app.py` wherever the FastAPI app is created):

```python
from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="static"), name="static")
```

Skin link tags in the shell `<head>`:
```html
<link rel="stylesheet" href="/static/skins/wadsworth-base.css?v=1">
<link rel="stylesheet" href="/static/skins/{skin_name}.css?v=1">
```

Increment `?v=` on each deploy to bust browser cache.

---

## Skin Template

Copy this file to `static/skins/your_skin_name.css` and change the values.
Only `:root` — never add component CSS to a skin file.

```css
/*
 * Wadsworth Skin: YOUR SKIN NAME
 * Author: YOUR NAME
 * Description: ONE LINE DESCRIPTION
 * Tier: free | pro   (pro skins require active Wadsworth Pro subscription)
 *
 * Rules:
 *  - Only redefine :root variables. Never add component CSS here.
 *  - Every variable listed below MUST be defined — no skipping.
 *  - Test on: dashboard, /market, /businesses, /stats/leaderboard, /admin, /estate
 *  - Minimum contrast ratio 4.5:1 for all text on its background (WCAG AA).
 */

:root {

  /* ── Backgrounds ───────────────────────────────────────────── */
  --bg-page:       #020617;   /* main page background              */
  --bg-card:       #0f172a;   /* card / panel background           */
  --bg-card-2:     #1e293b;   /* nested containers, table rows     */
  --bg-input:      #1e293b;   /* form inputs, selects              */
  --bg-header:     #0b1220;   /* fixed top header bar              */
  --bg-ticker:     #0a1628;   /* fixed bottom ticker bar           */
  --bg-overlay:    rgba(0,0,0,0.6); /* modal overlay               */

  /* ── Borders ───────────────────────────────────────────────── */
  --border:        #1e293b;   /* primary card / input borders      */
  --border-subtle: #334155;   /* dividers, section separators      */
  --border-focus:  #38bdf8;   /* input focus ring                  */

  /* ── Text ──────────────────────────────────────────────────── */
  --text-primary:    #e5e7eb; /* body text                         */
  --text-secondary:  #94a3b8; /* labels, column headers            */
  --text-muted:      #64748b; /* disabled, placeholder             */
  --text-faint:      #475569; /* metadata, very subtle             */
  --text-on-accent:  #000000; /* text on accent-colored buttons    */

  /* ── Accent / Brand ────────────────────────────────────────── */
  --accent:          #38bdf8; /* primary — links, interactive      */
  --accent-dim:      #0ea5e9; /* pressed/hover state               */
  --accent-bg:       rgba(56,189,248,0.08); /* subtle accent tint  */
  --accent-2:        #f59e0b; /* secondary — warnings, alt buttons */
  --accent-2-dim:    #d97706; /* pressed/hover of accent-2         */
  --accent-3:        #a78bfa; /* events, trophies, level badges    */

  /* ── Semantic ──────────────────────────────────────────────── */
  --color-success:       #22c55e;
  --color-success-light: #4ade80;
  --color-success-bg:    rgba(34,197,94,0.08);
  --color-danger:        #ef4444;
  --color-danger-light:  #f87171;
  --color-danger-dark:   #dc2626;
  --color-danger-bg:     rgba(239,68,68,0.08);
  --color-warning:       #f59e0b;
  --color-warning-light: #fbbf24;
  --color-gold:          #d4af37; /* premium, medals, badges       */
  --color-orange:        #f97316; /* ask prices, orange items      */

}
```

---

## Skin Author Checklist

Before submitting a new skin:

- [ ] All 32 variables defined (no skipping)
- [ ] File in `static/skins/`, named with only `a-z`, `0-9`, `_` (no spaces)
- [ ] `Tier:` comment set to `free` or `pro`
- [ ] Tested on at minimum: `/` (dashboard), `/market`, `/businesses`, `/inventory`, `/stats/leaderboard`, `/admin`, `/estate`
- [ ] No component CSS in the file — variables only
- [ ] Text contrast passes WCAG AA (4.5:1) against its background
- [ ] `--text-on-accent` is readable on `--accent` background
- [ ] `--color-success` / `--color-danger` are distinguishable (not both green, not both red)

---

## Files That Will Change Per Phase

### Phase 1
- `auth.py` — add `skin` column to Player
- `ux.py` — `shell()` signature + `<link>` injection
- `stats_ux.py` — `stats_shell()` `<link>` injection
- `admins_ux.py` — `admin_shell()` `<link>` injection
- `estate_ux.py` — `death_shell()` `<link>` injection
- `settings_ux.py` — skin picker UI + save endpoint
- `static/skins/default.css` ← NEW
- `static/skins/wadsworth-base.css` ← NEW

### Phase 2 (CSS consolidation)
- `ux.py` — remove `<style>` block from `shell()`
- `stats_ux.py` — remove `<style>` block from `stats_shell()`
- `admins_ux.py` — remove `<style>` block from `admin_shell()`
- `estate_ux.py` — remove `<style>` block from `death_shell()`
- `static/skins/wadsworth-base.css` — expand with de-duplicated component CSS using `var()`
- `static/skins/modules/admin.css` ← NEW (admin-specific classes)
- `static/skins/modules/estate.css` ← NEW (estate-specific classes)

### Phase 3 (inline style remediation — per file, can be done incrementally)
- All 26 `*_ux.py` files — inline `style="color:#..."` → CSS class

### Phase 4 (new skins — no Python changes)
- `static/skins/<skin_name>.css` ← NEW per skin

---

## Open Questions

- **Skin names visible to players** — should display names be in the CSS comment header
  (parsed on load) or in a separate `skins_manifest.json`?
- **Subscriber gate** — skin picker reads `player.subscriber` flag; pro skins hidden/greyed
  when `subscriber == False`. Confirm this is the right UX vs. showing a lock icon.
- **Admin skins** — should admins get all skins regardless of subscription?
- **Preview** — live preview before saving (JS swaps the `<link>` href client-side) or
  save-and-reload? Live preview is one line of JS; save-and-reload is simpler.
- **Cache busting** — `?v=N` version param: bump manually on deploy, or hash-based?
