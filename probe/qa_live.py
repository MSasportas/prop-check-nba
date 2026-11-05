"""Live-game QA / diagnosis (2026-11-04): real Chrome on GitHub's servers, page origin = the public site.
Tries the ESPN feed with different fetch options and prints what the browser saw. Prints to the log only."""
import json, re, subprocess, time
from playwright.sync_api import sync_playwright
SITE = "https://msasportas.github.io/prop-check-nba/"
D = time.strftime("%Y%m%d", time.gmtime(time.time() - 5 * 3600))
SB = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=" + D
for h in ([], ["-H", "Cache-Control: no-cache", "-H", "Pragma: no-cache"]):
    out = subprocess.run(["curl", "-s", "-o", "/dev/null", "-D", "-", "-H", "Origin: https://msasportas.github.io"] + h + [SB],
                         capture_output=True, text=True).stdout
    print("CURL", h, [l for l in out.splitlines() if re.match(r"(?i)HTTP|access-control-allow-origin|cache-control", l)])
JS = """async ([u, opts]) => { try { const r = await fetch(u, opts); const t = await r.text();
          return {ok: r.ok, status: r.status, acao: r.headers.get('access-control-allow-origin'), len: t.length}; }
        catch (e) { return {error: String(e)}; } }"""
with sync_playwright() as p:
    br = p.chromium.launch()
    for label, ctxopts in (("iphone13", dict(p.devices["iPhone 13"])), ("desktop-chrome", {})):
        ctx = br.new_context(**ctxopts); pg = ctx.new_page(); cons = []
        pg.on("console", lambda m: cons.append(m.text[:300]) if m.type == "error" else None)
        hdrs = []
        pg.on("request", lambda r: hdrs.append(r.headers) if "site.api.espn.com" in r.url else None)
        pg.goto(SITE + "#picks"); pg.wait_for_timeout(2000)
        print("UA", label, pg.evaluate("navigator.userAgent")[:120])
        for name, opts in (("no-store", {"cache": "no-store"}), ("no-store+omit", {"cache": "no-store", "credentials": "omit"}),
                           ("default", {}), ("default+bust", None)):
            u = SB + ("&_=%d" % time.time() if opts is None else "")
            print("FETCH", label, name, pg.evaluate(JS, [u, opts or {}]))
        print("REQ HEADERS (last)", hdrs[-1] if hdrs else None)
        print("CONSOLE", cons[:6])
        # the page itself
        cons.clear(); reqs = []
        pg.on("requestfailed", lambda r: reqs.append(("FAILED", r.failure, r.url[-60:])) if "espn" in r.url else None)
        pg.on("response", lambda r: reqs.append((r.status, r.url[-60:])) if "site.api.espn" in r.url else None)
        pg.goto(SITE + "#live"); pg.wait_for_timeout(23000)
        print("PAGE", label, "espn responses:", reqs[:8])
        t = pg.evaluate("document.body.innerText")
        print("PAGE TEXT", label, t[:700].replace("\n", " | "))
        print("CONSOLE", cons[:6])
        ctx.close()
    br.close()
