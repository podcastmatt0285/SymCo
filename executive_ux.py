"""
executive_ux.py

UX for the executive management system.
- Dashboard: view all hired executives with abilities, category badges, school progress
- Marketplace: browse by category, legendary section, clear ability descriptions
- School: enrolment confirmation showing school-discount sources
- Upgrade selection: clear "performance only, no new abilities" messaging
- API endpoints: hire, fire, school, upgrade
"""

from typing import Optional
from fastapi import APIRouter, Cookie, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter()


# ==========================
# HELPERS
# ==========================
def get_current_player(session_token: Optional[str]):
    from auth import get_player_from_session, get_db
    db     = get_db()
    player = get_player_from_session(db, session_token)
    db.close()
    return player


# ==========================
# STYLES
# ==========================
EXEC_STYLES = """
<style>
    * { margin:0; padding:0; box-sizing:border-box; }
    body {
        font-family: 'JetBrains Mono','Fira Code',monospace;
        background: #020617;
        color: #e5e7eb;
        min-height: 100vh;
        padding: 20px;
    }
    .container { max-width: 1300px; margin: 0 auto; }

    /* ── Header ─────────────────────────────────────────────────────── */
    .header {
        display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 24px; padding-bottom: 16px;
        border-bottom: 1px solid #1e293b;
    }
    .header h1 { font-size: 24px; color: #c084fc; }
    .nav-link {
        color: #38bdf8; text-decoration: none; font-size: 14px;
        padding: 8px 16px; border: 1px solid #38bdf8; border-radius: 6px;
    }
    .nav-link:hover { background: #38bdf822; }

    /* ── Nav row ─────────────────────────────────────────────────────── */
    .nav-row { display:flex; gap:12px; margin-bottom:20px; flex-wrap:wrap; }

    /* ── Cards ───────────────────────────────────────────────────────── */
    .card {
        background: #0f172a; border: 1px solid #1e293b;
        border-radius: 8px; padding: 20px; margin-bottom: 16px;
    }
    .card-special {
        background: #0f172a; border: 2px solid #d4af37;
        border-radius: 8px; padding: 20px; margin-bottom: 16px;
        box-shadow: 0 0 18px #d4af3744;
    }
    .card-quit {
        background: #0f172a; border: 2px solid #ef4444;
        border-radius: 8px; padding: 20px; margin-bottom: 16px;
        box-shadow: 0 0 12px #ef444422;
    }
    .exec-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
        gap: 16px;
    }

    /* ── Executive card internals ────────────────────────────────────── */
    .exec-name  { font-size: 18px; font-weight: bold; color: #f1f5f9; margin-bottom: 3px; }
    .exec-title { font-size: 13px; color: #d4af37; margin-bottom: 6px; font-style: italic; }
    .exec-desc  { font-size: 12px; color: #64748b; margin-bottom: 10px; }
    .exec-special-tag {
        display: inline-block; background: #d4af3722; color: #d4af37;
        padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;
        margin-bottom: 8px;
    }

    /* Category badge */
    .cat-badge {
        display: inline-block; padding: 2px 10px; border-radius: 4px;
        font-size: 11px; font-weight: bold; margin-bottom: 8px;
        text-transform: uppercase; letter-spacing: 0.05em;
    }

    /* ── Abilities section ───────────────────────────────────────────── */
    .abilities-section {
        background: #0a1020; border: 1px solid #1e293b44;
        border-radius: 6px; padding: 10px 12px; margin: 10px 0;
    }
    .abilities-header {
        font-size: 11px; font-weight: bold; color: #64748b;
        text-transform: uppercase; letter-spacing: 0.08em;
        margin-bottom: 6px;
    }
    .ability-chip {
        display: inline-flex; align-items: center; gap: 5px;
        background: #1e293b; border: 1px solid #334155;
        border-radius: 4px; padding: 3px 8px; margin: 2px;
        font-size: 11px; cursor: default; position: relative;
    }
    .ability-chip:hover .ability-tooltip { display: block; }
    .ability-name { color: #c084fc; font-weight: bold; }
    .ability-tooltip {
        display: none; position: absolute; bottom: calc(100% + 4px); left: 0;
        background: #0f172a; border: 1px solid #334155;
        padding: 8px 10px; border-radius: 6px; width: 220px; z-index: 20;
        font-size: 11px; color: #e5e7eb; white-space: normal; pointer-events: none;
        box-shadow: 0 4px 16px #00000066;
    }
    .legendary-ability {
        display: flex; align-items: flex-start; gap: 8px;
        background: #d4af3711; border: 1px solid #d4af3744;
        border-radius: 6px; padding: 8px 10px; margin-top: 8px;
        font-size: 12px;
    }
    .legendary-ability-name { color: #d4af37; font-weight: bold; }
    .legendary-ability-desc { color: #94a3b8; }

    /* ── Performance meter ───────────────────────────────────────────── */
    .perf-meter {
        background: #1e293b; border-radius: 6px; padding: 8px 12px;
        margin: 8px 0; display: flex; justify-content: space-between;
        align-items: center;
    }
    .perf-label { font-size: 11px; color: #64748b; }
    .perf-value { font-size: 13px; font-weight: bold; }

    /* ── Stat rows ───────────────────────────────────────────────────── */
    .stat-row {
        display: flex; justify-content: space-between;
        padding: 4px 0; border-bottom: 1px solid #1e293b44; font-size: 13px;
    }
    .stat-label { color: #94a3b8; }
    .stat-value { color: #e5e7eb; font-weight: bold; }
    .stat-value.green  { color: #22c55e; }
    .stat-value.orange { color: #f59e0b; }
    .stat-value.red    { color: #ef4444; }
    .stat-value.purple { color: #c084fc; }
    .stat-value.gold   { color: #d4af37; }
    .stat-value.blue   { color: #38bdf8; }

    /* ── Bars ────────────────────────────────────────────────────────── */
    .level-bar {
        width: 100%; height: 7px; background: #1e293b;
        border-radius: 4px; margin: 6px 0; overflow: hidden;
    }
    .level-fill {
        height: 100%; border-radius: 4px;
        background: linear-gradient(90deg, #38bdf8, #c084fc);
    }
    .school-bar .level-fill { background: linear-gradient(90deg, #f59e0b, #22c55e); }
    .age-bar .level-fill    { background: linear-gradient(90deg, #22c55e, #f59e0b, #ef4444); }
    .perf-bar .level-fill   { background: linear-gradient(90deg, #c084fc, #d4af37); }

    /* ── Alerts ──────────────────────────────────────────────────────── */
    .alert-warning {
        background: #f59e0b22; border: 1px solid #f59e0b;
        color: #f59e0b; padding: 8px 12px; border-radius: 6px; font-size: 12px;
        margin: 6px 0;
    }
    .alert-danger {
        background: #ef444422; border: 1px solid #ef4444;
        color: #ef4444; padding: 8px 12px; border-radius: 6px; font-size: 12px;
        margin: 6px 0;
    }
    .alert-success {
        background: #22c55e22; border: 1px solid #22c55e;
        color: #22c55e; padding: 8px 12px; border-radius: 6px; font-size: 12px;
        margin: 6px 0;
    }
    .alert-p2p {
        background: #f9a8d422; border: 1px solid #f9a8d4;
        color: #f9a8d4; padding: 8px 12px; border-radius: 6px; font-size: 12px;
        margin: 6px 0;
    }

    /* ── Buttons ─────────────────────────────────────────────────────── */
    .btn {
        display: inline-block; padding: 8px 16px; border-radius: 6px;
        text-decoration: none; font-size: 13px; font-weight: bold;
        cursor: pointer; border: none; font-family: inherit; text-align: center;
    }
    .btn-blue   { background: #38bdf8; color: #020617; }
    .btn-blue:hover { background: #7dd3fc; }
    .btn-orange { background: #f59e0b; color: #020617; }
    .btn-orange:hover { background: #fbbf24; }
    .btn-red    { background: #ef4444; color: #fff; }
    .btn-red:hover { background: #f87171; }
    .btn-green  { background: #22c55e; color: #020617; }
    .btn-green:hover { background: #4ade80; }
    .btn-purple { background: #c084fc; color: #020617; }
    .btn-purple:hover { background: #d8b4fe; }
    .btn-gold   { background: #d4af37; color: #020617; }
    .btn-gold:hover { background: #e5c54a; }
    .btn-small  { padding: 5px 12px; font-size: 12px; }
    .actions    { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }

    /* ── Messages ────────────────────────────────────────────────────── */
    .msg-success {
        background: #22c55e22; border: 1px solid #22c55e; color: #22c55e;
        padding: 12px; border-radius: 6px; margin-bottom: 16px;
    }
    .msg-error {
        background: #ef444422; border: 1px solid #ef4444; color: #ef4444;
        padding: 12px; border-radius: 6px; margin-bottom: 16px;
    }

    /* ── Flavor text ─────────────────────────────────────────────────── */
    .flavor-text {
        font-style: italic; color: #94a3b8; font-size: 12px;
        margin-top: 8px; padding: 8px; border-left: 2px solid #d4af37;
    }

    /* ── Badges ──────────────────────────────────────────────────────── */
    .badge {
        display: inline-block; padding: 2px 8px; border-radius: 4px;
        font-size: 11px; font-weight: bold; margin-right: 4px;
    }
    .badge-new         { background: #22c55e22; color: #22c55e; }
    .badge-fired       { background: #ef444422; color: #ef4444; }
    .badge-retired     { background: #f59e0b22; color: #f59e0b; }
    .badge-quit        { background: #dc262622; color: #dc2626; border: 1px solid #dc262666; }
    .badge-school      { background: #38bdf822; color: #38bdf8; }
    .badge-pension     { background: #c084fc22; color: #c084fc; }

    /* ── Summary grid ────────────────────────────────────────────────── */
    .summary-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
        gap: 12px; margin-bottom: 20px;
    }
    .summary-card {
        background: #1e293b; border-radius: 6px; padding: 12px; text-align: center;
    }
    .summary-card .label { color: #94a3b8; font-size: 12px; }
    .summary-card .value { font-size: 22px; font-weight: bold; color: #f1f5f9; }

    /* ── Category filter ─────────────────────────────────────────────── */
    .filter-row { display:flex; gap:8px; margin-bottom:16px; flex-wrap:wrap; align-items:center; }
    .filter-btn {
        padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold;
        cursor: pointer; border: 1px solid #334155; background: #1e293b;
        color: #94a3b8; text-decoration: none; font-family: inherit;
    }
    .filter-btn.active, .filter-btn:hover { border-color: #c084fc; color: #c084fc; }
    .filter-btn.cat-land      { border-color: #86efac44; }
    .filter-btn.cat-land.active, .filter-btn.cat-land:hover { border-color: #86efac; color: #86efac; }
    .filter-btn.cat-business  { border-color: #c084fc44; }
    .filter-btn.cat-business.active, .filter-btn.cat-business:hover { border-color: #c084fc; color: #c084fc; }
    .filter-btn.cat-sales     { border-color: #38bdf844; }
    .filter-btn.cat-sales.active, .filter-btn.cat-sales:hover { border-color: #38bdf8; color: #38bdf8; }
    .filter-btn.cat-production{ border-color: #f59e0b44; }
    .filter-btn.cat-production.active, .filter-btn.cat-production:hover { border-color: #f59e0b; color: #f59e0b; }
    .filter-btn.cat-taxes     { border-color: #fca5a544; }
    .filter-btn.cat-taxes.active, .filter-btn.cat-taxes:hover { border-color: #fca5a5; color: #fca5a5; }
    .filter-btn.cat-banking   { border-color: #22c55e44; }
    .filter-btn.cat-banking.active, .filter-btn.cat-banking:hover { border-color: #22c55e; color: #22c55e; }
    .filter-btn.cat-crypto    { border-color: #a78bfa44; }
    .filter-btn.cat-crypto.active, .filter-btn.cat-crypto:hover { border-color: #a78bfa; color: #a78bfa; }
    .filter-btn.cat-cities    { border-color: #67e8f944; }
    .filter-btn.cat-cities.active, .filter-btn.cat-cities:hover { border-color: #67e8f9; color: #67e8f9; }
    .filter-btn.cat-districts { border-color: #fbbf2444; }
    .filter-btn.cat-districts.active, .filter-btn.cat-districts:hover { border-color: #fbbf24; color: #fbbf24; }
    .filter-btn.cat-counties  { border-color: #d9f99d44; }
    .filter-btn.cat-counties.active, .filter-btn.cat-counties:hover { border-color: #d9f99d; color: #d9f99d; }
    .filter-btn.cat-p2p       { border-color: #f9a8d444; }
    .filter-btn.cat-p2p.active, .filter-btn.cat-p2p:hover { border-color: #f9a8d4; color: #f9a8d4; }

    /* ── Upgrade cards ───────────────────────────────────────────────── */
    .upgrade-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 16px;
    }
    .upgrade-option {
        background: #1e293b; border: 1px solid #334155;
        border-radius: 8px; padding: 18px; cursor: pointer;
        transition: border-color 0.2s, box-shadow 0.2s;
    }
    .upgrade-option:hover { border-color: #c084fc; box-shadow: 0 0 12px #c084fc22; }
    .upgrade-name { font-weight: bold; color: #c084fc; margin-bottom: 6px; font-size: 15px; }
    .upgrade-desc { font-size: 13px; color: #94a3b8; line-height: 1.5; }
    .upgrade-note {
        font-size: 11px; color: #22c55e; margin-top: 8px; padding: 4px 8px;
        background: #22c55e11; border-radius: 4px; display: inline-block;
    }

    /* ── Empty state ─────────────────────────────────────────────────── */
    .empty-state { text-align: center; padding: 40px; color: #64748b; }
    .empty-state h3 { color: #94a3b8; margin-bottom: 8px; }

    /* ── Responsive ──────────────────────────────────────────────────── */
    @media (max-width: 640px) {
        .exec-grid    { grid-template-columns: 1fr; }
        .summary-grid { grid-template-columns: 1fr 1fr; }
        .nav-row      { flex-direction: column; }
        .upgrade-grid { grid-template-columns: 1fr; }
    }
</style>
"""

