"""Render seammoney org cards: orgfetch terminal card + 12-month commit graph.

Self-contained (stdlib only). Needs GITHUB_TOKEN. Also rewrites the repo
showcase table between markers in profile/README.md.
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

T = {
    "bg": "#0d1117", "bg2": "#10151d", "panel": "#161b22", "border": "#30363d",
    "fg": "#c9d1d9", "muted": "#8b949e", "phosphor": "#53fca1",
    "amber": "#ffb454", "key": "#ffa657", "value": "#a5d6ff",
}

LANG_COLORS = {
    "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Move": "#4a90e2",
    "Python": "#3572A5", "Rust": "#dea584", "HTML": "#e34c26",
    "Svelte": "#ff3e00", "Solidity": "#AA6746",
}

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

    # Weekly commit counts per repo (REST stats; 202 = still computing).
    monthly = [0] * 12
    total_year = 0
    now = datetime.datetime.now(datetime.timezone.utc)
    for r in repos:
        for attempt in range(3):
            data, status = api(f"/repos/{ORG}/{r['name']}/stats/commit_activity")
            if status == 202 or data is None or not isinstance(data, list):
                time.sleep(3)
                continue
            for wk in data:
                d = datetime.datetime.fromtimestamp(wk["week"], datetime.timezone.utc)
                months_ago = (now.year - d.year) * 12 + now.month - d.month
                if 0 <= months_ago < 12:
                    monthly[11 - months_ago] += wk["total"]
                    total_year += wk["total"]
            break
    return org, repos, monthly, total_year


def render_orgfetch(org, repos, total_year):
    stars = sum(r["stargazers_count"] for r in repos)
    forks = sum(r["forks_count"] for r in repos)
    langs = {}
    for r in repos:
        if r["language"]:
            langs[r["language"]] = langs.get(r["language"], 0) + 1
    top_langs = sorted(langs.items(), key=lambda kv: -kv[1])[:4]
    lang_total = sum(v for _, v in langs.items()) or 1
    created = datetime.datetime.fromisoformat(org["created_at"].replace("Z", "+00:00"))

    W = 940
    ascii_x, ascii_y, lh = 56, 110, 19
    art = "".join(
        f'<text x="{ascii_x}" y="{ascii_y + i * lh}" font-size="15" fill="{T["phosphor"]}" '
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
        f'fill="{T["phosphor"]}" filter="url(#soft)">seam<tspan fill="{T["muted"]}">@</tspan>'
        f'<tspan fill="{T["value"]}">money</tspan></text>',
        f'<text x="{info_x}" y="{info_y + ilh}" font-size="13" fill="{T["border"]}" '
        f'xml:space="preserve">{"-" * 40}</text>',
    ]
    for i, (k, v) in enumerate(kv):
        y = info_y + (i + 2) * ilh
        rows.append(
            f'<g font-size="13"><text x="{info_x}" y="{y}" fill="{T["key"]}" font-weight="600">{k}</text>'
            f'<text x="{info_x + 90}" y="{y}" fill="{T["fg"]}">{esc(v)}</text></g>'
        )

    # language bar
    bar_y = info_y + (len(kv) + 2) * ilh + 14
    bar_x, bar_w = info_x, 540
    x = bar_x
    segs, labels = [], []
    for lang, count in top_langs:
        w = bar_w * count / lang_total
        color = LANG_COLORS.get(lang, "#8b949e")
        segs.append(f'<rect x="{x:.1f}" y="{bar_y}" width="{w:.1f}" height="12" fill="{color}"/>')
        x += w
    lx = bar_x
    for lang, count in top_langs:
        color = LANG_COLORS.get(lang, "#8b949e")
        pct = 100 * count / lang_total
        labels.append(
            f'<circle cx="{lx + 5}" cy="{bar_y + 32}" r="5" fill="{color}"/>'
            f'<text x="{lx + 16}" y="{bar_y + 36}" font-size="11" fill="{T["fg"]}">{lang} {pct:.0f}%</text>'
        )
        lx += 16 + (len(lang) + 4) * 7 + 18

    H = bar_y + 64
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" font-family="{MONO}">
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{T['bg']}"/><stop offset="1" stop-color="{T['bg2']}"/>
  </linearGradient>
  <filter id="soft" x="-30%" y="-30%" width="160%" height="160%">
    <feGaussianBlur stdDeviation="1.4" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">
    <rect width="4" height="2" fill="#000" opacity="0.14"/>
  </pattern>
</defs>
<rect width="{W}" height="{H}" rx="14" fill="url(#bg)" stroke="{T['border']}"/>
<circle cx="26" cy="26" r="7" fill="#ff5f56"/><circle cx="48" cy="26" r="7" fill="#ffbd2e"/><circle cx="70" cy="26" r="7" fill="#27c93f"/>
<text x="{W / 2}" y="31" text-anchor="middle" font-size="13" fill="{T['muted']}">seam@money: ~/orgfetch</text>
<line x1="0" y1="46" x2="{W}" y2="46" stroke="{T['border']}"/>
{art}
{"".join(rows)}
{"".join(segs)}
{"".join(labels)}
<rect width="{W}" height="{H}" rx="14" fill="url(#scan)"/>
</svg>"""


