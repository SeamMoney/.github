"""seammoney org cards v2 — markets-terminal aesthetic.

Renders: orgfetch terminal card, SEAMMONEY-PERP candle dashboard (org-wide
weekly commit candles on a 7-day rolling index + repo order book), and rich
per-repo showcase cards with commit sparklines. Rewrites the showcase grid
between markers in profile/README.md. Stdlib only; needs GITHUB_TOKEN.
"""
import datetime
import json
import os
import pathlib
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
ORG = "seammoney"
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
MONO = "ui-monospace,'JetBrains Mono','SF Mono',Menlo,Consolas,monospace"

C = {
    "bg": "#070b10", "bg2": "#10151d", "panel": "#0b1018", "border": "#1c2430",
    "grid": "#141b26", "dot": "#1a2330", "fg": "#9fb2c8", "muted": "#55657a",
    "mint": "#16c79a", "mintHi": "#97fce4", "red": "#f6465d", "amber": "#ffb454",
    "key": "#ffa657", "value": "#a5d6ff",
}

LANG_COLORS = {
    "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Move": "#4a90e2",
    "Python": "#3572A5", "Rust": "#dea584", "HTML": "#e34c26",
    "Svelte": "#ff3e00", "Solidity": "#AA6746", "Vue": "#41b883",
}

# Flagships always shown first if they exist
BOOST = ["tx-composer", "cash.trading", "aptos-polymarket", "MoveGPT"]

DOLLAR = [
    "  $$$$$$\\ ",
    " $$  __$$\\",
    " $$ /  \\__|",
    " \\$$$$$$\\ ",
    "  \\____$$\\",
    " $$\\   $$ |",
    " \\$$$$$$  |",
    "  \\______/ ",
]


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("User-Agent", ORG)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode()), r.status


def compact(n):
    n = float(n)
    for div, suf in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(n) >= div:
            return f"{n / div:.1f}{suf}"
    return f"{n:.0f}"


def ago(iso):
    d = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    days = (datetime.datetime.now(datetime.timezone.utc) - d).days
    if days < 1:
        return "today"
    if days < 30:
        return f"{days}d ago"
    if days < 365:
        return f"{days // 30}mo ago"
    return f"{days // 365}y ago"


def fetch():
    org, _ = api(f"/orgs/{ORG}")
    repos, page = [], 1
    while True:
        batch, _ = api(f"/orgs/{ORG}/repos?per_page=100&page={page}&type=public")
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    repos = [r for r in repos if not r["fork"]]

    daily = [0] * 364  # org-wide, oldest → newest
    for r in repos:
        weekly = [0] * 52
        for attempt in range(3):
            data, status = api(f"/repos/{ORG}/{r['name']}/stats/commit_activity")
            if status == 202 or not isinstance(data, list) or not data:
                time.sleep(3)
                continue
            data = data[-52:]
            for wi, wk in enumerate(data):
                weekly[wi + 52 - len(data)] = wk.get("total", 0)
                for di, dv in enumerate(wk.get("days", [])):
                    idx = (wi + 52 - len(data)) * 7 + di
                    if idx < 364:
                        daily[idx] += dv
            break
        r["_weekly"] = weekly
        r["_commits52"] = sum(weekly)
    return org, repos, daily