# JS for category filter on marketplace
FILTER_JS = """
<script>
function filterCategory(cat) {
    document.querySelectorAll('.exec-cat-card').forEach(el => {
        if (cat === 'all' || el.dataset.cat === cat) {
            el.style.display = '';
        } else {
            el.style.display = 'none';
        }
    });
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.cat === cat);
    });
    // Hide section headers if all cards in section hidden
    document.querySelectorAll('.cat-section').forEach(sec => {
        const visible = [...sec.querySelectorAll('.exec-cat-card')]
            .some(el => el.style.display !== 'none');
        sec.style.display = visible ? '' : 'none';
    });
}
</script>
"""


def exec_shell(title: str, body: str, player=None) -> str:
    balance_html = ""
    if player:
        balance_html = f'<span style="color:#22c55e;">${player.cash_balance:,.2f}</span>'
    return f"""<!DOCTYPE html>
<html><head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Wadsworth — {title}</title>
    {EXEC_STYLES}
    {FILTER_JS}
</head><body>
<div class="container">
    <div class="header">
        <h1>{title}</h1>
        <div style="display:flex;gap:16px;align-items:center;">
            {balance_html}
            <a href="/" class="nav-link">Dashboard</a>
        </div>
    </div>
    {body}
</div>
</body></html>"""


