# Admin / Mod Dashboard — Feature Backlog

Brainstormed by comparing SymCo's current toolset against Discord, Reddit, and Twitch.
Items are grouped by category and ranked by value/complexity at the bottom.

---

## Player Oversight

- [ ] **Mod notes per player** — Freeform private notes on the player detail page, visible only to staff. Persists across sessions. Discord and Reddit both have this. Audit log only records actions taken, not suspicions or context.
- [ ] **Warning / strike system** — Formal warning primitive: log a warning with a reason, visible to the player, counted toward escalation. Separate from mute/timeout/ban — you can warn without acting. Prerequisite for the auto-escalation threshold alert (deferred item 16).
- [ ] **Login / session history** — IP address, rough geolocation (country), browser/device hint, timestamp per login. Useful for ban evasion and account compromise detection. Currently IPs are only inferable from linked-account matching.
- [ ] **Full financial transaction ledger** — "Money Trail" tab on player detail: every transfer in/out, market buy/sell, salary, business revenue, P2P. Currently only open orders and P2P contracts are visible.
- [ ] **Account freeze (non-destructive suspension)** — Lock login without triggering estate/death. Used while investigating. Different from timeout (chat-only) and ban (destructive). Discord calls it "account disabled," Reddit calls it suspension.

---

## Moderation Queue / Workflow

- [ ] **Player report queue** — In-game report button for players to flag others. Mods triage a queue instead of hunting manually. Reddit's modqueue is their centerpiece tool.
- [ ] **Modqueue triage workflow** — Reported items move through states: Pending → Reviewed → Actioned. Without this mods have no systematic workflow.
- [ ] **Bulk player actions** — Multi-select on the player list to ban/timeout/mute several accounts at once. "Ban all linked" covers IP clusters but not manually identified bot rings.
- [ ] **Mod action second-approval** — Require a second admin to confirm permanent bans and player deletes. Two-man rule prevents rogue mod mistakes.

---

## AutoMod / Preventive

- [ ] **Word / phrase filter** — Block or auto-flag messages containing configured words/phrases. Discord AutoMod, Twitch AutoMod, Reddit AutoModerator all do this. Every chat message is currently unfiltered.
- [ ] **New account restrictions** — Gate chat access behind account age or tutorial progress (e.g. must complete step 3 before posting in global). Prevents throwaway spam.
- [ ] **Rate limiting per player** — Admin-configurable caps: messages per minute, trades per hour, P2P contracts per day.
- [ ] **IP ban with CIDR support** — Block at IP level, not just account. Alt-account banning still allows fresh signups from the same machine. Needs proxy/VPN range support.
- [ ] **Shadowban / ghost mode** — Player sees their own messages but nobody else does. Better than visible mute for spam accounts because they don't immediately evade.

---

## Appeal & Accountability

- [ ] **Ban appeal system** — Player-facing form to submit an appeal after a ban. Appeals appear in the mod queue. No current channel between a banned player and staff.
- [ ] **Mod performance dashboard** — Actions per mod this week, breakdown by type, average response time to reports. Prevents inactive mods from holding titles without working.
- [ ] **Action expiry countdown** — Show "timeout expires in 2h 14m" on the player list and detail page. Timeouts already expire but there's no dashboard view of pending expirations.

---

## Economy-Specific (unique to SymCo)

- [ ] **Collusion / fraud investigation tool** — Cross-reference all P2P transactions between two specific players side by side. Player A sending Player B $10M across 5 trades should be a visible flag.
- [ ] **Wealth inequality / Gini view** — Top 10 players' share of total cash, economy concentration chart. Useful for detecting alt-account money laundering. Economy health panel shows totals but not distribution.
- [ ] **Escrow admin override** — Cancel a stuck P2P escrow and return funds to both parties without triggering a cancellation penalty. P2P detail page is currently read-only.
- [ ] **Business intervention** — Force-complete a production tick, reset a stuck cycle, or set `progress_ticks` manually from the admin UI. A crashed business blocks a player economically with no fix. (Originally deferred as item 14.)

---

## Priority Ranking

### High value / low complexity — build these first
1. Mod notes per player
2. Login / IP history tab on player detail
3. Warning system (log + notify player, no action required)
4. Action expiry countdown on player list
5. Report queue (player-submitted)
6. New account restrictions (tutorial gating on chat)

### Medium value / medium complexity
7. Word filter / AutoMod rules
8. Full financial transaction ledger per player
9. Account freeze (non-destructive login block)
10. Bulk select + action from player list
11. Collusion investigation (two-player P2P cross-reference)
12. Mod performance dashboard
13. Shadowban

### High value / high complexity — longer term
14. Ban appeal system (needs player-facing UI too)
15. IP ban with CIDR support
16. Mod action second-approval for destructive ops
17. Rate limiting per player (configurable from admin)
18. Wealth distribution / Gini coefficient view

---

## Biggest gaps vs. major platforms
- **vs. Discord** — mod notes, report queue, warning/strike primitive
- **vs. Reddit** — modqueue triage workflow
- **vs. Twitch** — AutoMod word filters