# ---------------------------------------------------------------- orgfetch
def render_orgfetch(org, repos, total_year):
    stars = sum(r["stargazers_count"] for r in repos)
    forks = sum(r["forks_count"] for r in repos)
    langs = {}
    for r in repos:
        if r["language"]:
            langs[r["language"]] = langs.get(r["language"], 0) + 1
    top_langs = sorted(langs.items(), key=lambda kv: -kv[1])[:4]
    lang_total = sum(langs.values()) or 1
    created = datetime.datetime.fromisoformat(org["created_at"].replace("Z", "+00:00"))

    W = 940
    art = "".join(
        f'<text x="56" y="{110 + i * 19}" font-size="15" fill="{C["mint"]}" '
        f'xml:space="preserve" filter="url(#soft)">{esc(line)}</text>'
        for i, line in enumerate(DOLLAR)
    )
    info_x, info_y, ilh = 320, 96, 21
    kv = [
        ("Org", "Seam Money — onchain finance lab"),
        ("Founded", f"{created:%b %Y} · San Francisco"),
        ("Repos", f"{len(repos)} public · {stars} stars · {forks} forks"),
        ("Commits", f"{total_year:,} across all repos (12 mo)"),
        ("Stack", "Move · TypeScript · Python · Rust"),
        ("Chains", "Aptos · Sui · Solana · EVM"),
        ("Builds", "DEXs · prediction markets · trading bots"),
        ("Human", "github.com/maxmoneycash"),
    ]
    rows = [
        f'<text x="{info_x}" y="{info_y}" font-size="15" font-weight="700" '
        f'fill="{C["mintHi"]}" filter="url(#soft)">seam<tspan fill="{C["muted"]}">@</tspan>'
        f'<tspan fill="{C["value"]}">money</tspan></text>',
        f'<text x="{info_x}" y="{info_y + ilh}" font-size="13" fill="{C["border"]}" '
        f'xml:space="preserve">{"-" * 40}</text>',
    ]
    for i, (k, v) in enumerate(kv):
        y = info_y + (i + 2) * ilh
        rows.append(
            f'<g font-size="13"><text x="{info_x}" y="{y}" fill="{C["key"]}" font-weight="600">{k}</text>'
            f'<text x="{info_x + 90}" y="{y}" fill="{C["fg"]}">{esc(v)}</text></g>'
        )
    bar_y = info_y + (len(kv) + 2) * ilh + 14
    x, segs, labels = info_x, [], []
    for lang, count in top_langs:
        w = 540 * count / lang_total
        segs.append(f'<rect x="{x:.1f}" y="{bar_y}" width="{w:.1f}" height="12" fill="{LANG_COLORS.get(lang, "#8b949e")}"/>')
        x += w
    lx = info_x
    for lang, count in top_langs:
        pct = 100 * count / lang_total
        labels.append(
            f'<circle cx="{lx + 5}" cy="{bar_y + 32}" r="5" fill="{LANG_COLORS.get(lang, "#8b949e")}"/>'
            f'<text x="{lx + 16}" y="{bar_y + 36}" font-size="11" fill="{C["fg"]}">{lang} {pct:.0f}%</text>'
        )
        lx += 16 + (len(lang) + 4) * 7 + 18
    H = bar_y + 64
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" font-family="{MONO}">
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{C['bg']}"/><stop offset="1" stop-color="{C['bg2']}"/>
  </linearGradient>
  <filter id="soft" x="-30%" y="-30%" width="160%" height="160%">
    <feGaussianBlur stdDeviation="1.4" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">
    <rect width="4" height="2" fill="#000" opacity="0.14"/>
  </pattern>