# ==========================
# RENDER HELPERS
# ==========================

def _cat_badge(category: str) -> str:
    from executive import EXECUTIVE_CATEGORIES
    cat = EXECUTIVE_CATEGORIES.get(category, {"label": category, "color": "#94a3b8"})
    return (f'<span class="cat-badge" '
            f'style="background:{cat["color"]}22;color:{cat["color"]};'
            f'border:1px solid {cat["color"]}44;">'
            f'{cat["label"]}</span>')


def _ability_chips(exec_obj, show_school_mult: bool = True) -> str:
    from executive import EXEC_ABILITIES, get_school_performance_multiplier
    ability_keys = [a for a in (exec_obj.abilities or "").split(",") if a]
    if not ability_keys:
        return '<span style="color:#475569;font-size:12px;font-style:italic;">No ability data (legacy exec)</span>'

    chips = ""
    for key in ability_keys:
        adef = EXEC_ABILITIES.get(key, {})
        name = adef.get("name", key)
        desc = adef.get("desc", "")
        chips += f"""
        <span class="ability-chip">
            <span class="ability-name">{name}</span>
            <span class="ability-tooltip">{desc}</span>
        </span>"""
    return chips


def _school_perf_bar(exec_obj) -> str:
    from executive import get_school_performance_multiplier, SCHOOL_UPGRADES
    mult = get_school_performance_multiplier(exec_obj)
    if mult <= 1.0:
        return ""
    pct = min((mult - 1.0) / 4.0, 1.0) * 100  # 1x=0%, 5x=100%
    bonuses = [b for b in (exec_obj.bonuses or "").split(",") if b]
    labels = []
    for b in bonuses:
        for k, v in SCHOOL_UPGRADES.items():
            if v["bonus"] == b:
                labels.append(v["name"])
                break
    label_str = " → ".join(labels) if labels else "Trained"
    return f"""
    <div style="margin:8px 0;">
        <div style="display:flex;justify-content:space-between;font-size:11px;color:#94a3b8;margin-bottom:3px;">
            <span>School Performance</span>
            <span style="color:#c084fc;font-weight:bold;">{mult:.2f}x  ({label_str})</span>
        </div>
        <div class="level-bar perf-bar"><div class="level-fill" style="width:{pct:.0f}%"></div></div>
    </div>"""


