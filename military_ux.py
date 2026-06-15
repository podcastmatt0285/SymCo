"""
military_ux.py

Player-facing Branch Warfare panels rendered inside the /port-authority page.
All mutations go through the JSON API in `military.router` (/api/military/*).
The panels are composed into the existing Port Authority page body (which owns
the shared `#pa-msg` status line and the `_show()` helper).
"""

import html
from typing import Callable


def _label(slug: str) -> str:
    try:
        from military import item_name
        return item_name(slug)
    except Exception:
        return slug.replace("_", " ").title()


def _fmt_items(d: dict) -> str:
    if not d:
        return "none"
    return ", ".join(f"{int(v)}× {_label(k)}" for k, v in d.items())


def build_warfare_panels(player_id: int, fmt_usd: Callable = None) -> str:
    """Return the full Branch Warfare HTML block for the PA dashboard."""
    import military

    st = military.get_military_status(player_id)
    if not st["has_pa"]:
        return ""

    banned = st["banned"]
    branches = st["branches"]
    event = st["event"]
    campaign = st["campaign"]
    blockades = st["blockades"]
    go_dark = st["go_dark"]
    battles = st["battles"]
    watchlist = st.get("watchlist", [])

    # ── Force composition ────────────────────────────────────────────────────
    if branches:
        force_rows = []
        for br_key, b in sorted(branches.items()):
            unit_rows = "".join(
                f"<tr><td style='padding:3px 8px;'>{_label(u['slug'])}</td>"
                f"<td style='padding:3px 8px;text-align:right;'>{int(u['qty'])}</td>"
                f"<td style='padding:3px 8px;text-align:right;color:#94a3b8;'>{int(u['home'])} home</td>"
                f"<td style='padding:3px 8px;text-align:right;color:#fbbf24;'>A{u['attack']}/D{u['defense']}</td></tr>"
                for u in sorted(b["units"], key=lambda x: -x["attack"])
            )
            force_rows.append(
                f"<div style='border:1px solid #2D1810;padding:8px;margin-bottom:8px;'>"
                f"<div style='color:#B08D57;font-weight:bold;'>{b['label']} "
                f"<span style='color:#94a3b8;font-weight:normal;font-size:0.85em;'>"
                f"— attack {b['attack']} · defense {b['defense']} · {b['committed']} committed</span></div>"
                f"<table style='width:100%;border-collapse:collapse;font-size:0.9em;'>{unit_rows}</table></div>"
            )
        force_html = "".join(force_rows)
    else:
        force_html = ("<p style='color:#94a3b8;'>No units in Port Authority command. "
                      "Deposit weapons below to raise your Branches.</p>")

    # Available-at-home unit inputs (used by all force pickers).
    home_units = []
    for br_key, b in sorted(branches.items()):
        for u in sorted(b["units"], key=lambda x: -x["attack"]):
            if u["home"] > 0:
                home_units.append((u["slug"], int(u["home"]), b["label"]))
    if home_units:
        picker_rows = "".join(
            f"<div style='display:flex;justify-content:space-between;align-items:center;gap:8px;padding:2px 0;'>"
            f"<span style='font-size:0.9em;'>{_label(slug)} "
            f"<span style='color:#94a3b8;'>({home} home · {lbl})</span></span>"
            f"<input type='number' min='0' max='{home}' value='0' class='mil-force' "
            f"data-slug='{slug}' style='width:80px;padding:4px;'></div>"
            for slug, home, lbl in home_units
        )
    else:
        picker_rows = "<p style='color:#94a3b8;'>No uncommitted units at home.</p>"

    # ── Procurement event / campaign ─────────────────────────────────────────
    if banned:
        event_html = ("<div style='border:1px solid #f87171;padding:12px;color:#f87171;'>"
                      "Your security force is banned after a campaign wipe. You cannot fight "
                      "until the 60-day ban expires.</div>")
    elif campaign:
        tgts = campaign["targets"]
        idx = campaign["current_index"]
        prog = "".join(
            f"<li style='color:{'#4ade80' if i < idx else ('#fbbf24' if i == idx else '#94a3b8')};'>"
            f"Target #{t}{' ✓' if i < idx else (' ⚔️ next' if i == idx else '')}</li>"
            for i, t in enumerate(tgts)
        )
        nb = (campaign.get("next_battle_at") or "")[:16].replace("T", " ")
        event_html = (
            f"<div style='border:1px solid #4ade80;padding:12px;'>"
            f"<div style='color:#4ade80;font-weight:bold;'>Campaign in progress</div>"
            f"<ul style='margin:6px 0;'>{prog}</ul>"
            f"<div style='color:#94a3b8;font-size:0.9em;'>Next battle: {nb} UTC · "
            f"Committed force: {_fmt_items(campaign['committed_force'])}</div></div>"
        )
    elif event:
        allowed = ", ".join(military.BRANCH_LABELS.get(b, b) for b in event["branches"])
        cap = event["max_branch_strength"]
        cap_txt = f"max {cap} power/branch" if cap else "no branch cap"
        event_html = (
            f"<div style='border:1px solid #B08D57;padding:12px;'>"
            f"<div style='color:#B08D57;font-weight:bold;'>{html.escape(event['title'])}</div>"
            f"<div style='color:#94a3b8;font-size:0.9em;margin:4px 0 10px;'>"
            f"Branches: {allowed} · {cap_txt} · loot {int(event['loot_fraction']*100)}% · "
            f"1 battle / {event['battle_hours']}h</div>"
            f"<div style='margin-bottom:6px;'>Select 3 targets:</div>"
            f"<div id='mil-targets'></div>"
            f"<input type='text' id='mil-search' placeholder='Search players…' "
            f"oninput='milSearch()' style='width:100%;padding:6px;margin:6px 0;'>"
            f"<div id='mil-search-results' style='font-size:0.9em;'></div>"
            f"<div style='margin-top:10px;color:#B08D57;'>Commit force:</div>"
            f"<div style='max-height:200px;overflow:auto;border:1px solid #2D1810;padding:6px;margin:6px 0;'>{picker_rows}</div>"
            f"<button onclick='milCommitCampaign()' style='padding:8px 18px;cursor:pointer;"
            f"background:#8B4513;color:#F5F5DC;border:1px solid #B08D57;'>⚔️ Launch Campaign</button>"
            f"</div>"
        )
    else:
        event_html = ("<p style='color:#94a3b8;'>No Procurement Event is active. "
                      "When the government opens one, pick 3 targets and commit your forces here.</p>")

    # ── Blockades ────────────────────────────────────────────────────────────
    on_me = blockades["on_me"]
    by_me = blockades["by_me"]
    if on_me:
        b = on_me[0]
        exp = b["expires_at"][:16].replace("T", " ")
        break_html = (
            f"<div style='border:1px solid #f87171;padding:10px;margin-bottom:8px;'>"
            f"<div style='color:#f87171;'>⛔ Blockaded by player #{b['deployer_id']} "
            f"(expires {exp} UTC). Your commerce is frozen until you lift it.</div>"
            f"<div style='margin:6px 0;color:#B08D57;'>Commit a force to break it:</div>"
            f"<button onclick='milBreakBlockade()' style='padding:6px 14px;cursor:pointer;"
            f"background:#8B4513;color:#F5F5DC;border:1px solid #B08D57;'>Break Blockade "
            f"(uses force selected above)</button></div>"
        )
    else:
        break_html = ""
    by_me_html = "".join(
        f"<li style='color:#94a3b8;'>On player #{b['target_id']} — expires "
        f"{b['expires_at'][:16].replace('T', ' ')} UTC</li>" for b in by_me
    ) or "<li style='color:#94a3b8;'>None.</li>"

    # Saved future targets (rendered server-side; tap one to load it as the target).
    if watchlist:
        watch_rows = "".join(
            "<div style='display:flex;justify-content:space-between;align-items:center;"
            "gap:8px;padding:3px 0;border-bottom:1px solid #2D1810;'>"
            f"<span style='color:#F5F5DC;cursor:pointer;' "
            f"onclick=\"milSetBlockTarget({w['id']}, &#39;{w['name'].replace(chr(39), '')}&#39;)\">"
            f"🎯 {html.escape(w['name'])} <span style='color:#94a3b8;'>(#{w['id']})</span></span>"
            f"<span style='cursor:pointer;color:#f87171;' title='Remove' "
            f"onclick='milRemoveWatch({w['id']})'>✕</span></div>"
            for w in watchlist
        )
    else:
        watch_rows = ("<div style='color:#94a3b8;'>No saved targets yet — search below "
                      "and tap ➕ to start a list of players you're eyeing.</div>")

    blockade_html = (
        f"{break_html}"
        f"<div style='border:1px solid #2D1810;padding:10px;'>"
        f"<div style='color:#B08D57;'>Deploy a blockade (you defend; target must beat you in 72h):</div>"
        f"<input type='text' id='mil-block-search' placeholder='Search players by name…' "
        f"oninput='milBlockSearch()' autocomplete='off' style='padding:6px;margin:6px 0;width:100%;'>"
        f"<div id='mil-block-results' style='font-size:0.9em;'></div>"
        f"<div id='mil-block-selected' style='color:#94a3b8;margin:6px 0;'>No target selected.</div>"
        f"<div style='color:#94a3b8;font-size:0.85em;'>Uses the force quantities selected above.</div>"
        f"<button onclick='milDeployBlockade()' style='margin-top:6px;padding:6px 14px;cursor:pointer;'>"
        f"🚫 Deploy Blockade</button></div>"
        # Watchlist of future targets
        f"<div style='border:1px solid #2D1810;padding:10px;margin-top:8px;'>"
        f"<b style='color:#B08D57;'>🎯 Future targets "
        f"<span style='color:#94a3b8;font-weight:normal;'>"
        f"({len(watchlist)}/{military.WATCHLIST_MAX}) — players you're eyeing</span></b>"
        f"<div id='mil-watchlist' style='margin-top:6px;'>{watch_rows}</div></div>"
        f"<div style='margin-top:8px;'><b style='color:#B08D57;'>Your active blockades:</b>"
        f"<ul style='margin:4px 0;'>{by_me_html}</ul></div>"
    )

    # ── Espionage ────────────────────────────────────────────────────────────
    dark_list = "".join(
        f"<li style='color:#94a3b8;'>Dark to player #{g['hidden_from']} — until "
        f"{g['expires_at'][:16].replace('T', ' ')} UTC</li>" for g in go_dark
    ) or "<li style='color:#94a3b8;'>Not hidden from anyone.</li>"
    espionage_html = (
        f"<div style='border:1px solid #2D1810;padding:10px;'>"
        f"<div style='color:#B08D57;'>Go dark — spend Intelligence units (drones) to vanish "
        f"from a rival's target search for up to 7 days:</div>"
        f"<div style='display:flex;gap:8px;flex-wrap:wrap;margin:6px 0;'>"
        f"<input type='number' id='mil-dark-target' placeholder='Hide from player ID' style='padding:6px;width:180px;'>"
        f"<input type='number' id='mil-dark-drones' min='1' value='1' placeholder='drones' style='padding:6px;width:100px;'>"
        f"<button onclick='milGoDark()' style='padding:6px 14px;cursor:pointer;'>🕶️ Go Dark</button></div>"
        f"<ul style='margin:4px 0;'>{dark_list}</ul></div>"
    )

    # ── Battle history ───────────────────────────────────────────────────────
    if battles:
        b_rows = "".join(
            f"<tr><td style='padding:4px 8px;'>{_label(b['kind'])}</td>"
            f"<td style='padding:4px 8px;'>{b['as'].title()} vs #{b['opponent']}</td>"
            f"<td style='padding:4px 8px;color:{'#4ade80' if (b['winner']=='attacker')==(b['as']=='attacker') else '#f87171'};'>"
            f"{(b['winner'] or '').title()}</td>"
            f"<td style='padding:4px 8px;color:#94a3b8;'>{b['rounds']}</td>"
            f"<td style='padding:4px 8px;color:#94a3b8;font-size:0.85em;'>"
            f"You lost: {_fmt_items(b['attacker_losses'] if b['as']=='attacker' else b['defender_losses'])}"
            f"{(' · Loot: ' + _fmt_items(b['loot'])) if b['loot'] and b['as']=='attacker' else ''}</td></tr>"
            for b in battles
        )
    else:
        b_rows = "<tr><td colspan='5' style='padding:10px;color:#94a3b8;'>No battles yet.</td></tr>"

    # ── Assemble ─────────────────────────────────────────────────────────────
    return f"""
      <h2 style="color:#B08D57;margin-top:28px;border-top:1px solid #2D1810;padding-top:16px;">
        ⚔️ Branch Warfare
      </h2>
      <p style="color:#94a3b8;margin:0 0 12px;font-size:0.9em;">
        Raise four Branches — Navy, Army, Air Force, Intelligence — in Port Authority command.
        Fight deterministic one-unit-at-a-time battles to loot rivals during Procurement Events,
        blockade their commerce, or go dark to hide from attackers. Units destroyed in battle are
        gone for good.
      </p>

      <h3 style="color:#B08D57;margin-top:14px;">Your Branches</h3>
      {force_html}

      <h3 style="color:#B08D57;margin-top:18px;">Procurement Campaign</h3>
      {event_html}

      <h3 style="color:#B08D57;margin-top:18px;">Blockades</h3>
      {blockade_html}

      <h3 style="color:#B08D57;margin-top:18px;">Espionage</h3>
      {espionage_html}

      <h3 style="color:#B08D57;margin-top:18px;">Battle History</h3>
      <table style="width:100%;border-collapse:collapse;border:1px solid #2D1810;">
        <tr style="color:#94a3b8;">
          <td style="padding:4px 8px;">Kind</td><td style="padding:4px 8px;">Match</td>
          <td style="padding:4px 8px;">Result</td><td style="padding:4px 8px;">Rounds</td>
          <td style="padding:4px 8px;">Detail</td>
        </tr>
        {b_rows}
      </table>

      <script>
      var _milTargets = [];
      function _milMsg(t){{ if(typeof _show==='function') _show(t); else alert(t); }}
      function _milForce(){{
        var f = {{}};
        document.querySelectorAll('.mil-force').forEach(function(el){{
          var q = parseInt(el.value||'0');
          if(q>0) f[el.getAttribute('data-slug')] = q;
        }});
        return f;
      }}
      async function milSearch(){{
        var q = document.getElementById('mil-search').value;
        if(!q){{ document.getElementById('mil-search-results').innerHTML=''; return; }}
        var r = await fetch('/api/military/search?q='+encodeURIComponent(q));
        var j = await r.json();
        var html = (j.results||[]).map(function(p){{
          return '<div style="cursor:pointer;padding:3px 0;color:#B08D57;" onclick="milPickTarget('+p.id+',\\''+
                 (p.name||'').replace(/\\'/g,'')+'\\')">+ '+(p.name||('Player #'+p.id))+' (#'+p.id+')</div>';
        }}).join('');
        document.getElementById('mil-search-results').innerHTML = html || '<span style="color:#94a3b8;">No players.</span>';
      }}
      function milPickTarget(id, name){{
        if(_milTargets.indexOf(id)>=0) return;
        if(_milTargets.length>=3){{ _milMsg('You already picked 3 targets.'); return; }}
        _milTargets.push(id);
        _renderTargets();
      }}
      function milRemoveTarget(id){{ _milTargets = _milTargets.filter(function(t){{return t!=id;}}); _renderTargets(); }}
      function _renderTargets(){{
        var el = document.getElementById('mil-targets');
        if(!el) return;
        el.innerHTML = _milTargets.map(function(t){{
          return '<span style="display:inline-block;background:#2D1810;padding:3px 8px;margin:2px;border-radius:4px;">#'+
                 t+' <span style="cursor:pointer;color:#f87171;" onclick="milRemoveTarget('+t+')">✕</span></span>';
        }}).join('');
      }}
      async function milCommitCampaign(){{
        if(_milTargets.length!==3){{ _milMsg('Pick exactly 3 targets.'); return; }}
        var r = await fetch('/api/military/campaign/commit', {{method:'POST',headers:{{'Content-Type':'application/json'}},
          body: JSON.stringify({{targets:_milTargets, force:_milForce()}})}});
        var j = await r.json(); _milMsg(j.message||j.error||'');
        if(j.ok) setTimeout(function(){{location.reload();}}, 900);
      }}
      // ── Blockade target: live name search + watchlist ──────────────────────
      var _milBlockTarget = 0;
      var _milBlockTimer = null;
      function milBlockSearch(){{
        clearTimeout(_milBlockTimer);
        _milBlockTimer = setTimeout(_milBlockSearchNow, 180);
      }}
      async function _milBlockSearchNow(){{
        var q = document.getElementById('mil-block-search').value;
        if(!q){{ document.getElementById('mil-block-results').innerHTML=''; return; }}
        var r = await fetch('/api/military/search?q='+encodeURIComponent(q));
        var j = await r.json();
        var html = (j.results||[]).map(function(p){{
          var nm = (p.name||('Player #'+p.id)).replace(/\\'/g,'');
          return '<div style="padding:3px 0;display:flex;gap:10px;align-items:center;">'+
            '<span style="color:#B08D57;cursor:pointer;" onclick="milSetBlockTarget('+p.id+',\\''+nm+'\\')">🎯 '+
            nm+' (#'+p.id+')</span>'+
            '<span style="color:#94a3b8;cursor:pointer;" title="Add to watchlist" onclick="milAddWatch('+p.id+')">➕</span></div>';
        }}).join('');
        document.getElementById('mil-block-results').innerHTML = html || '<span style="color:#94a3b8;">No players.</span>';
      }}
      function milSetBlockTarget(id, name){{
        _milBlockTarget = id;
        document.getElementById('mil-block-selected').innerHTML =
          '🎯 Target: <b style="color:#F5F5DC;">'+name+'</b> (#'+id+')';
        document.getElementById('mil-block-results').innerHTML='';
        var sb = document.getElementById('mil-block-search'); if(sb) sb.value = name;
      }}
      async function milAddWatch(id){{
        var r = await fetch('/api/military/watchlist/add', {{method:'POST',headers:{{'Content-Type':'application/json'}},
          body: JSON.stringify({{target_id:id}})}});
        var j = await r.json(); _milMsg(j.message||j.error||'');
        if(j.ok) setTimeout(function(){{location.reload();}}, 700);
      }}
      async function milRemoveWatch(id){{
        var r = await fetch('/api/military/watchlist/remove', {{method:'POST',headers:{{'Content-Type':'application/json'}},
          body: JSON.stringify({{target_id:id}})}});
        var j = await r.json(); _milMsg(j.message||j.error||'');
        if(j.ok) setTimeout(function(){{location.reload();}}, 500);
      }}
      async function milDeployBlockade(){{
        if(!_milBlockTarget){{ _milMsg('Search for a player and tap 🎯 to select a target first.'); return; }}
        var r = await fetch('/api/military/blockade/deploy', {{method:'POST',headers:{{'Content-Type':'application/json'}},
          body: JSON.stringify({{target_id:_milBlockTarget, force:_milForce()}})}});
        var j = await r.json(); _milMsg(j.message||j.error||'');
        if(j.ok) setTimeout(function(){{location.reload();}}, 900);
      }}
      async function milBreakBlockade(){{
        var r = await fetch('/api/military/blockade/break', {{method:'POST',headers:{{'Content-Type':'application/json'}},
          body: JSON.stringify({{force:_milForce()}})}});
        var j = await r.json(); _milMsg(j.message||j.error||'');
        if(j.ok) setTimeout(function(){{location.reload();}}, 900);
      }}
      async function milGoDark(){{
        var t = parseInt(document.getElementById('mil-dark-target').value||'0');
        var d = parseInt(document.getElementById('mil-dark-drones').value||'0');
        if(!t){{ _milMsg('Enter a player ID to hide from.'); return; }}
        var r = await fetch('/api/military/go-dark', {{method:'POST',headers:{{'Content-Type':'application/json'}},
          body: JSON.stringify({{hidden_from:t, drones:d}})}});
        var j = await r.json(); _milMsg(j.message||j.error||'');
        if(j.ok) setTimeout(function(){{location.reload();}}, 900);
      }}
      </script>
    """
