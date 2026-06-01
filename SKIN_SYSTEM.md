# Wadsworth Skin System — Design Document

> **Last updated:** 2026-06-01  
> Any future Claude session implementing or extending skins should start here.
> This document is the single source of truth — no re-audit of the codebase needed.

---

## Audit Summary

| Metric | Value |
|--------|-------|
| HTML-generating Python files | 26 |
| Total lines generating HTML | ~63,000 |
| Unique hex color values | 601+ |
| CSS variables in default.css | 140 |
| Independent shell functions | 15 (see full table below) |
| Delegating shell functions (no changes needed) | 3 |
| CSS classes across all shells | 170+ |
| Inline `style=""` attributes | 6,655+ |
| Lines of CSS in shell `<style>` blocks | ~1,200 (to be extracted to wadsworth-base.css) |
| HTML routes | 100+ |
| Static file serving | ✅ Already wired (`app.py:554`) |

---

## Resolved Design Decisions

### Skin display names
The settings picker shows a **human-readable display name** like "Polished Cyberpunk",
not the filename `shine_gloss_cyberpunk2`. The display name is parsed from the `Description:`
comment in the skin file header. The picker reads this line and capitalises the words.

### Subscriber gate UX
- **All players** can open the skin picker and **preview** any skin live
- Previewing a non-subscribed pro skin temporarily switches it client-side
- When a non-subscriber **leaves the picker page**, it reverts to their last saved skin
- Only **Wadsworth Pro subscribers** can **save** a skin selection permanently
- Free players can save any `Tier: free` skin

### Cache busting
Browser caches save CSS files so players don't re-download them on every page load.
When a CSS file is updated on the server the browser may still show the old version.
The `?v=N` number appended to the `<link href>` forces the browser to treat it as a
new file and fetch fresh. **Resolution: increment `?v=` manually on each deploy.**
This is a 1-line change and requires no automated system.

---

## Static File Serving

**Already configured.** `app.py:554`:
```python
app.mount("/static", StaticFiles(directory="static"), name="static")
```

`/static/skins/` is already reachable. No new routes needed.

**Head injection pattern — order matters:**
```html
<!-- 1. Component styles (shared, uses CSS variables) -->
<link rel="stylesheet" href="/static/skins/wadsworth-base.css?v=1">
<!-- 2. Player's chosen skin (defines all CSS variables) -->
<link rel="stylesheet" href="/static/skins/{skin_name}.css?v=1">
<!-- 3. Module override (page-group-specific accent — only on relevant shells) -->
<link rel="stylesheet" href="/static/skins/modules/admin.css?v=1">
```

---

## All Shell Functions — Complete Injection Map

**A "shell function" is any Python function that returns a complete HTML document.**
All 15 independent shells need patching in Phase 1. The 3 delegating ones inherit
automatically once `ux.shell()` is patched.

### Independent shells (need direct patching)

| Function / Constant | File | Approx. Line | Module override needed? | Notes |
|---------------------|------|-------------|------------------------|-------|
| `shell()` | `ux.py` | 600 | — | Core; all primary game pages |
| `stats_shell()` | `stats_ux.py` | 435 | — | All `/stats/*` pages |
| `admin_shell()` | `admins_ux.py` | 73 | `modules/admin.css` | Red accent |
| `death_shell()` | `estate_ux.py` | 44 | — | `/estate/*` pages |
| `chat_shell()` | `chat_ux.py` | 113 | — | Chat rooms |
| `_LEATHER_HEAD` | `company_ux.py` | ~50 | — | Leather/company theme constant |
| Corporate actions pages | `corporate_actions_ui.py` | 252, 1342, 1521, 1651 | — | Multiple separate full-page returns |
| City pages | `cities_ux.py` | 398, 583, 1573 | — | Multiple city management pages |
| County pages | `counties_ux.py` | 757, 961, 1068, 1148, 1308, 1646, 1931, 2115, 2987 | — | 9 occurrences |
| Executive shell | `executive_ux.py` | 364 | `modules/executive.css` | Purple accent |
| DM shell | `dm_ux.py` | 102 | — | Direct messages |
| Mod shell | `mod_ux.py` | 43 | — | Moderator tools |
| Meme coin pages | `memecoins_ux.py` | 378, 535, 616, 990, 2362 | `modules/memecoins.css` | Orange accent; multiple pages |
| Reserve banks shell | `reserve_banks_ux.py` | 119 | — | Banking / currency pages |
| Login / register | `auth.py` | ~622 | — | First page players see |

### Delegating shells (no changes — inherit automatically)

| Function | File | Delegates to |
|----------|------|-------------|
| `shell()` | `districts_ux.py` | `ux.shell()` |
| `shell()` | `p2p_ux.py` | `ux.shell()` |
| `shell()` | `trusted_trade_ux.py` | `ux.shell()` |

---

## Module Overrides

Four page groups use a different primary accent to signal a distinct context.
Each has a `modules/*.css` file loaded as a third `<link>` tag, **after** the
player's skin file, overriding just the accent-related variables.

| File | Pages | Accent | Rationale |
|------|-------|--------|-----------|
| `modules/admin.css` | `/admin/*` | 🔴 Red `#ef4444` | Staff see red → immediately know they're in admin |
| `modules/executive.css` | `/executives/*` | 🟣 Purple `#c084fc` | Prestige / power aesthetic for exec management |
| `modules/memecoins.css` | `/memecoins/*` | 🟠 Orange `#f59e0b` | Chaotic-energy palette matching meme speculation |
| `modules/mod.css` | `/mod/*` | 🟣 Violet `#7c3aed` | Darker bg + violet accent signals moderation context |

**Skin authors:** you do not need to account for any of these files.
They are applied automatically on top of any skin.

---

## CSS Variable Taxonomy (140 variables)