def render_exec_card(ex, show_actions=True, is_owner=False, marketplace=False) -> str:
    from executive import (EXECUTIVE_JOBS, EXECUTIVE_CATEGORIES, PAY_CYCLE_LABELS,
                           PAY_CYCLES, LEGENDARY_BONUS_ABILITIES)

    job_info = EXECUTIVE_JOBS.get(ex.job, {"title": ex.job, "abbr": "?",
                                            "category": "business", "description": ""})
    category = job_info.get("category", "business")
    cat_info = EXECUTIVE_CATEGORIES.get(category, {"label": category, "color": "#94a3b8"})
    card_class = "card-special" if ex.is_special else "card"

    # Quit-nonpayment gets special styling
    is_quit = (ex.marketplace_reason == "quit_nonpayment")
    if is_quit:
        card_class = "card-quit"

    # Name
    name = f"{ex.first_name} {ex.last_name}"
    if ex.is_special and ex.special_title:
        name += f' <span style="color:#d4af37;font-size:14px;">"{ex.special_title}"</span>'

    # Legendary tag + ability
    legendary_html = ""
    if ex.is_special and ex.special_ability:
        leg = LEGENDARY_BONUS_ABILITIES.get(ex.special_ability, {})
        legendary_html = f"""
        <div class="legendary-ability">
            <span style="font-size:16px;">★</span>
            <div>
                <div class="legendary-ability-name">LEGENDARY: {leg.get('name', ex.special_ability)}</div>
                <div class="legendary-ability-desc">{leg.get('desc', '')}</div>
            </div>
        </div>"""

    # Flavor
    flavor_html = ""
    if ex.is_special and ex.special_flavor:
        flavor_html = f'<div class="flavor-text">{ex.special_flavor}</div>'

    # Abilities
    ability_chips = _ability_chips(ex)
    abilities_html = f"""
    <div class="abilities-section">
        <div class="abilities-header">Abilities ({len([a for a in (ex.abilities or "").split(',') if a])})</div>
        {ability_chips}
    </div>"""

    # School performance
    school_perf_html = _school_perf_bar(ex)

    # Level bar
    level_pct = min(ex.level / 7.0, 1.0) * 100
    level_html = f"""
    <div class="stat-row">
        <span class="stat-label">Level</span>
        <span class="stat-value purple">{ex.level}/7</span>
    </div>
    <div class="level-bar"><div class="level-fill" style="width:{level_pct:.0f}%"></div></div>"""

    # Age bar
    age_pct   = min(ex.current_age / max(ex.max_age, 1), 1.0) * 100
    age_color = ("green" if ex.current_age < ex.retirement_age - 10
                 else ("orange" if ex.current_age < ex.retirement_age else "red"))
    age_html = f"""
    <div class="stat-row">
        <span class="stat-label">Age</span>
        <span class="stat-value {age_color}">{ex.current_age}  (retires {ex.retirement_age}, max {ex.max_age})</span>
    </div>
    <div class="level-bar age-bar"><div class="level-fill" style="width:{age_pct:.0f}%"></div></div>"""

    # Wage + pay cycle
    cycle_label = PAY_CYCLE_LABELS.get(ex.pay_cycle, ex.pay_cycle)
    wage_html = f"""
    <div class="stat-row">
        <span class="stat-label">Wage</span>
        <span class="stat-value green">${ex.wage:,.2f} {cycle_label}</span>
    </div>"""

    # Hiring fee (marketplace)
    hiring_fee_html = ""
    if marketplace:
        cycle_ticks  = PAY_CYCLES.get(ex.pay_cycle, 720)
        hiring_fee   = ex.wage * (PAY_CYCLES["day"] / cycle_ticks)
        hiring_fee_html = f"""
        <div class="stat-row">
            <span class="stat-label">Hiring Fee (1 day wages)</span>
            <span class="stat-value gold">${hiring_fee:,.2f}</span>
        </div>"""

    # Missed payments warning
    missed_html = ""
    if (ex.missed_payments or 0) > 0:
        missed_html = f'<div class="alert-warning">⚠ {ex.missed_payments} missed payment(s) — pay on time to avoid forced quit!</div>'

    # School progress
    school_html = ""
    if ex.is_in_school:
        total = max(ex.school_total_ticks or 1, 1)
        pct   = max(5, int((1 - ex.school_ticks_remaining / total) * 100))
        real_s = ex.school_ticks_remaining * 5
        if real_s < 60:
            remain_str = f"{real_s}s"
        elif real_s < 3600:
            remain_str = f"{real_s//60}m {real_s%60}s"
        else:
            remain_str = f"{real_s//3600}h {(real_s%3600)//60}m"
        school_html = f"""
        <div class="stat-row">
            <span class="stat-label">In School</span>
            <span class="stat-value orange">Lvl {ex.level+1} — {remain_str} remaining</span>
        </div>
        <div class="level-bar school-bar">
            <div class="level-fill" style="width:{pct}%"></div>
        </div>
        <div style="font-size:11px;color:#64748b;">Abilities are paused during school. Performance boost on graduation.</div>"""
    elif ex.pending_upgrade:
        school_html = f"""
        <div style="background:#c084fc22;border:1px solid #c084fc;padding:10px;border-radius:6px;margin-top:8px;">
            <strong style="color:#c084fc;">Graduation Ready!</strong>
            Choose a performance upgrade for this executive.
            <div class="actions">
                <a href="/executives/upgrade/{ex.id}" class="btn btn-purple btn-small">Select Upgrade →</a>
            </div>
        </div>"""

    # Pension
    pension_html = ""
    if (ex.pension_ticks_remaining or 0) > 0:
        pension_html = f"""
        <div class="stat-row">
            <span class="stat-label">Pension Paid Out</span>
            <span class="stat-value orange">${ex.pension_owed:,.2f} over {ex.pension_ticks_remaining} ticks</span>
        </div>"""

    # Severance (informational)
    severance_html = ""
    if (ex.severance_owed or 0) > 0:
        severance_html = f"""
        <div class="stat-row">
            <span class="stat-label">Severance Paid</span>
            <span class="stat-value red">${ex.severance_owed:,.2f}</span>
        </div>"""

    # Marketplace badge
    badge_html = ""
    if marketplace:
        reason_map = {
            "new":               ('<span class="badge badge-new">NEW</span>', ""),
            "fired":             ('<span class="badge badge-fired">FIRED</span>', ""),
            "retired_available": ('<span class="badge badge-retired">VETERAN</span>', ""),
            "quit_nonpayment":   ('<span class="badge badge-quit">QUIT — Unpaid</span>',
                                  '<div class="alert-danger" style="font-size:11px;margin:4px 0;">Left previous employer due to non-payment. '
                                  'Will re-enter market but demands punctual pay.</div>'),
        }
        reason = ex.marketplace_reason or "new"
        b_html, note = reason_map.get(reason, ('<span class="badge badge-new">AVAILABLE</span>', ""))
        badge_html = b_html + note

    # P2P ability callout
    p2p_keys  = [a for a in (ex.abilities or "").split(",") if a in
                 ("p2p_notification","dm_threeway","contract_tracker","fee_negotiator",
                  "network_expander","deal_scout","rep_shield","mediation_svc")]
    p2p_html = ""
    if p2p_keys:
        from executive import EXEC_ABILITIES
        p2p_labels = [EXEC_ABILITIES.get(k, {}).get("name", k) for k in p2p_keys]
        p2p_html = f'<div class="alert-p2p">P2P Features: {" · ".join(p2p_labels)}</div>'

    # Actions
    actions_html = ""
    if show_actions and is_owner:
        btns = []
        if not ex.is_in_school and not ex.pending_upgrade and ex.level < 7:
            btns.append(f'<a href="/executives/school/{ex.id}" class="btn btn-orange btn-small">Send to School</a>')
        fire_msg = f"Fire {ex.first_name}? You will owe severance + pension immediately."
        btns.append(f"""
            <form method="POST" action="/api/executives/fire" style="display:inline;">
                <input type="hidden" name="executive_id" value="{ex.id}">
                <button type="submit" class="btn btn-red btn-small"
                    onclick="return confirm('{fire_msg}')">Fire</button>
            </form>""")
        actions_html = f'<div class="actions">{"".join(btns)}</div>'
    elif show_actions and marketplace:
        actions_html = f"""
        <div class="actions">
            <form method="POST" action="/api/executives/hire" style="display:inline;">
                <input type="hidden" name="executive_id" value="{ex.id}">
                <button type="submit" class="btn btn-green btn-small">Hire</button>
            </form>
        </div>"""

    # Final card
    return f"""
    <div class="{card_class} exec-cat-card" data-cat="{category}">
        {badge_html}
        <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:4px;">
            <div class="exec-name">{name}</div>
            {_cat_badge(category)}
        </div>
        <div class="exec-title">{job_info['title']} ({job_info.get('abbr','?')})</div>
        <div class="exec-desc">{job_info.get('description','')}</div>
        {legendary_html}
        {abilities_html}
        {p2p_html}
        {school_perf_html}
        {level_html}
        {age_html}
        {wage_html}
        {hiring_fee_html}
        {missed_html}
        {school_html}
        {pension_html}
        {severance_html}
        {flavor_html}
        {actions_html}
    </div>"""


