"""Generate assets/stats.svg from the GitHub contribution calendar.

Runs daily in GitHub Actions (see .github/workflows/stats.yml), so the card
is always fresh: no third-party service, no stale cache.
"""
import datetime as dt
import json
import os
import sys
import urllib.request

USER = os.environ.get("GH_USER", "byjerkz")
OUT = os.environ.get("OUT", "assets/stats.svg")
QUERY = """query($login:String!){user(login:$login){contributionsCollection{
contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}"""


def fetch_days():
    if len(sys.argv) > 1:  # local preview: python stats.py sample.json
        return json.load(open(sys.argv[1], encoding="utf-8"))
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GH_TOKEN']}", "Content-Type": "application/json"},
    )
    data = json.load(urllib.request.urlopen(req))
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return {d["date"]: d["contributionCount"] for w in weeks for d in w["contributionDays"]}


def metrics(days):
    dates = sorted(days)
    total = sum(days.values())
    active = sum(1 for d in dates if days[d] > 0)
    longest = run = 0
    for d in dates:
        run = run + 1 if days[d] > 0 else 0
        longest = max(longest, run)
    current = 0
    rev = list(reversed(dates))
    if rev and days[rev[0]] == 0:  # today not done yet: streak still alive
        rev = rev[1:]
    for d in rev:
        if days[d] == 0:
            break
        current += 1
    return total, current, longest, active


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;")


def render(days):
    total, current, longest, active = metrics(days)
    today = max(days) if days else dt.date.today().isoformat()
    end = dt.date.fromisoformat(today)
    last = [(end - dt.timedelta(days=i)).isoformat() for i in range(29, -1, -1)]
    vals = [days.get(d, 0) for d in last]
    peak = max(vals) or 1

    W, H, m = 900, 250, 16
    tiles = [("CONTRIBUTIONS", total, "last 12 months"),
             ("CURRENT STREAK", current, "days in a row"),
             ("LONGEST STREAK", longest, "days"),
             ("ACTIVE DAYS", active, "last 12 months")]
    o = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="JetBrains Mono, Consolas, Menlo, monospace">
<defs>
<linearGradient id="bar" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#00b4d8" stop-opacity=".35"/><stop offset="1" stop-color="#00b4d8"/></linearGradient>
<filter id="g" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<style>
.c{{font-size:11px;fill:#c9d1d9}} .l{{font-size:9.5px;fill:#00b4d8;font-weight:700;letter-spacing:1.4px}}
.n{{font-size:30px;fill:#e6edf3;font-weight:700}} .u{{font-size:10px;fill:#8b949e}}
.blink{{animation:bl 1s steps(1) infinite}} @keyframes bl{{50%{{opacity:0}}}}
</style>
</defs>
<rect width="{W}" height="{H}" rx="10" fill="#0d1117"/>
<text x="{m+2}" y="28" class="c"><tspan fill="#3fb950">jerkz@dev</tspan><tspan fill="#8b949e">:</tspan><tspan fill="#00b4d8">~</tspan><tspan fill="#8b949e">$ </tspan>git stats --year<tspan class="blink" fill="#00b4d8"> ▌</tspan></text>
<text x="{W-m}" y="28" text-anchor="end" class="u">updated {today}</text>''']
    tw = (W - 2 * m - 3 * 12) / 4
    for i, (lab, num, unit) in enumerate(tiles):
        x = m + i * (tw + 12)
        o.append(f'''<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{0.15 + i * 0.15:.2f}s" dur=".5s" fill="freeze"/>
<rect x="{x:.1f}" y="44" width="{tw:.1f}" height="78" rx="9" fill="#161b22" stroke="#00b4d8" stroke-opacity=".3"/>
<text x="{x + 14:.1f}" y="66" class="l">{lab}</text>
<text x="{x + 14:.1f}" y="102" class="n">{num}</text>
<text x="{x + 22 + len(str(num)) * 19:.1f}" y="102" class="u">{esc(unit)}</text></g>''')
    # 30-day activity chart
    cy0, ch = 150, 72
    base = cy0 + ch
    o.append(f'<text x="{m + 2}" y="{cy0 - 6}" class="l">LAST 30 DAYS</text>')
    o.append(f'<line x1="{m}" y1="{base}" x2="{W - m}" y2="{base}" stroke="#30363d"/>')
    bw = (W - 2 * m) / 30
    for i, v in enumerate(vals):
        h = max(2, v / peak * (ch - 10)) if v else 2
        x = m + i * bw + 3
        col = "url(#bar)" if v else "#21262d"
        o.append(f'<rect x="{x:.1f}" width="{bw - 6:.1f}" rx="2" fill="{col}" y="{base}" height="0">'
                 f'<title>{last[i]}: {v}</title>'
                 f'<animate attributeName="height" from="0" to="{h:.1f}" begin="{0.6 + i * 0.03:.2f}s" dur=".6s" fill="freeze"/>'
                 f'<animate attributeName="y" from="{base}" to="{base - h:.1f}" begin="{0.6 + i * 0.03:.2f}s" dur=".6s" fill="freeze"/></rect>')
        if v == peak and v:
            o.append(f'<text x="{x + (bw - 6) / 2:.1f}" y="{base - h - 6:.1f}" text-anchor="middle" class="u" opacity="0">{v}'
                     f'<animate attributeName="opacity" from="0" to="1" begin="1.6s" dur=".4s" fill="freeze"/></text>')
    o.append(f'<text x="{m}" y="{base + 16}" class="u">{dt.date.fromisoformat(last[0]).strftime("%b %d")}</text>')
    o.append(f'<text x="{W - m}" y="{base + 16}" text-anchor="end" class="u">today</text>')
    o.append("</svg>")
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    open(OUT, "w", encoding="utf-8").write("\n".join(o))
    print(f"wrote {OUT}: total={total} current={current} longest={longest} active={active}")


if __name__ == "__main__":
    render(fetch_days())