</defs>
<rect width="{W}" height="{H}" rx="14" fill="url(#bg)" stroke="{C['border']}"/>
<circle cx="26" cy="26" r="7" fill="#ff5f56"/><circle cx="48" cy="26" r="7" fill="#ffbd2e"/><circle cx="70" cy="26" r="7" fill="#27c93f"/>
<text x="{W / 2}" y="31" text-anchor="middle" font-size="13" fill="{C['muted']}">seam@money: ~/orgfetch</text>
<line x1="0" y1="46" x2="{W}" y2="46" stroke="{C['border']}"/>
{art}{"".join(rows)}{"".join(segs)}{"".join(labels)}
<rect width="{W}" height="{H}" rx="14" fill="url(#scan)"/>
</svg>"""


# ---------------------------------------------------------------- market
def render_market(repos, daily):
    W, H = 940, 560
    head_h = 44
    chart_x, chart_y = 24, head_h + 26
    chart_w, chart_h = 600, 290
    vol_h = 54
    panel_h = chart_h + vol_h + 46
    total = sum(daily)
    parts = []

    roll = [sum(daily[max(0, i - 6):i + 1]) for i in range(len(daily))]
    candles = []
    for wi in range(52):
        seg = roll[wi * 7:wi * 7 + 7]
        if seg:
            candles.append({
                "o": seg[0], "c": seg[-1], "h": max(seg), "l": min(seg),
                "v": sum(daily[wi * 7:wi * 7 + 7]),
            })

    d30 = sum(daily[-30:])
    d30p = sum(daily[-60:-30]) or 1
    delta = 100 * (d30 - d30p) / d30p
    parts.append(
        f'<text x="{chart_x}" y="28" font-size="14" font-weight="700" fill="{C["mintHi"]}">SEAMMONEY-PERP</text>'
        f'<text x="{chart_x + 162}" y="28" font-size="11" fill="{C["muted"]}">ORG COMMITS / 52W</text>'
        f'<circle cx="{chart_x + 308}" cy="24" r="4" fill="{C["mint"]}">'
        f'<animate attributeName="opacity" values="1;0.2;1" dur="2s" repeatCount="indefinite"/></circle>'
        f'<text x="{chart_x + 320}" y="28" font-size="11" fill="{C["mint"]}">LIVE</text>'
        f'<text x="{W - 24}" y="28" text-anchor="end" font-size="11" fill="{C["fg"]}">'
        f'LAST <tspan fill="{C["mintHi"]}" font-weight="700">{roll[-1] if roll else 0}</tspan>'
        f'   30D <tspan fill="{C["mint"] if delta >= 0 else C["red"]}" font-weight="700">{delta:+.1f}%</tspan>'
        f'   52W VOL <tspan fill="{C["mintHi"]}" font-weight="700">{total:,}</tspan>'
        f'   REPOS <tspan fill="{C["amber"]}" font-weight="700">{len(repos)}</tspan></text>'
    )

    parts.append(
        f'<rect x="{chart_x - 4}" y="{chart_y - 14}" width="{chart_w + 60}" height="{panel_h}" rx="8" '
        f'fill="{C["panel"]}" stroke="{C["border"]}"/>'
        f'<rect x="{chart_x - 4}" y="{chart_y - 14}" width="{chart_w + 60}" height="{panel_h}" rx="8" fill="url(#dots)"/>'
    )
    hi = max((c["h"] for c in candles), default=1)
    lo = min((c["l"] for c in candles), default=0)
    span = max(hi - lo, 1)
    hi += span * 0.06
    lo = max(lo - span * 0.05, 0)
    span = hi - lo

    def ys(v):
        return chart_y + chart_h * (1 - (v - lo) / span)

    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        v = lo + span * frac
        parts.append(
            f'<line x1="{chart_x + 4}" y1="{ys(v):.1f}" x2="{chart_x + chart_w}" y2="{ys(v):.1f}" '
            f'stroke="{C["grid"]}" stroke-dasharray="2 6"/>'
            f'<text x="{chart_x + chart_w + 10}" y="{ys(v) + 4:.1f}" font-size="9" fill="{C["muted"]}">{v:,.0f}</text>'
        )
    step = chart_w / max(len(candles), 1)
    body_w = max(step - 3, 2.5)
    pts = " ".join(
        f"{chart_x + 6 + i * step + body_w / 2:.1f},{ys(c['c']):.1f}" for i, c in enumerate(candles)
    )
    parts.append(f'<polyline points="{pts}" fill="none" stroke="{C["mintHi"]}" stroke-width="1" opacity="0.35"/>')
    vmax = max((c["v"] for c in candles), default=1) or 1
    for i, c in enumerate(candles):
        x = chart_x + 6 + i * step
        mid = x + body_w / 2
        up = c["c"] >= c["o"]
        color = C["mint"] if up else C["red"]
        top, bot = max(c["o"], c["c"]), min(c["o"], c["c"])
        parts.append(
            f'<line x1="{mid:.1f}" y1="{ys(c["h"]):.1f}" x2="{mid:.1f}" y2="{ys(c["l"]):.1f}" stroke="{color}"/>'
            f'<rect x="{x:.1f}" y="{ys(top):.1f}" width="{body_w:.1f}" height="{max(ys(bot) - ys(top), 2):.1f}" rx="1" fill="{color}"/>'
        )
        vy = chart_y + chart_h + 12
        vh = vol_h * c["v"] / vmax
        parts.append(
            f'<rect x="{x:.1f}" y="{vy + vol_h - vh:.1f}" width="{body_w:.1f}" height="{max(vh, 1):.1f}" '
            f'fill="{color}" opacity="0.4"/>'
        )
    if candles:
        ly = ys(candles[-1]["c"])
        parts.append(
            f'<line x1="{chart_x + 4}" y1="{ly:.1f}" x2="{chart_x + chart_w}" y2="{ly:.1f}" '
            f'stroke="{C["amber"]}" stroke-dasharray="6 4"/>'
            f'<rect x="{chart_x + chart_w + 4}" y="{ly - 9:.1f}" width="50" height="17" rx="3" fill="{C["amber"]}"/>'
            f'<text x="{chart_x + chart_w + 29}" y="{ly + 4:.1f}" text-anchor="middle" font-size="10" '
            f'font-weight="700" fill="#070b10">{candles[-1]["c"]}</text>'
        )
    now = datetime.datetime.now(datetime.timezone.utc)
    for wi in range(0, 52, 4):
        d = now - datetime.timedelta(days=(52 - wi) * 7)
        mon = f"{d:%b}".upper()
        parts.append(
            f'<text x="{chart_x + 6 + wi * step:.1f}" y="{chart_y + chart_h + vol_h + 26}" '
            f'font-size="9" fill="{C["muted"]}">{mon}</text>'
        )

    # order book: asks = top stars, bids = hottest last 4 weeks
    ob_x, ob_w = chart_x + chart_w + 76, W - chart_x - chart_w - 100
    ob_y = chart_y - 14
    row_h = 22
    parts.append(
        f'<rect x="{ob_x}" y="{ob_y}" width="{ob_w}" height="{panel_h}" rx="8" fill="{C["panel"]}" stroke="{C["border"]}"/>'
        f'<text x="{ob_x + 14}" y="{ob_y + 24}" font-size="11" letter-spacing="2" fill="{C["fg"]}">ORDER BOOK</text>'
        f'<text x="{ob_x + ob_w - 14}" y="{ob_y + 24}" text-anchor="end" font-size="9" fill="{C["muted"]}">REPOS</text>'
    )
    by_stars = sorted(repos, key=lambda r: -r["stargazers_count"])[:5]
    smax = max((r["stargazers_count"] for r in by_stars), default=1) or 1
    ay = ob_y + 38
    for r in by_stars:
        bw = (ob_w - 28) * r["stargazers_count"] / smax
        parts.append(
            f'<rect x="{ob_x + ob_w - 14 - bw:.1f}" y="{ay}" width="{bw:.1f}" height="{row_h - 5}" fill="{C["red"]}" opacity="0.16"/>'
            f'<text x="{ob_x + 14}" y="{ay + 12}" font-size="9.5" fill="{C["red"]}">{esc(r["name"][:15].upper())}</text>'
            f'<text x="{ob_x + ob_w - 14}" y="{ay + 12}" text-anchor="end" font-size="10" fill="{C["fg"]}">★ {r["stargazers_count"]}</text>'
        )
        ay += row_h
    parts.append(
        f'<line x1="{ob_x + 10}" y1="{ay + 3}" x2="{ob_x + ob_w - 10}" y2="{ay + 3}" stroke="{C["border"]}"/>'
        f'<text x="{ob_x + ob_w / 2}" y="{ay + 19}" text-anchor="middle" font-size="11" font-weight="700" '
        f'fill="{C["amber"]}">MARK {total:,} COMMITS</text>'
        f'<line x1="{ob_x + 10}" y1="{ay + 27}" x2="{ob_x + ob_w - 10}" y2="{ay + 27}" stroke="{C["border"]}"/>'
    )
    hot = sorted(repos, key=lambda r: -sum(r.get("_weekly", [0])[-4:]))[:5]
    hmax = max((sum(r.get("_weekly", [0])[-4:]) for r in hot), default=1) or 1
    by = ay + 40
    for r in hot:
        v = sum(r.get("_weekly", [0])[-4:])
        bw = (ob_w - 28) * v / hmax
        parts.append(
            f'<rect x="{ob_x + 14}" y="{by}" width="{bw:.1f}" height="{row_h - 5}" fill="{C["mint"]}" opacity="0.16"/>'
            f'<text x="{ob_x + 14}" y="{by + 12}" font-size="9.5" fill="{C["mint"]}">{esc(r["name"][:15].upper())}</text>'
            f'<text x="{ob_x + ob_w - 14}" y="{by + 12}" text-anchor="end" font-size="10" fill="{C["fg"]}">{v}c · 4w</text>'
        )
        by += row_h
    parts.append(
        f'<text x="{ob_x + 14}" y="{by + 18}" font-size="9" fill="{C["muted"]}">ASKS = STARS · BIDS = 4W COMMITS</text>'
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" font-family="{MONO}">
<defs>
  <pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse">
    <circle cx="2" cy="2" r="0.9" fill="{C['dot']}"/>
  </pattern>
</defs>
<rect width="{W}" height="{H}" rx="14" fill="{C['bg']}" stroke="{C['border']}"/>
<line x1="0" y1="{head_h}" x2="{W}" y2="{head_h}" stroke="{C['border']}"/>
{"".join(parts)}
</svg>"""