# ==========================
# PAGES
# ==========================

@router.get("/executives", response_class=HTMLResponse)
def executives_dashboard(session_token: Optional[str] = Cookie(None),
                          msg: Optional[str] = Query(None)):
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from executive import (get_player_executives, MAX_EXECUTIVES_PER_PLAYER,
                           get_db, PAY_CYCLES, EXECUTIVE_JOBS, EXECUTIVE_CATEGORIES,
                           player_has_ability)
    db = get_db()
    try:
        execs = get_player_executives(db, player.id)

        msg_html = ""
        if msg:
            css = ("msg-success" if any(w in msg.lower()
                   for w in ["success","hired","fired","upgraded","sent","graduated"])
                   else "msg-error")
            msg_html = f'<div class="{css}">{msg}</div>'

        nav_html = """
        <div class="nav-row">
            <a href="/executives" class="btn btn-purple">My Executives</a>
            <a href="/executives/marketplace" class="btn btn-blue">Marketplace</a>
            <a href="/" class="nav-link">Dashboard</a>
        </div>"""

        # Summary
        total_wages_per_hour = 0.0
        active_count = school_count = pending_count = legendary_count = 0
        for ex in execs:
            if not ex.is_retired:
                active_count += 1
                ct = PAY_CYCLES.get(ex.pay_cycle, 720)
                total_wages_per_hour += ex.wage * (720 / ct)
            if ex.is_in_school:
                school_count += 1
            if ex.pending_upgrade:
                pending_count += 1
            if ex.is_special:
                legendary_count += 1

        # P2P status
        has_p2p_notif = player_has_ability(db, player.id, "p2p_notification")
        has_p2p_3way  = player_has_ability(db, player.id, "dm_threeway")
        p2p_status = ""
        if has_p2p_notif or has_p2p_3way:
            feats = []
            if has_p2p_notif:
                feats.append("📩 DM + 📄 Contract notifications on P2P button")
            if has_p2p_3way:
                feats.append("3rd-party DM invites enabled")
            p2p_status = f'<div class="alert-p2p" style="margin-bottom:12px;">P2P Executive Features Active: {" | ".join(feats)}</div>'

        summary_html = f"""
        <div class="summary-grid">
            <div class="summary-card">
                <div class="label">Roster</div>
                <div class="value">{len(execs)}/{MAX_EXECUTIVES_PER_PLAYER}</div>
            </div>
            <div class="summary-card">
                <div class="label">Active</div>
                <div class="value" style="color:#22c55e;">{active_count}</div>
            </div>
            <div class="summary-card">
                <div class="label">Legendary</div>
                <div class="value" style="color:#d4af37;">{legendary_count}</div>
            </div>
            <div class="summary-card">
                <div class="label">In School</div>
                <div class="value" style="color:#f59e0b;">{school_count}</div>
            </div>
            <div class="summary-card">
                <div class="label">Wages/Hour</div>
                <div class="value" style="color:#ef4444;">${total_wages_per_hour:,.2f}</div>
            </div>
        </div>"""

        pending_html = ""
        if pending_count:
            pending_html = f"""
            <div style="background:#c084fc22;border:1px solid #c084fc;padding:12px;border-radius:6px;margin-bottom:16px;">
                <strong style="color:#c084fc;">🎓 {pending_count} executive(s) graduated!</strong>
                Select their performance upgrades below.
            </div>"""

        if execs:
            cards_html = '<div class="exec-grid">'
            for ex in sorted(execs, key=lambda x: (not x.is_special, -x.level)):
                cards_html += render_exec_card(ex, show_actions=True, is_owner=True)
            cards_html += '</div>'
        else:
            cards_html = """
            <div class="empty-state">
                <h3>No Executives Hired</h3>
                <p>Visit the marketplace to hire your first executive.</p><br>
                <a href="/executives/marketplace" class="btn btn-blue">Browse Marketplace</a>
            </div>"""

        body = f"{msg_html}{nav_html}{p2p_status}{summary_html}{pending_html}{cards_html}"
        return exec_shell("Executives Dashboard", body, player)
    finally:
        db.close()