All 140 variables are defined in `static/skins/default.css`.

Variables are split into three tiers:
- **Core UI (79 vars)** — every skin MUST define all of these
- **Specialty Themes (22 vars)** — subsystems with their own visual language (loader,
  audio, leather/company, wiki); most skins define these but can leave them as-is
- **Semantic data (39 vars)** — game-specific meaning; most skins can leave as-is or
  omit entirely (they fall back to the `default.css` definitions)

### CORE UI (79 vars)

#### Backgrounds (7)
| Variable | Default | Role |
|----------|---------|------|
| `--bg-page` | `#020617` | Main page background |
| `--bg-card` | `#0f172a` | Card / panel background |
| `--bg-card-2` | `#1e293b` | Nested containers, alt rows, modals |
| `--bg-input` | `#1e293b` | Form inputs, selects, textareas |
| `--bg-header` | `#0b1220` | Fixed top header bar |
| `--bg-ticker` | `#0a1628` | Fixed bottom live-price ticker |
| `--bg-overlay` | `rgba(0,0,0,0.6)` | Modal / drawer overlay |

#### Borders (3)
| Variable | Default | Role |
|----------|---------|------|
| `--border` | `#1e293b` | Primary card / input borders |
| `--border-subtle` | `#334155` | Dividers, section separators |
| `--border-focus` | `#38bdf8` | Input focus ring |

#### Text (7)
| Variable | Default | Role |
|----------|---------|------|
| `--text-primary` | `#e5e7eb` | Body text, general content |
| `--text-bright` | `#f1f5f9` | Emphasized values, stat numbers |
| `--text-secondary` | `#94a3b8` | Labels, column headers, captions |
| `--text-muted` | `#64748b` | Disabled, placeholder, de-emphasized |
| `--text-faint` | `#475569` | Metadata, timestamps, very subtle text |
| `--text-on-accent` | `#000000` | Text placed ON an accent-colored background |
| `--text-on-danger` | `#ffffff` | Text placed ON a danger-colored background |

#### Accent / Brand (9)
| Variable | Default | Role |
|----------|---------|------|
| `--accent` | `#38bdf8` | Primary — links, interactive, highlights |
| `--accent-dim` | `#0ea5e9` | Hover / pressed state |
| `--accent-bg` | `rgba(56,189,248,0.08)` | Subtle tint on cards |
| `--accent-2` | `#f59e0b` | Secondary — warnings, alt buttons |
| `--accent-2-dim` | `#d97706` | Hover / pressed of accent-2 |
| `--accent-2-bg` | `rgba(245,158,11,0.08)` | Subtle accent-2 tint |
| `--accent-3` | `#a78bfa` | Tertiary — events, trophies, level badges |
| `--accent-3-dim` | `#7c3aed` | Hover / pressed of accent-3 |
| `--accent-3-bg` | `rgba(167,139,250,0.08)` | Subtle accent-3 tint |

#### Semantic Colors (20)
| Variable | Default | Role |
|----------|---------|------|
| `--color-success` | `#22c55e` | Gains, positive values, online |
| `--color-success-light` | `#4ade80` | Success highlights |
| `--color-success-dark` | `#16a34a` | Pressed / dark variant |
| `--color-success-bg` | `rgba(34,197,94,0.08)` | Success card tint |
| `--color-danger` | `#ef4444` | Errors, losses, bans |
| `--color-danger-light` | `#f87171` | Error highlights |
| `--color-danger-dark` | `#dc2626` | Critical / permanent-action |
| `--color-danger-xdark` | `#7f1d1d` | Danger button fill |
| `--color-danger-bg` | `rgba(239,68,68,0.08)` | Danger card tint |
| `--color-warning` | `#f59e0b` | Warnings, alerts |
| `--color-warning-light` | `#fbbf24` | Warning highlights |
| `--color-warning-bg` | `rgba(245,158,11,0.08)` | Warning card tint |
| `--color-gold` | `#d4af37` | Premium badge, subscriber marker |
| `--color-gold-bg` | `rgba(212,175,55,0.10)` | Gold card tint |
| `--color-orange` | `#f97316` | Ask prices, orange-coded items |
| `--color-purple` | `#a78bfa` | Level badges |
| `--color-teal` | `#0d9488` | Teal economy indicators |
| `--color-pink` | `#ec4899` | Pink event / contract badges |
| `--color-lime` | `#84cc16` | Land transactions, land badges |
| `--color-sky` | `#60a5fa` | DM / message badges, info tints |

#### Medals (3)
| Variable | Default | Role |
|----------|---------|------|
| `--color-rank-1` | `#d4af37` | Gold — 1st place |
| `--color-rank-2` | `#c0c0c0` | Silver — 2nd place |
| `--color-rank-3` | `#cd7f32` | Bronze — 3rd place |

#### Fonts (4)
| Variable | Default | Role |
|----------|---------|------|
| `--font-body` | `'JetBrains Mono', 'Courier New', monospace` | All page body text |
| `--font-serif` | `Georgia, serif` | Audio player, estate cert-card headings |
| `--font-cursive` | `'Caveat', cursive` | Decorative callouts |
| `--font-sans` | `'Segoe UI', system-ui, sans-serif` | Fallback sans-serif |

#### Border Radius (7)
| Variable | Default | Role |
|----------|---------|------|
| `--radius-sm` | `3px` | Badges, small tags |
| `--radius-md` | `4px` | Standard buttons, inputs |
| `--radius-lg` | `8px` | Cards, panels |
| `--radius-xl` | `12px` | Large cards, modals |
| `--radius-2xl` | `20px` | Extra-large chips |
| `--radius-pill` | `9999px` | Pill buttons |
| `--radius-circle` | `50%` | Avatar circles |