# ---------------------------------------------------------------- repo cards
def render_repo_card(r):
    W, H = 560, 170
    name = r["name"]
    lang = r["language"] or "—"
    lang_color = LANG_COLORS.get(lang, "#8b949e")
    weekly = r.get("_weekly", [0] * 52)
    commits = r.get("_commits52", 0)
    desc = (r.get("description") or "").strip()
    created = datetime.datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
    if not desc:
        desc = f"{lang} project · est. {created:%b %Y}"
    # wrap to two lines of ~62 chars
    words, lines, cur = desc.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > 62:
            lines.append(cur)
            cur = w
            if len(lines) == 2:
                break
        else:
            cur = f"{cur} {w}".strip()
    if cur and len(lines) < 2:
        lines.append(cur)
    if len(lines) == 2 and len(" ".join(words)) > len(" ".join(lines)):
        lines[1] = lines[1][:59] + "..."
    desc_svg = "".join(
        f'<text x="28" y="{64 + i * 17}" font-size="11.5" fill="{C["fg"]}">{esc(l)}</text>'
        for i, l in enumerate(lines)
    )

    # sparkline
    sx, sy, sw, sh = 28, 104, 320, 40
    wmax = max(max(weekly), 1)
    pts = " ".join(
        f"{sx + i * sw / 51:.1f},{sy + sh - sh * v / wmax:.1f}" for i, v in enumerate(weekly)
    )
    area = f"{sx},{sy + sh} {pts} {sx + sw},{sy + sh}"

    ticker = "$" + "".join(ch for ch in name.upper() if ch.isalnum())[:5]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" font-family="{MONO}">