@router.get("/executives/marketplace", response_class=HTMLResponse)
def executives_marketplace(session_token: Optional[str] = Cookie(None),
                            msg: Optional[str] = Query(None),
                            cat: Optional[str] = Query("all")):
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from executive import (get_marketplace_executives, get_db,
                           EXECUTIVE_CATEGORIES, EXECUTIVE_JOBS)
    db = get_db()
    try:
        available = get_marketplace_executives(db)

        msg_html = ""
        if msg:
            css = "msg-success" if any(w in msg.lower() for w in ["hired","success"]) else "msg-error"
            msg_html = f'<div class="{css}">{msg}</div>'

        nav_html = """
        <div class="nav-row">
            <a href="/executives" class="btn btn-purple">My Executives</a>
            <a href="/executives/marketplace" class="btn btn-blue">Marketplace</a>
            <a href="/" class="nav-link">Dashboard</a>
        </div>"""

        # Category filter buttons
        filter_html = '<div class="filter-row"><span style="color:#94a3b8;font-size:12px;">Filter:</span>'
        filter_html += f'<button class="filter-btn active" data-cat="all" onclick="filterCategory(\'all\')">All ({len(available)})</button>'
        for cat_key, cat_data in EXECUTIVE_CATEGORIES.items():
            cnt = sum(1 for e in available
                      if EXECUTIVE_JOBS.get(e.job, {}).get("category") == cat_key)
            if cnt:
                filter_html += (f'<button class="filter-btn cat-{cat_key}" '
                                f'data-cat="{cat_key}" '
                                f'onclick="filterCategory(\'{cat_key}\')">'
                                f'{cat_data["label"]} ({cnt})</button>')
        filter_html += '</div>'

        if available:
            specials = [e for e in available if e.is_special]
            regulars = [e for e in available if not e.is_special]

            cards_html = ""
            if specials:
                cards_html += '<div class="cat-section"><h3 style="color:#d4af37;margin-bottom:12px;">★ Legendary Executives</h3>'
                cards_html += '<div class="exec-grid">'
                for ex in specials:
                    cards_html += render_exec_card(ex, show_actions=True, marketplace=True)
                cards_html += '</div></div><br>'

            if regulars:
                cards_html += '<div class="cat-section"><h3 style="color:#94a3b8;margin-bottom:12px;">Available Executives</h3>'
                cards_html += '<div class="exec-grid">'
                for ex in regulars:
                    cards_html += render_exec_card(ex, show_actions=True, marketplace=True)
                cards_html += '</div></div>'
        else:
            cards_html = """
            <div class="empty-state">
                <h3>No Executives Available</h3>
                <p>New executives enter the workforce periodically. Check back soon.</p>
            </div>"""

        count_html = f'<p style="color:#94a3b8;margin-bottom:12px;">{len(available)} executive(s) available</p>'
        body = f"{msg_html}{nav_html}{count_html}{filter_html}{cards_html}"
        return exec_shell("Executive Marketplace", body, player)
    finally:
        db.close()


