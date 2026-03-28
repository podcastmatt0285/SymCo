import re
import datetime
from xml.sax.saxutils import escape


def _iso_today():
    return datetime.date.today().isoformat()


def _safe_date_from_ts(ts, fallback):
    try:
        return datetime.datetime.fromtimestamp(ts).date().isoformat()
    except Exception:
        return fallback


def _get_channel_lastmod(db, handle, fallback):
    """
    Use real channel activity if available.
    Falls back safely to created_at-derived date.
    """
    try:
        row = db.query(
            "SELECT MAX(timestamp) AS ts FROM broadcast_history WHERE handle = ?",
            (handle,),
            one=True
        )
        if row and row["ts"]:
            return _safe_date_from_ts(row["ts"], fallback)
    except Exception:
        pass
    return fallback


def generate_sitemap(db, domain="notifly.cc"):
    """
    Generates a Google-safe XML sitemap.

    Includes:
    - Homepage
    - Public channel pages
    - Active livestream pages
    - Top explore hashtag pages

    Excludes:
    - Admin
    - API
    - Subscriber-only pages
    """

    base_url = f"https://{domain}"
    today = _iso_today()

    xml = []
    xml.append('<?xml version="1.0" encoding="UTF-8"?>')
    xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    def add_url(loc, lastmod, priority):
        safe_loc = escape(loc, {'"': '&quot;'})
        xml.append("  <url>")
        xml.append(f"    <loc>{safe_loc}</loc>")
        xml.append(f"    <lastmod>{lastmod}</lastmod>")
        xml.append(f"    <priority>{priority}</priority>")
        xml.append("  </url>")

    # --- Home ---
    add_url(f"{base_url}/", today, "1.0")

    # --- Channels ---
    try:
        channels = db.query(
            "SELECT handle, created_at FROM channels ORDER BY handle ASC"
        )

        for c in channels:
            handle = c["handle"]
            if not handle:
                continue

            created_fallback = (
                _safe_date_from_ts(c["created_at"], today)
                if c["created_at"]
                else today
            )

            lastmod = _get_channel_lastmod(db, handle, created_fallback)

            add_url(
                f"{base_url}/c/{handle}",
                lastmod,
                "0.8"
            )

            # --- Active livestreams ---
            try:
                row = db.query(
                    "SELECT stream_key FROM livestreams "
                    "WHERE handle = ? AND is_live = 1",
                    (handle,),
                    one=True
                )
                if row and row.get("stream_key"):
                    add_url(
                        f"{base_url}/c/{handle}/Livestream-{row['stream_key']}",
                        today,
                        "0.9"
                    )
            except Exception:
                pass

    except Exception as e:
        print(f"[Sitemap] Channel scan failed: {e}")

    # --- Explore / Hashtags ---
    try:
        bios = db.query(
            "SELECT bio FROM channels WHERE bio IS NOT NULL AND bio != ''"
        )

        tag_counts = {}

        for row in bios:
            for tag in re.findall(r"#(\w+)", row["bio"]):
                t = tag.lower()
                if t.isalnum():
                    tag_counts[t] = tag_counts.get(t, 0) + 1

        for tag, count in sorted(
            tag_counts.items(),
            key=lambda x: (-x[1], x[0])
        )[:20]:
            priority = min(0.7, 0.5 + count * 0.05)
            add_url(
                f"{base_url}/explore/{tag}",
                today,
                f"{priority:.1f}"
            )

    except Exception as e:
        print(f"[Sitemap] Tag scan failed: {e}")

    xml.append("</urlset>")
    return "\n".join(xml)
