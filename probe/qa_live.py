"""Live-game QA (2026-11-04): open the PUBLIC site's Live tab in Chrome (iPhone 13) on GitHub's servers during real games.
Checks in-browser polling: requests every 10 s, CORS works, pause when hidden, resume on return, backup/fail path. Prints to the log."""
import base64, json, re, sys, time, urllib.request
from playwright.sync_api import sync_playwright
SITE = "https://msasportas.github.io/prop-check-nba/"
for i in range(40):                      # wait for Pages to serve the new build
    try:
        html = urllib.request.urlopen(SITE + "?t=%d" % time.time(), timeout=20).read().decode()
        if "cdn.nba.com/static/json/liveData" in html:
            print("new build served after", i * 15, "s"); break
    except Exception as e:
        print("wait", repr(e)[:80])
    time.sleep(15)
else:
    print("NEW BUILD NOT SERVED"); sys.exit(1)

def shot(pg, name):
    b = pg.screenshot(type="jpeg", quality=55, full_page=True)
    print("SHOT-BEGIN", name); print(base64.b64encode(b).decode()); print("SHOT-END", name)

with sync_playwright() as p:
    br = p.chromium.launch()
    dev = dict(p.devices["iPhone 13"])
    ctx = br.new_context(**dev); pg = ctx.new_page()
    reqs, errs = [], []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append("console: " + m.text) if m.type == "error" else None)
    pg.on("response", lambda r: reqs.append((round(time.time(), 1), r.status, r.url.split("?")[0][-70:])) if re.search(r"espn\.com/apis|cdn\.nba\.com", r.url) else None)
    pg.on("requestfailed", lambda r: reqs.append((round(time.time(), 1), "FAILED " + str(r.failure), r.url[-70:])) if re.search(r"espn\.com/apis|cdn\.nba\.com", r.url) else None)
    t0 = time.time()
    pg.goto(SITE + "#live"); pg.wait_for_timeout(32000)
    sb = [r for r in reqs if "scoreboard" in r[2]]
    print("SCOREBOARD READS in 32s:", len(sb), [round(r[0] - t0, 1) for r in sb], "statuses", sorted({str(r[1]) for r in reqs}))
    print("SUMMARY READS:", len([r for r in reqs if "summary" in r[2]]))
    txt = pg.evaluate("document.body.innerText")
    print("LIVE TEXT:\n" + txt[:1800])
    print("SCROLL", pg.evaluate("[document.scrollingElement.scrollWidth, innerWidth]"))
    shot(pg, "live")
    # pause when hidden
    n0 = len(reqs)
    pg.evaluate("""() => { Object.defineProperty(document, 'visibilityState', {configurable: true, get: () => 'hidden'});
                         Object.defineProperty(document, 'hidden', {configurable: true, get: () => true});
                         document.dispatchEvent(new Event('visibilitychange')); }""")
    pg.wait_for_timeout(22000)
    print("READS WHILE HIDDEN 22s:", len(reqs) - n0)
    n1 = len(reqs); t1 = time.time()
    pg.evaluate("""() => { Object.defineProperty(document, 'visibilityState', {configurable: true, get: () => 'visible'});
                         Object.defineProperty(document, 'hidden', {configurable: true, get: () => false});
                         document.dispatchEvent(new Event('visibilitychange')); }""")
    pg.wait_for_timeout(3000)
    print("READS WITHIN 3s OF RETURN:", len(reqs) - n1)
    # other tab = no polling
    pg.click(".tab[data-view=picks]") if pg.query_selector(".tab[data-view=picks]") else None
    n2 = len(reqs); pg.wait_for_timeout(15000); print("READS ON PICKS TAB 15s:", len(reqs) - n2)
    print("PAGE ERRORS:", errs[:10])
    ctx.close()
    # ESPN blocked -> NBA.com backup (403 from GitHub) -> must say unavailable, no scores
    ctx = br.new_context(**dev); pg = ctx.new_page(); errs2 = []
    pg.on("pageerror", lambda e: errs2.append(str(e)))
    pg.route(re.compile(r"site\.api\.espn\.com"), lambda r: r.abort())
    pg.goto(SITE + "#live"); pg.wait_for_timeout(15000)
    t = pg.evaluate("document.body.innerText")
    print("ESPN-BLOCKED TEXT:\n" + t[:900]); print("PAGE ERRORS:", errs2)
    shot(pg, "allfail")
    br.close()