@router.get("/executives/school/{executive_id}", response_class=HTMLResponse)
def school_confirm(executive_id: int, session_token: Optional[str] = Cookie(None)):
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from executive import (Executive, EXECUTIVE_JOBS, SCHOOL_BASE_COST, SCHOOL_BASE_TICKS,
                           get_school_discount, get_db, get_specific_ability_bonus)
    db = get_db()
    try:
        ex = db.query(Executive).filter(
            Executive.id == executive_id,
            Executive.player_id == player.id
        ).first()
        if not ex:
            return RedirectResponse(url="/executives?msg=Executive not found", status_code=303)
        if ex.level >= 7:
            return RedirectResponse(url="/executives?msg=Executive is at max level", status_code=303)

        target_level = ex.level + 1
        cost  = SCHOOL_BASE_COST * target_level
        ticks = SCHOOL_BASE_TICKS * target_level

        discount = get_school_discount(db, player.id)
        cost  *= max(0.20, 1.0 - discount)
        ticks  = int(ticks * max(0.20, 1.0 - discount))

        fast_learner = ex.is_special and ex.special_ability == "fast_learner"
        if fast_learner:
            ticks = ticks // 2

        real_s = ticks * 5
        if real_s < 60:
            time_str = f"{real_s}s"
        elif real_s < 3600:
            time_str = f"{real_s // 60}m {real_s % 60}s"
        else:
            time_str = f"{real_s // 3600}h {(real_s % 3600) // 60}m"

        can_afford = player.cash_balance >= cost
        job_info   = EXECUTIVE_JOBS.get(ex.job, {"title": ex.job})

        # Show what abilities will be boosted
        ability_keys = [a for a in (ex.abilities or "").split(",") if a]

        # Discount sources
        disc_lines = []
        pr = get_specific_ability_bonus(db, player.id, "process_reeng")
        rb = get_specific_ability_bonus(db, player.id, "retention_bonus")
        if pr:
            disc_lines.append(f'Process Reengineering: −{pr*100:.1f}%')
        if rb:
            disc_lines.append(f'Retention Bonus: −{rb*100:.1f}%')
        if fast_learner:
            disc_lines.append('Fast Learner (legendary): halved duration')
        disc_html = ""
        if disc_lines:
            disc_html = ('<div class="alert-success" style="margin:8px 0;">'
                         + "Discounts applied: " + " | ".join(disc_lines) + '</div>')

        abilities_preview = "".join(
            f'<span style="background:#1e293b;border:1px solid #334155;border-radius:4px;'
            f'padding:3px 8px;margin:2px;font-size:11px;color:#c084fc;display:inline-block;">'
            f'{a}</span>' for a in ability_keys
        ) or '<span style="color:#64748b;font-size:12px;">None (legacy executive)</span>'

        body = f"""
        <div class="nav-row"><a href="/executives" class="nav-link">← Back</a></div>
        <div class="card">
            <h2>Send to School: {ex.first_name} {ex.last_name}</h2>
            <p style="color:#94a3b8;">{job_info['title']} — Level {ex.level} → {target_level}</p>
            <br>
            <div class="stat-row">
                <span class="stat-label">Tuition</span>
                <span class="stat-value {'green' if can_afford else 'red'}">${cost:,.2f}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Duration</span>
                <span class="stat-value orange">{ticks} ticks (~{time_str})</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Your Balance</span>
                <span class="stat-value green">${player.cash_balance:,.2f}</span>
            </div>
            {disc_html}
            <br>
            <div style="background:#0a1020;border-radius:6px;padding:12px;margin:8px 0;">
                <div style="font-size:12px;font-weight:bold;color:#94a3b8;margin-bottom:6px;">
                    WHAT SCHOOL DOES — IMPORTANT
                </div>
                <p style="color:#e5e7eb;font-size:13px;line-height:1.6;">
                    School <strong style="color:#22c55e;">boosts the effectiveness</strong> of this executive's
                    existing abilities. It <strong style="color:#ef4444;">never adds new abilities</strong>.
                    After graduation you will choose one of three performance-focus options.
                </p>
                <div style="margin-top:8px;font-size:12px;color:#64748b;">Abilities that will be boosted:</div>
                <div style="margin-top:4px;">{abilities_preview}</div>
            </div>
            <p style="color:#94a3b8;font-size:12px;">
                While in school this executive provides no bonuses. Wage raises +15% upon graduation.
            </p>
            <div class="actions">
                {'<form method="POST" action="/api/executives/school"><input type="hidden" name="executive_id" value="' + str(ex.id) + '"><button type="submit" class="btn btn-orange">Enroll Now</button></form>'
                  if can_afford else
                  '<span class="btn btn-red" style="cursor:not-allowed;opacity:0.6;">Insufficient Funds</span>'}
                <a href="/executives" class="btn btn-blue">Cancel</a>
            </div>
        </div>"""
        return exec_shell("School Enrollment", body, player)
    finally:
        db.close()