def render_commits(monthly):
    W, H = 940, 240
    chart_x, chart_y, chart_w, chart_h = 56, 70, 830, 120
    mx = max(monthly + [1])
    now = datetime.datetime.now(datetime.timezone.utc)
    bars = []
    bw = (chart_w - 11 * 14) / 12
    for i, v in enumerate(monthly):
        x = chart_x + i * (bw + 14)
        h = max(chart_h * v / mx, 2)
        d = now - datetime.timedelta(days=30 * (11 - i))
        last = i == 11
        bars.append(
            f'<rect x="{x:.1f}" y="{chart_y + chart_h - h:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="3" '
            f'fill="{T["amber"] if last else T["phosphor"]}" opacity="{1 if last else 0.4 + 0.6 * v / mx:.2f}"/>'
            f'<text x="{x + bw / 2:.1f}" y="{chart_y + chart_h - h - 7:.1f}" text-anchor="middle" '
            f'font-size="10" fill="{T["phosphor"]}">{v if v else ""}</text>'
            f'<text x="{x + bw / 2:.1f}" y="{chart_y + chart_h + 18}" text-anchor="middle" '
            f'font-size="10" fill="{T["muted"]}">{d:%b}</text>'
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" font-family="{MONO}">
<defs>
  <linearGradient id="bg2" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{T['bg']}"/><stop offset="1" stop-color="{T['bg2']}"/>
  </linearGradient>
  <pattern id="scan2" width="4" height="4" patternUnits="userSpaceOnUse">
    <rect width="4" height="2" fill="#000" opacity="0.14"/>
  </pattern>
</defs>
<rect width="{W}" height="{H}" rx="14" fill="url(#bg2)" stroke="{T['border']}"/>
<text x="56" y="40" font-size="12" fill="{T['muted']}">~ <tspan fill="{T['phosphor']}">❯</tspan> <tspan fill="{T['fg']}">git log --all --since="1 year" --oneline | wc -l</tspan>  <tspan fill="{T['amber']}">→ {sum(monthly):,} commits</tspan></text>
{"".join(bars)}
<rect width="{W}" height="{H}" rx="14" fill="url(#scan2)"/>
</svg>"""


def repo_table(repos):
    top = sorted(repos, key=lambda r: (r["stargazers_count"], r["pushed_at"]), reverse=True)[:6]
    rows = []
    for i in range(0, len(top), 2):
        cells = []
        for r in top[i:i + 2]:
            lang = r["language"] or "—"
            color = LANG_COLORS.get(lang, "#8b949e")
            desc = (r["description"] or "").strip()
            if len(desc) > 80:
                desc = desc[:77] + "..."
            cells.append(
                f'<td width="50%"><a href="{r["html_url"]}"><b><samp>{esc(r["name"])}</samp></b></a>'
                f' <img src="https://img.shields.io/badge/-{esc(lang)}-{color.lstrip("#")}?style=flat-square" align="right"/>'
                f'<br/><sub>{esc(desc)}</sub><br/>'
                f'<sub>⭐ {r["stargazers_count"]} · ⑂ {r["forks_count"]}</sub></td>'
            )
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return "<table width=\"100%\">" + "".join(rows) + "</table>"


def main():
    org, repos, monthly, total_year = fetch()
    assets = ROOT / "profile" / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "orgfetch.svg").write_text(render_orgfetch(org, repos, total_year))
    (assets / "commits.svg").write_text(render_commits(monthly))

    readme = ROOT / "profile" / "README.md"
    text = readme.read_text()
    start, end = "<!-- REPOS:START -->", "<!-- REPOS:END -->"
    if start in text and end in text:
        head, rest = text.split(start, 1)
        _, tail = rest.split(end, 1)
        text = head + start + "\n" + repo_table(repos) + "\n" + end + tail
        readme.write_text(text)
    print(f"rendered org cards: {len(repos)} repos, {total_year} commits/yr")


if __name__ == "__main__":
    main()