<defs>
  <linearGradient id="cardbg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#0d1117"/><stop offset="1" stop-color="#0a0f16"/>
  </linearGradient>
  <linearGradient id="sparkfill" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{C['mint']}" stop-opacity="0.35"/>
    <stop offset="1" stop-color="{C['mint']}" stop-opacity="0.02"/>
  </linearGradient>
</defs>
<rect width="{W}" height="{H}" rx="12" fill="url(#cardbg)" stroke="{C['border']}"/>
<text x="28" y="34" font-size="16" font-weight="700" fill="{C['mintHi']}">{esc(name)}</text>
<text x="{28 + len(name) * 10.5 + 14}" y="34" font-size="10" fill="{C['muted']}">{ticker}</text>
<g>
  <rect x="{W - 28 - len(lang) * 7 - 26}" y="20" width="{len(lang) * 7 + 26}" height="20" rx="10" fill="{C['panel']}" stroke="{lang_color}" stroke-opacity="0.6"/>
  <circle cx="{W - 28 - len(lang) * 7 - 13}" cy="30" r="4" fill="{lang_color}"/>
  <text x="{W - 34}" y="34" text-anchor="end" font-size="10" fill="{C['fg']}">{esc(lang)}</text>
</g>
{desc_svg}
<polygon points="{area}" fill="url(#sparkfill)"/>
<polyline points="{pts}" fill="none" stroke="{C['mint']}" stroke-width="1.4"/>
<text x="{sx}" y="{sy + sh + 16}" font-size="9" fill="{C['muted']}">52W COMMIT FLOW</text>
<g font-size="11" fill="{C['fg']}">
  <text x="{W - 28}" y="{sy + 8}" text-anchor="end">★ {r['stargazers_count']}   ⑂ {r['forks_count']}</text>
  <text x="{W - 28}" y="{sy + 26}" text-anchor="end"><tspan fill="{C['mintHi']}" font-weight="700">{commits}</tspan> commits · 52w</text>
  <text x="{W - 28}" y="{sy + 44}" text-anchor="end" fill="{C['muted']}">pushed {ago(r['pushed_at'])}</text>
</g>
</svg>"""


def score(r):
    boost = (len(BOOST) - BOOST.index(r["name"])) * 1000 if r["name"] in BOOST else 0
    days_old = (
        datetime.datetime.now(datetime.timezone.utc)
        - datetime.datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00"))
    ).days
    return boost + r["stargazers_count"] * 50 + r.get("_commits52", 0) - days_old * 0.5


def main():
    org, repos, daily = fetch()
    total_year = sum(daily)
    assets = ROOT / "profile" / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "orgfetch.svg").write_text(render_orgfetch(org, repos, total_year))
    (assets / "market.svg").write_text(render_market(repos, daily))

    showcase = sorted(repos, key=score, reverse=True)[:8]
    cells = []
    for r in showcase:
        (assets / f"repo-{r['name']}.svg").write_text(render_repo_card(r))
        cells.append(
            f'<a href="{r["html_url"]}"><img src="./assets/repo-{r["name"]}.svg" width="418" alt="{esc(r["name"])}"/></a>'
        )
    grid = '<p align="center">\n' + "\n".join(cells) + "\n</p>"

    readme = ROOT / "profile" / "README.md"
    text = readme.read_text()
    start, end = "<!-- REPOS:START -->", "<!-- REPOS:END -->"
    if start in text and end in text:
        head, rest = text.split(start, 1)
        _, tail = rest.split(end, 1)
        readme.write_text(head + start + "\n" + grid + "\n" + end + tail)
    print(f"rendered org v2: {len(repos)} repos, {total_year} commits/yr, {len(showcase)} showcase cards")


if __name__ == "__main__":
    main()