#### Z-Index Stacking (5)
| Variable | Default | Role |
|----------|---------|------|
| `--z-below` | `-1` | Behind flow (pseudo-elements) |
| `--z-base` | `100` | Search bars, filter overlays |
| `--z-audio` | `150` | Audio player bar (#gs-bar) |
| `--z-ticker` | `1000` | Fixed bottom ticker |
| `--z-modal` | `9999` | Modals, nav-loader overlay |

#### Shadows (4)
| Variable | Default | Role |
|----------|---------|------|
| `--shadow-sm` | `0 1px 4px rgba(0,0,0,0.6)` | Small depth (knobs) |
| `--shadow-md` | `0 4px 20px rgba(0,0,0,0.7)` | Panels, audio player |
| `--shadow-glow` | `0 8px 25px rgba(56,189,248,0.15)` | Card hover cyan glow |
| `--shadow-glow-danger` | `0 8px 25px rgba(239,68,68,0.15)` | Danger card glow |

#### Transitions (3)
| Variable | Default | Role |
|----------|---------|------|
| `--dur-fast` | `0.15s` | Micro-interactions |
| `--dur-normal` | `0.2s` | Standard hover / focus |
| `--dur-slow` | `2s` | lien-pulse, scroll title |

#### Gradients (7)
| Variable | Default | Role |
|----------|---------|------|
| `--grad-card` | `linear-gradient(135deg, var(--bg-card) 0%, var(--bg-card-2) 100%)` | Stats card backgrounds |
| `--grad-bar` | `linear-gradient(to top, var(--accent), var(--accent-dim))` | Mini progress bars |
| `--grad-cert` | `linear-gradient(135deg, #0a0a14 0%, #111827 100%)` | Estate cert-card body |
| `--grad-cert-border` | `linear-gradient(90deg, var(--border-subtle), var(--border), var(--border-subtle))` | Cert-card top border |
| `--grad-delete-zone` | `linear-gradient(135deg, #0a0a14 0%, #1a0a0a 100%)` | Estate delete zone |
| `--grad-audio-knob` | `linear-gradient(to bottom, #3d2b1f, #1a0f0a)` | Audio tuner knob |
| `--grad-kpi` | `linear-gradient(135deg, #080f1e 0%, #0d1829 100%)` | KPI / stats-page card body |

---

### SPECIALTY THEMES (22 vars)

Subsystems that have their own visual language distinct from the main game UI.
Skins that target a different aesthetic should override these too, but they're optional —
omitting them falls back to the `default.css` mahogany / parchment / wiki values.

#### Nav-Loader / Loading Screen (2)
The page transition overlay shares the mahogany aesthetic with the audio player.
The `--audio-*` variables drive most of the loader look; only two are unique.

| Variable | Default | Role |
|----------|---------|------|
| `--loader-border` | `#2d1810` | Card outer border ring |
| `--loader-bar-start` | `#8b4513` | Progress bar gradient left (sienna) |

Cross-references to `--audio-*` in the loader:
- Loader body background → `--audio-bg-dark`
- Loader text / title colour → `--audio-accent`
- Loader progress bar mid → `--audio-accent`
- Loader progress bar end → `#f5f5dc` (cream — fixed, not a variable)

#### Audio Player — Mahogany / Vintage Hi-Fi (5)
| Variable | Default | Role |
|----------|---------|------|
| `--audio-bg-dark` | `#1a0f0a` | Tuner body background |
| `--audio-bg-mid` | `#3d2b1f` | Knob gradient midpoint |
| `--audio-accent` | `#b08d57` | Dial highlights, station name colour |
| `--audio-font` | `var(--font-serif)` | Station name / readout font |
| `--audio-pastels-json` | (15-colour JSON string) | Pastel cycle per station (read by JS) |

Full pastel array: `#FFB7B2 #FFDAC1 #E2F0CB #B5EAD7 #C7CEEA #FF9AA2 #F8BBD0 #E1BEE7 #D1C4E9 #BBDEFB #C8E6C9 #F0F4C3 #FFF9C4 #FFE0B2 #F5F5DC`

#### Company Pages — Leather & Parchment (6)
Company and ledger pages (`_LEATHER_HEAD` constant in `company_ux.py`) use a handwritten
journal aesthetic that is completely distinct from the rest of the game: dark walnut sidebar,
cream parchment main body, tan ink. Also uses `--font-cursive` ('Caveat') for ledger headings.

| Variable | Default | Role |
|----------|---------|------|
| `--leather-bg-dark` | `#1a0e06` | Walnut brown — sidebar, dark areas |
| `--leather-bg-light` | `#f5ead0` | Cream parchment — main content area |
| `--leather-text` | `#2a1505` | Dark brown ink for body text |
| `--leather-accent` | `#c9a97a` | Tan — borders, highlights, nav |
| `--leather-accent-2` | `#6b3a1f` | Dark tan — links, pressed states |
| `--leather-border` | `#2d1810` | Same dark border as `--loader-border` |

#### WikiWads — Encyclopedia Theme (9)
The wiki / encyclopedia (`wiki_shell()` in `stats_ux.py`) uses a completely different
3-colour accent palette from the rest of the game. The palette follows a 10/30/60 rule:
primary orange (headings, CTAs), secondary yellow (highlights), tertiary blue (body accents).

| Variable | Default | Role |
|----------|---------|------|
| `--wiki-bg-page` | `#04070f` | Deeper black than main `--bg-page` |
| `--wiki-bg-card` | `#090e1c` | Wiki card background |
| `--wiki-bg-card-2` | `#0c1528` | Wiki nested / alt background |
| `--wiki-border` | `#1d2f55` | Wiki card and section borders |
| `--wiki-text` | `#dde8ff` | Wiki body text (cooler white) |
| `--wiki-text-muted` | `#607098` | Wiki muted text, metadata |
| `--wiki-accent-1` | `#f5a855` | Primary — orange (10%) headings, CTAs |
| `--wiki-accent-2` | `#f5d76e` | Secondary — yellow (30%) highlights |
| `--wiki-accent-3` | `#90c4f0` | Tertiary — blue (60%) body accents |

---

### WORLD MAP — EXCLUDED FROM SKIN SYSTEM

The world map renders terrain via canvas and the terrain colours are hardcoded
in game logic. Skinning the world map terrain is out of scope — the 13 terrain
colour values (`prairie`, `forest`, `desert`, `marsh`, `mountain`, `tundra`,
`jungle`, `savanna`, `hills`, `island`, `coastal`, `lake`, `ocean`) are **not**
CSS variables and do not live in any skin file.

---

### SEMANTIC DATA (39 vars)

Game-specific meaning. Most skins leave these unchanged — they encode information
(green = gain, red = loss, etc.). Override only if your skin breaks the visual
logic they represent.

#### Transaction Ledger Badge Colors (13)
Each transaction type has a coloured left-bar accent in the ledger rows.
These are sourced from `TYPE_BADGE_COLORS` dict in `stats_ux.py`.

| Variable | Default | Transaction types covered |
|----------|---------|--------------------------|
| `--tx-market` | `#3b82f6` | market_buy, market_sell |
| `--tx-resource` | `#0ea5e9` | resource_gain, resource_loss, resource_use |
| `--tx-cash-in` | `#22c55e` | cash_in |
| `--tx-cash-out` | `#ef4444` | cash_out |
| `--tx-business` | `#8b5cf6` | retail_sale, business_startup |
| `--tx-land` | `#84cc16` | land_buy, land_sell |
| `--tx-district` | `#f59e0b` | district_merge, district_tax |
| `--tx-crypto` | `#f59e0b` | crypto_buy, crypto_sell, crypto_swap |
| `--tx-bonds` | `#0891b2` | bond_purchase, bond_sell, bond_maturity, bond_called |
| `--tx-shares` | `#3b82f6` | share_buy, share_sell |
| `--tx-dividend` | `#22c55e` | dividend (received), annuity_interest |
| `--tx-tax` | `#f97316` | tax |
| `--tx-p2p` | `#6366f1` | p2p_contract_acquired, p2p_contract_sold, p2p_breach_penalty |

#### Chart.js / Canvas Colors (8)
Used in Chart.js config objects generated in Python HTML strings.
In Phase 3 these will be read via `getComputedStyle` so charts respond to skin changes.

| Variable | Default | Role |
|----------|---------|------|
| `--chart-income` | `rgba(34,197,94,0.7)` | Income bar fill |
| `--chart-expense` | `rgba(239,68,68,0.65)` | Expense bar fill |
| `--chart-line` | `#38bdf8` | Net position line colour |
| `--chart-line-fill` | `rgba(56,189,248,0.07)` | Net position area fill |
| `--chart-tooltip-bg` | `#0f172a` | Tooltip background |
| `--chart-tooltip-border` | `#334155` | Tooltip border |
| `--chart-grid` | `#111827` | Grid lines |
| `--chart-tick` | `#475569` | Axis tick labels |

#### Chat Mention Highlights (5)
| Variable | Default | Role |
|----------|---------|------|
| `--mention-player` | `#22c55e` | @player mention chip |
| `--mention-item` | `#38bdf8` | Item mention chip |
| `--mention-crypto` | `#fbbf24` | Crypto mention chip |
| `--mention-stock` | `#f97316` | Stock mention chip |
| `--chat-mod-accent` | `#f59e0b` | Moderator message left border |

#### Notification Badge — Header 📒 Icon (2)
| Variable | Default | Role |
|----------|---------|------|
| `--notif-badge` | `#ef4444` | Unread count text colour |
| `--notif-badge-bg` | `rgba(239,68,68,0.13)` | Unread count background |

#### Notification Type Badge Colors — Expanded Panel (9)
Each notification type in the expanded notification panel has a coloured badge.
Source: notification rendering in `ux.py` ~lines 3726–3872.

| Variable | Default | Notification types covered |
|----------|---------|---------------------------|
| `--notif-market` | `#f59e0b` | MARKET — trade alerts |
| `--notif-corporate` | `#38bdf8` | CORPORATE — acquisition / merger |
| `--notif-execs` | `#a78bfa` | EXECUTIVES — exec hire / fire / events |
| `--notif-general` | `#64748b` | NOTICE — general system messages |
| `--notif-govt` | `#22c55e` | GOVERNMENT — city / county / district |
| `--notif-business` | `#fb923c` | BUSINESS — production, retail |
| `--notif-land` | `#84cc16` | LAND — plot purchases, land events |
| `--notif-contract` | `#f472b6` | CONTRACT — P2P contract alerts |
| `--notif-dm` | `#60a5fa` | MESSAGE — direct messages |

#### Direct Messages / DM (2)
| Variable | Default | Role |
|----------|---------|------|
| `--dm-own-accent` | `#c084fc` | Own outgoing message bubble / accent |
| `--dm-unread` | `#c084fc` | Unread conversation badge |

---

## Animations and Keyframes

These live in `wadsworth-base.css`. They are not variables — they reference variables for colour.

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

@keyframes nl-pulse-anim {          /* nav-loader breathing effect */
  0%, 100% { opacity: 0.3; }
  50%       { opacity: 0.7; }
}
```

---

## CSS Classes — Master List for `wadsworth-base.css`

`wadsworth-base.css` (Phase 2) extracts all 170+ component classes from the shell
`<style>` blocks and converts hardcoded hex to `var()`.

### Layout
`body` `a` `* {box-sizing}` `.container` `.grid` `.grid-2` `.grid-3`

### Header & Navigation
`.header` `.brand` `.brand img` `.header-right` `.balance`
`.nav` `.nav a` `.nav a:hover` `.nav a.active` `.nav::-webkit-scrollbar`

### Cards
`.card` `.card:hover` `.card-header` `.card-title` `.card-value` `.card-subtitle` `.card-icon`
`.cert-card` `.cert-card::before` `.cert-header` `.cert-title` `.cert-badge` `.cert-badge-idle` `.cert-badge-voluntary`
`.card-special` (executive gold border) `.card-quit` (executive red border)
`.link-card` `.link-card:hover` `.lc-icon` `.lc-title` `.lc-desc` `.link-grid`

### Buttons (17 variants)
`.btn` `.btn-blue` `.btn-orange` `.btn-red` `.btn-gold`
`.btn-danger` `.btn-danger:hover` `.btn-secondary` `.btn-secondary:hover`
`.btn-primary` `.btn-primary:hover`
`.btn-yellow` `.btn-yellow:hover` `.btn-green` `.btn-green:hover`
`.btn-gray` `.btn-gray:hover`
`.btn-buy` `.btn-sell` `.btn-meme` (meme coins)

### Badges (13 variants)
`.badge` `.badge-gold` `.badge-silver` `.badge-bronze`
`.badge-blue` `.badge-green` `.badge-gray` `.badge-red` `.badge-yellow`
`.badge-meme` `.badge-native` `.badge-buy` `.badge-sell`
`.exec-special-tag` `.exec-title` (executive page)

### Stats & Data Display
`.stat-row` `.stat-row:last-child` `.stat-label` `.stat-value`
`.stat-value.positive` `.stat-value.negative`
`.stat-grid` `.stat-box`
`.page-title` `.page-subtitle`

### Executive-Specific
`.exec-name` `.exec-title` `.ability-chip` `.ability-name`
`.legendary-ability` `.legendary-ability-name` `.perf-meter`

### Tables
`.table-wrap` `.table` `.table th` `.table th:hover` `.table td` `.table tr:hover`

### Forms & Inputs
`input` `select` `textarea` `input:focus` `select:focus` `textarea:focus`
`.search-box` `.search-box:focus`
`.form-row` `.form-row > *` `.form-row .btn` `.form-label`

### Filters & Tabs
`.filter-tabs` `.filter-tab` `.filter-tab:hover` `.filter-tab.active`
`.tabs` `.tabs a` `.tabs a:hover` `.tabs a.active`

### Transaction Ledger
`.txr` (transaction row) `.txchip` (filter chips) `.txsort` (sort buttons)
Active states for both use `--accent-3` (indigo) for sort, `--accent` (blue) for filter

### Charts & Visualisation
`.chart-container` `.mini-chart` `.mini-chart-bar` `.progress` `.progress-bar`

### Chat-Specific
`.chat-msg` `.chat-msg-avatar` `.chat-msg-avatar-letter`
`.chat-msg.system-msg` `.chat-msg.patch-note-msg`
`.chat-input-bar` `.chat-input-bar input:focus` `.chat-input-bar button`
`.emoji-picker`
`.mention-player` `.mention-item` `.mention-crypto` `.mention-stock`

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
`.notif-row` (notification panel rows)

### Status Helpers (replaces Python status-color dicts)
`.status-critical` `.status-warning` `.status-ok`
`.positive` `.negative` (meme coins + general)

### Lien
`.lien-critical` (animation applied here)

### Ticker
`.ticker` `#tkViewport` `.ticker-controls` `.ticker-btn` `.ticker-btn:hover` `.ticker-btn.active`

### WikiWads Pages
`.wh` (wiki hero/header) `.wn` (wiki nav) `.wm` (wiki main area)
`.wpt` (wiki page title) `.ws` (wiki section) `.wg` (wiki grid)
`.wc` (wiki card) `.wb` (wiki body text) `.wkv` (wiki key-value row) `.whero` (wiki hero image)
Orange headings use `--wiki-accent-1`; yellow highlights `--wiki-accent-2`; blue links `--wiki-accent-3`

### Company / Ledger (Leather Theme)
`.ledger` (main company journal page) `.nav-pill` (sidebar nav pills)
Body background → `--leather-bg-light`; sidebar → `--leather-bg-dark`; ink → `--leather-text`

### Misc
`.divider` `.detail-section` `.detail-title` `.recipe-item` `.recipe-arrow`

### Responsive
`@media (max-width: 640px)` `@media (max-width: 480px)` `@media (min-width: 640px)`

---

## Python Status Color Dicts

Several Python files compute `style="color:{hex}"` via dicts. Convert to CSS classes.

```python
# Before:
status_colors = {"critical": "#dc2626", "warning": "#f59e0b", "ok": "#64748b"}
html = f'<span style="color:{status_colors[s]};">{label}</span>'

# After:
html = f'<span class="status-{s}">{label}</span>'
```

```css
.status-critical { color: var(--color-danger-dark); }
.status-warning  { color: var(--color-warning); }
.status-ok       { color: var(--text-muted); }
```

**Files with status-color dicts to convert:**
- `ux.py` — lien status (critical / warning / ok)
- `admins_ux.py` — player status (banned, muted, online, suspended)
- `stats_ux.py` — economy health
- `districts_ux.py` — district status
- `counties_ux.py` — county health

---

## SVG / Icon Fill Colors

Known fills → CSS class conversions (Phase 3):
```
fill="#22c55e" → class="svg-success"  → fill: var(--color-success)
fill="#ef4444" → class="svg-danger"   → fill: var(--color-danger)
fill="#475569" → class="svg-faint"    → fill: var(--text-faint)
fill="#64748b" → class="svg-muted"    → fill: var(--text-muted)
fill="#607098" → class="svg-series"   → fill: var(--accent-3-dim)
fill="#e2e8f0" → class="svg-light"    → fill: var(--text-secondary)
fill="#000000" → class="svg-dark"     → fill: var(--text-on-accent)
```

---

## Chart.js Color Integration (Phase 3)

Chart.js config objects in Python HTML strings currently use hardcoded hex.
In Phase 3, wire them to read CSS variables:

```javascript
const root = document.documentElement;
const cv = (v) => getComputedStyle(root).getPropertyValue(v).trim();

// Replace hardcoded colors:
backgroundColor: cv('--chart-income'),   // was 'rgba(34,197,94,0.7)'
borderColor:     cv('--chart-line'),      // was '#38bdf8'
// etc.
```

This makes charts respond to skin changes without a page reload.

---

## Implementation Plan

### Phase 1 — Plumbing (2–3 sessions due to 15 independent shells)
Goal: skin selection works end-to-end. No visual change for players yet.

**Changes:**
1. `auth.py` — add `skin = Column(String(64), default="default", nullable=False)` to `Player`
2. Patch all **15 independent shell functions** to inject two (or three) `<link>` tags
   - Priority order: `ux.py` → `stats_ux.py` → `admins_ux.py` → `estate_ux.py` → remaining 11
   - Each shell gets a `skin` param (loaded from `player.skin`)
   - Admin shell gets third tag: `modules/admin.css`
   - Executive shell gets third tag: `modules/executive.css`
   - Memecoins pages get third tag: `modules/memecoins.css`
3. `settings_ux.py` — add skin picker tab: `<select>` of available skins (glob `static/skins/*.css`, exclude `wadsworth-base.css` and `modules/`); display names from CSS `Description:` header comment; pro skins shown but disabled for non-subscribers; live preview swaps `<link>` href client-side; save button only available to subscribers
4. Static files: `default.css` ✅, `modules/admin.css` ✅, `modules/executive.css` ✅, `modules/memecoins.css` ✅

**Verification:** DevTools shows correct `<link>` tags on each page type →
default.css vars resolve → page looks identical to today.

---

### Phase 2 — CSS Consolidation (2–3 sessions)
Goal: extract ~1,200 lines of duplicated shell CSS into `wadsworth-base.css`.

1. Diff all 15 shell `<style>` blocks to find shared vs. unique classes
2. Shared classes → `wadsworth-base.css` with `var()` colours
3. Shell-specific classes → `modules/{module}.css`
4. Delete `<style>` block from each shell function after extraction
5. All gradients use gradient variables; all animations use `--dur-*`

**New files:** `wadsworth-base.css` (~1,400 lines), `modules/estate.css`, `modules/stats.css`, `modules/chat.css`

---

### Phase 3 — Inline Style Remediation (many sessions)
Goal: convert 6,655 inline `style="color:#..."` attributes to CSS classes.
**Not required for skins to work** — Phase 2 is sufficient. Phase 3 improves
fidelity so inline-styled elements also respond to skin changes.

Priority: `ux.py` → `admins_ux.py` → `stats_ux.py` → `estate_ux.py` → all others
Also: Python status-color dicts → CSS classes; SVG fills → CSS classes; Chart.js → `getComputedStyle`

---

### Phase 4 — Skin Creation (ongoing)
One skin = one file in `static/skins/`. See template section.
Subscriber skins have `Tier: pro` in the comment header.

---

## Skin Template

Copy to `static/skins/your_skin_name.css`. Override values only. No component CSS.

```css
/*
 * Wadsworth Skin: YOUR DISPLAY NAME
 * Author: YOUR NAME
 * Description: ONE LINE — this text appears in the skin picker
 * Tier: free | pro
 *
 * Rules:
 *  - Define all CORE UI variables (79 vars). Specialty theme and semantic data
 *    vars are optional — omit them to inherit defaults from default.css.
 *  - No component CSS. Variables only.
 *  - Test pages: / · /market · /businesses · /inventory · /stats/leaderboard
 *                /stats/economy · /estate · /admin · /executives · /memecoins
 *                /wiki · /company · /notifications · settings skin picker
 *  - WCAG AA: all text ≥ 4.5:1 against its background.
 *  - --text-on-accent must be readable on --accent.
 *  - Light themes: override --grad-cert, --grad-delete-zone, --grad-audio-knob
 *    (they contain hardcoded dark hex values). Also override --leather-bg-dark
 *    and --wiki-bg-page (both are very dark by default).
 *  - If changing --accent, update --shadow-glow to match its rgba.
 *  - If changing --color-danger, update --shadow-glow-danger to match.
 */

:root {

  /* ═══════════════════════════════════════════════════════════
   * CORE UI — required in every skin (79 vars)
   * ═══════════════════════════════════════════════════════════ */

  /* ── Backgrounds ─────────────────────────────────────────── */
  --bg-page:         #020617;
  --bg-card:         #0f172a;
  --bg-card-2:       #1e293b;
  --bg-input:        #1e293b;
  --bg-header:       #0b1220;
  --bg-ticker:       #0a1628;
  --bg-overlay:      rgba(0,0,0,0.6);

  /* ── Borders ─────────────────────────────────────────────── */
  --border:          #1e293b;
  --border-subtle:   #334155;
  --border-focus:    #38bdf8;

  /* ── Text ────────────────────────────────────────────────── */
  --text-primary:    #e5e7eb;
  --text-bright:     #f1f5f9;
  --text-secondary:  #94a3b8;
  --text-muted:      #64748b;
  --text-faint:      #475569;
  --text-on-accent:  #000000;
  --text-on-danger:  #ffffff;

  /* ── Accent / Brand ──────────────────────────────────────── */
  --accent:          #38bdf8;
  --accent-dim:      #0ea5e9;
  --accent-bg:       rgba(56,189,248,0.08);
  --accent-2:        #f59e0b;
  --accent-2-dim:    #d97706;
  --accent-2-bg:     rgba(245,158,11,0.08);
  --accent-3:        #a78bfa;
  --accent-3-dim:    #7c3aed;
  --accent-3-bg:     rgba(167,139,250,0.08);

  /* ── Semantic Colors ─────────────────────────────────────── */
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
  --color-lime:           #84cc16;
  --color-sky:            #60a5fa;

  /* ── Medals ──────────────────────────────────────────────── */
  --color-rank-1:    #d4af37;
  --color-rank-2:    #c0c0c0;
  --color-rank-3:    #cd7f32;

  /* ── Fonts ───────────────────────────────────────────────── */
  --font-body:     'JetBrains Mono', 'Courier New', monospace;
  --font-serif:    Georgia, serif;
  --font-cursive:  'Caveat', cursive;
  --font-sans:     'Segoe UI', system-ui, sans-serif;

  /* ── Border Radius ───────────────────────────────────────── */
  --radius-sm:     3px;
  --radius-md:     4px;
  --radius-lg:     8px;
  --radius-xl:     12px;
  --radius-2xl:    20px;
  --radius-pill:   9999px;
  --radius-circle: 50%;

  /* ── Z-Index ─────────────────────────────────────────────── */
  --z-below:    -1;
  --z-base:     100;
  --z-audio:    150;
  --z-ticker:   1000;
  --z-modal:    9999;

  /* ── Shadows ─────────────────────────────────────────────── */
  --shadow-sm:          0 1px 4px rgba(0,0,0,0.6);
  --shadow-md:          0 4px 20px rgba(0,0,0,0.7);
  --shadow-glow:        0 8px 25px rgba(56,189,248,0.15);
  --shadow-glow-danger: 0 8px 25px rgba(239,68,68,0.15);

  /* ── Transitions ─────────────────────────────────────────── */
  --dur-fast:   0.15s;
  --dur-normal: 0.2s;
  --dur-slow:   2s;

  /* ── Gradients ───────────────────────────────────────────── */
  --grad-card:        linear-gradient(135deg, var(--bg-card) 0%, var(--bg-card-2) 100%);
  --grad-bar:         linear-gradient(to top, var(--accent), var(--accent-dim));
  --grad-cert:        linear-gradient(135deg, #0a0a14 0%, #111827 100%);
  --grad-cert-border: linear-gradient(90deg, var(--border-subtle), var(--border), var(--border-subtle));
  --grad-delete-zone: linear-gradient(135deg, #0a0a14 0%, #1a0a0a 100%);
  --grad-audio-knob:  linear-gradient(to bottom, #3d2b1f, #1a0f0a);
  --grad-kpi:         linear-gradient(135deg, #080f1e 0%, #0d1829 100%);


  /* ═══════════════════════════════════════════════════════════
   * SPECIALTY THEMES — optional but recommended (22 vars)
   * ═══════════════════════════════════════════════════════════ */

  /* ── Nav-Loader / Loading Screen (2) ─────────────────────── */
  --loader-border:    #2d1810;
  --loader-bar-start: #8b4513;

  /* ── Audio Player — Mahogany (5) ─────────────────────────── */
  --audio-bg-dark:    #1a0f0a;
  --audio-bg-mid:     #3d2b1f;
  --audio-accent:     #b08d57;
  --audio-font:       var(--font-serif);
  --audio-pastels-json: '["#FFB7B2","#FFDAC1","#E2F0CB","#B5EAD7","#C7CEEA","#FF9AA2","#F8BBD0","#E1BEE7","#D1C4E9","#BBDEFB","#C8E6C9","#F0F4C3","#FFF9C4","#FFE0B2","#F5F5DC"]';

  /* ── Company Pages — Leather & Parchment (6) ─────────────── */
  --leather-bg-dark:  #1a0e06;
  --leather-bg-light: #f5ead0;
  --leather-text:     #2a1505;
  --leather-accent:   #c9a97a;
  --leather-accent-2: #6b3a1f;
  --leather-border:   #2d1810;

  /* ── WikiWads Encyclopedia (9) ───────────────────────────── */
  --wiki-bg-page:    #04070f;
  --wiki-bg-card:    #090e1c;
  --wiki-bg-card-2:  #0c1528;
  --wiki-border:     #1d2f55;
  --wiki-text:       #dde8ff;
  --wiki-text-muted: #607098;
  --wiki-accent-1:   #f5a855;
  --wiki-accent-2:   #f5d76e;
  --wiki-accent-3:   #90c4f0;


  /* ═══════════════════════════════════════════════════════════
   * SEMANTIC DATA — omit to inherit defaults (39 vars)
   * ═══════════════════════════════════════════════════════════ */

  /* ── Transaction Ledger Badges ───────────────────────────── */
  --tx-market:    #3b82f6;
  --tx-resource:  #0ea5e9;
  --tx-cash-in:   #22c55e;
  --tx-cash-out:  #ef4444;
  --tx-business:  #8b5cf6;
  --tx-land:      #84cc16;
  --tx-district:  #f59e0b;
  --tx-crypto:    #f59e0b;
  --tx-bonds:     #0891b2;
  --tx-shares:    #3b82f6;
  --tx-dividend:  #22c55e;
  --tx-tax:       #f97316;
  --tx-p2p:       #6366f1;

  /* ── Chart.js Colors ─────────────────────────────────────── */
  --chart-income:         rgba(34,197,94,0.7);
  --chart-expense:        rgba(239,68,68,0.65);
  --chart-line:           #38bdf8;
  --chart-line-fill:      rgba(56,189,248,0.07);
  --chart-tooltip-bg:     #0f172a;
  --chart-tooltip-border: #334155;
  --chart-grid:           #111827;
  --chart-tick:           #475569;

  /* ── Chat Mentions ───────────────────────────────────────── */
  --mention-player:  #22c55e;
  --mention-item:    #38bdf8;
  --mention-crypto:  #fbbf24;
  --mention-stock:   #f97316;
  --chat-mod-accent: #f59e0b;

  /* ── Notification Badge ──────────────────────────────────── */
  --notif-badge:     #ef4444;
  --notif-badge-bg:  rgba(239,68,68,0.13);

  /* ── Notification Type Badge Colors ─────────────────────── */
  --notif-market:    #f59e0b;
  --notif-corporate: #38bdf8;
  --notif-execs:     #a78bfa;
  --notif-general:   #64748b;
  --notif-govt:      #22c55e;
  --notif-business:  #fb923c;
  --notif-land:      #84cc16;
  --notif-contract:  #f472b6;
  --notif-dm:        #60a5fa;

  /* ── Direct Messages ─────────────────────────────────────── */
  --dm-own-accent:   #c084fc;
  --dm-unread:       #c084fc;

}
```

---

## Skin Author Checklist

**Required (core UI — 79 vars):**
- [ ] All 79 core UI variables defined
- [ ] Filename: `a-z`, `0-9`, `_` only — no spaces, no uppercase
- [ ] `Description:` comment line present (shown in picker)
- [ ] `Tier: free` or `Tier: pro` comment set
- [ ] No component CSS — variables only

**Visual QA (test these pages):**
- [ ] `/` dashboard — cards, header, ticker, balance, nav
- [ ] `/market` — order book, bid/ask colours, filters
- [ ] `/businesses` — retail price forms, progress bars
- [ ] `/inventory` — category pills, value bars, list form
- [ ] `/stats/leaderboard` — rank badges (gold/silver/bronze), trophy column
- [ ] `/stats/economy` — charts, transaction ledger (tx badge colours), tax section
- [ ] `/estate` — cert-card gradient, delete zone
- [ ] `/admin` — red accent override visible, table rows, danger buttons
- [ ] `/executives` — purple accent override, gold card-special border
- [ ] `/memecoins` — orange accent override, buy/sell badge colours
- [ ] `/mod/*` — violet accent override, darker card bg
- [ ] `/wiki` / WikiWads — orange/yellow/blue triple-accent, distinct bg/card
- [ ] `/company` — leather parchment bg, walnut sidebar, tan ink, Caveat font
- [ ] `/notifications` — 9 type-badge colours visible, header badge colour
- [ ] `/dm` — own-message accent (purple), unread badge
- [ ] Settings skin picker — preview works, save disabled for non-subscribers
- [ ] Chat room — mention chips (4 colours), mod message border

**Contrast & accessibility:**
- [ ] All text ≥ 4.5:1 against background (WCAG AA)
- [ ] `--text-on-accent` readable on `--accent`
- [ ] `--color-success` and `--color-danger` visually distinct
- [ ] `--color-rank-1/2/3` read as prestige order (not all same hue)

**Light theme extra steps:**
- [ ] Override `--grad-cert` (hardcoded dark hex)
- [ ] Override `--grad-delete-zone` (hardcoded dark hex)
- [ ] Override `--grad-audio-knob` (hardcoded dark hex)
- [ ] Override `--grad-kpi` (hardcoded very dark hex)
- [ ] Override `--audio-*` (mahogany theme looks odd on a light background)
- [ ] Override `--leather-bg-dark` (very dark by default — invert for light themes)
- [ ] Override `--wiki-bg-page` and `--wiki-bg-card*` (nearly black by default)

**Shadow consistency:**
- [ ] `--shadow-glow` rgba matches `--accent` hue
- [ ] `--shadow-glow-danger` rgba matches `--color-danger` hue

---

## Files Changed Per Phase

### Phase 1 (plumbing)
- `auth.py` — add `skin` column to `Player`
- `ux.py` — `shell()` + `<link>` injection
- `stats_ux.py` — `stats_shell()` + `<link>` injection
- `admins_ux.py` — `admin_shell()` + 3 `<link>` tags (base + skin + modules/admin.css)
- `estate_ux.py` — `death_shell()` + `<link>` injection
- `chat_ux.py` — `chat_shell()` + `<link>` injection
- `company_ux.py` — `_LEATHER_HEAD` constant + `<link>` injection
- `corporate_actions_ui.py` — all 4 full-page HTML returns
- `cities_ux.py` — all 3 full-page HTML returns
- `counties_ux.py` — all 9 full-page HTML returns
- `executive_ux.py` — shell + 3 `<link>` tags (base + skin + modules/executive.css)
- `dm_ux.py` — shell + `<link>` injection
- `mod_ux.py` — shell + `<link>` injection
- `memecoins_ux.py` — all 5 full-page returns + modules/memecoins.css
- `reserve_banks_ux.py` — shell + `<link>` injection
- `auth.py` — login/register page + `<link>` injection
- `settings_ux.py` — skin picker tab UI + save endpoint
- `static/skins/default.css` ✅ done (140 vars)
- `static/skins/modules/admin.css` ✅ done
- `static/skins/modules/executive.css` ✅ done
- `static/skins/modules/memecoins.css` ✅ done
- `static/skins/modules/mod.css` ✅ done

### Phase 2 (CSS consolidation)
- `static/skins/wadsworth-base.css` ← NEW
- `static/skins/modules/estate.css` ← NEW
- `static/skins/modules/stats.css` ← NEW
- `static/skins/modules/chat.css` ← NEW
- All 15 shell functions — delete `<style>` blocks

### Phase 3 (inline style remediation — incremental)
All 26 `*_ux.py` files — inline styles → CSS classes

### Phase 4 (skin files)
`static/skins/<skin_name>.css` ← one per skin