@router.get("/executives/upgrade/{executive_id}", response_class=HTMLResponse)
def upgrade_select(executive_id: int, session_token: Optional[str] = Cookie(None)):
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from executive import (Executive, EXECUTIVE_JOBS, SCHOOL_UPGRADES,
                           get_school_performance_multiplier, get_db, EXEC_ABILITIES)
    db = get_db()
    try:
        ex = db.query(Executive).filter(
            Executive.id == executive_id,
            Executive.player_id == player.id
        ).first()
        if not ex:
            return RedirectResponse(url="/executives?msg=Executive not found", status_code=303)
        if not ex.pending_upgrade:
            return RedirectResponse(url="/executives?msg=No pending upgrade", status_code=303)

        job_info   = EXECUTIVE_JOBS.get(ex.job, {"title": ex.job})
        curr_mult  = get_school_performance_multiplier(ex)
        ability_keys = [a for a in (ex.abilities or "").split(",") if a]

        abilities_list = "".join(
            f'<li style="margin:3px 0;color:#c084fc;">{EXEC_ABILITIES.get(k,{}).get("name",k)}'
            f' <span style="color:#64748b;font-size:11px;">— {EXEC_ABILITIES.get(k,{}).get("desc","")}</span></li>'
            for k in ability_keys
        )

        upgrade_cards = ""
        for key, u in SCHOOL_UPGRADES.items():
            new_mult = curr_mult * u["perf_mult"]
            wage_note = ""
            if u["wage_mod"] < 1.0:
                wage_note = f'<span class="upgrade-note">Wage adjusted: ×{u["wage_mod"]:.2f} ({(1-u["wage_mod"])*100:.0f}% reduction)</span>'
            team_note = ""
            if u["team_boost"] > 0:
                team_note = f'<span class="upgrade-note">+{u["team_boost"]*100:.0f}% to ALL executives</span>'
            upgrade_cards += f"""
            <form method="POST" action="/api/executives/upgrade" class="upgrade-option">
                <input type="hidden" name="executive_id" value="{ex.id}">
                <input type="hidden" name="bonus_key" value="{key}">
                <div class="upgrade-name">{u['name']}</div>
                <div class="upgrade-desc">{u['description']}</div>
                <div style="margin-top:8px;font-size:12px;color:#94a3b8;">
                    Performance multiplier: <span style="color:#c084fc;font-weight:bold;">{curr_mult:.2f}x → {new_mult:.2f}x</span>
                </div>
                {wage_note}{team_note}
                <br>
                <button type="submit" class="btn btn-purple btn-small">Choose This</button>
            </form>"""

        body = f"""
        <div class="nav-row"><a href="/executives" class="nav-link">← Back</a></div>
        <div class="card">
            <h2>🎓 Graduation — {ex.first_name} {ex.last_name}</h2>
            <p style="color:#94a3b8;">{job_info['title']} — Level {ex.level} → {ex.level + 1}</p>
            <br>
            <div style="background:#22c55e11;border:1px solid #22c55e44;border-radius:6px;padding:12px;margin-bottom:12px;">
                <strong style="color:#22c55e;">Performance Upgrade</strong>
                — Choose how this executive refines their skills.
                All options <strong>boost existing ability effectiveness</strong>.
                No new abilities are ever added through schooling.
            </div>
            <div style="font-size:12px;color:#64748b;margin-bottom:4px;">Current abilities being boosted:</div>
            <ul style="list-style:none;padding-left:8px;margin-bottom:12px;">{abilities_list or '<li style="color:#475569;">No abilities recorded</li>'}</ul>
            <div style="font-size:12px;color:#64748b;margin-bottom:2px;">
                Current performance multiplier: <span style="color:#c084fc;font-weight:bold;">{curr_mult:.2f}x</span>
            </div>
        </div>
        <div class="upgrade-grid">{upgrade_cards}</div>"""
        return exec_shell("Select School Upgrade", body, player)
    finally:
        db.close()


# ==========================
# API ENDPOINTS
# ==========================

@router.post("/api/executives/hire", response_class=HTMLResponse)
def api_hire(executive_id: int = Form(...),
             session_token: Optional[str] = Cookie(None)):
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    from executive import hire_executive, get_db
    db = get_db()
    try:
        result = hire_executive(db, player.id, executive_id)
        if result["success"]:
            return RedirectResponse(url=f"/executives?msg={result['message']}", status_code=303)
        return RedirectResponse(url=f"/executives/marketplace?msg={result['error']}", status_code=303)
    finally:
        db.close()


@router.post("/api/executives/fire", response_class=HTMLResponse)
def api_fire(executive_id: int = Form(...),
             session_token: Optional[str] = Cookie(None)):
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    from executive import fire_executive, get_db
    db = get_db()
    try:
        result = fire_executive(db, player.id, executive_id)
        msg = result["message"] if result["success"] else result["error"]
        return RedirectResponse(url=f"/executives?msg={msg}", status_code=303)
    finally:
        db.close()


@router.post("/api/executives/school", response_class=HTMLResponse)
def api_school(executive_id: int = Form(...),
               session_token: Optional[str] = Cookie(None)):
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    from executive import send_to_school, get_db
    db = get_db()
    try:
        result = send_to_school(db, player.id, executive_id)
        msg = result["message"] if result["success"] else result["error"]
        return RedirectResponse(url=f"/executives?msg={msg}", status_code=303)
    finally:
        db.close()


@router.post("/api/executives/upgrade", response_class=HTMLResponse)
def api_upgrade(executive_id: int = Form(...),
                bonus_key: str   = Form(...),
                session_token: Optional[str] = Cookie(None)):
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    from executive import apply_school_upgrade, get_db
    db = get_db()
    try:
        result = apply_school_upgrade(db, player.id, executive_id, bonus_key)
        msg = result["message"] if result["success"] else result["error"]
        return RedirectResponse(url=f"/executives?msg={msg}", status_code=303)
    finally:
        db.close()
